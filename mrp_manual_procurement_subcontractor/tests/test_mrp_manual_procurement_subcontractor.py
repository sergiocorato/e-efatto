# Copyright 2023 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo.addons.mrp_production_demo.tests.common_data import TestProductionData
from odoo.tests import Form
from odoo.tools import mute_logger


class TestMrpProductionManualProcurement(TestProductionData):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env['stock.warehouse'].search([], limit=1)
        cls.resupply_sub_on_order_route = cls.env['stock.location.route'].search([
            ('name', '=', 'Resupply Subcontractor on Order')])
        cls.partner_subcontract_location = cls.env['stock.location'].create({
            'name': 'Specific partner location',
            'location_id': cls.env.ref(
                'stock.stock_location_locations_partner').id,
            'usage': 'internal',
            'company_id': cls.env.user.company_id.id,
        })
        resupply_rule = cls.resupply_sub_on_order_route.rule_ids.filtered(
            lambda l: (
                l.location_id == cls.top_product.property_stock_production
                and l.location_src_id ==
                cls.env.user.company_id.subcontracting_location_id))
        resupply_rule.copy({
            'location_src_id': cls.partner_subcontract_location.id})
        resupply_warehouse_rule = (
            cls.warehouse.mapped('route_ids.rule_ids').filtered(lambda l: (
                l.location_id ==
                cls.env.user.company_id.subcontracting_location_id and
                l.location_src_id == cls.warehouse.lot_stock_id)))
        for warehouse_rule in resupply_warehouse_rule:
            warehouse_rule.copy({
                'location_id': cls.partner_subcontract_location.id})
        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'Test partner',
        })
        cls.subcontractor_partner1 = cls.env['res.partner'].create({
            'name': 'Subcontractor 1',
        })
        cls.subcontractor_partner1.property_stock_subcontractor = (
            cls.partner_subcontract_location.id)
        supplierinfo_1 = cls.env['product.supplierinfo'].create({
            'name': cls.subcontractor_partner1.id,
        })
        cls.subcontractor_partner2 = cls.env['res.partner'].create({
            'name': 'Subcontractor 2',
        })
        cls.subcontractor_partner2.property_stock_subcontractor = (
            cls.partner_subcontract_location.id)
        supplierinfo_2 = cls.env['product.supplierinfo'].create({
            'name': cls.subcontractor_partner2.id,
        })
        # ADD to top_product buy and (resupply route is necessary?)
        cls.top_product.write({
            'purchase_ok': True,
            'route_ids': [
                (4, cls.env.ref('purchase_stock.route_warehouse0_buy').id),
                (4, cls.resupply_sub_on_order_route.id),
                # (3, cls.env.ref('stock.route_warehouse0_mto').id),
            ],
            'seller_ids': [(6, 0, [supplierinfo_1.id, supplierinfo_2.id])],
        })
        cls.main_bom_subcontracted = cls.main_bom.copy(
            default={
                'type': 'subcontract',
                'subcontractor_ids': [
                    (6, 0, [
                        cls.subcontractor_partner1.id,
                        cls.subcontractor_partner2.id,
                    ])
                ],
            }
        )

    def _create_sale_order_line(self, order, product, qty):
        vals = {
            'order_id': order.id,
            'product_id': product.id,
            'product_uom_qty': qty,
            'price_unit': product.list_price,
            }
        line = self.env['sale.order.line'].create(vals)
        line.product_id_change()
        line.product_uom_change()
        line._onchange_discount()
        line._convert_to_write(line._cache)
        return line

    def test_01_mo_from_sale_with_subcontracting_and_mto(self):
        self.assertTrue(
            self.top_product.mapped('seller_ids.is_subcontractor')
        )
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
        })
        self._create_sale_order_line(sale_order, self.top_product, 3)
        sale_order.with_context(
            test_mrp_manual_procurement_subcontractor=True
        ).action_confirm()
        # check procurement has not created RDP, even launching scheduler (which will
        # do nothing anyway)
        with mute_logger('odoo.addons.stock.models.procurement'):
            self.procurement_model.run_scheduler()
        self.production = self.env['mrp.production'].search(
            [('product_id', '=', self.top_product.id)])
        self.assertTrue(self.production.is_stopped)
        po_ids = self.env['purchase.order'].search([
            ('state', '=', 'draft'),
            ('order_line.product_id', 'in', self.top_product.ids),
        ])
        self.assertFalse(po_ids)
        # continue production with subcontrator
        procure_form = Form(
            self.env["mrp.production.procure.subcontractor"].with_context(
                active_id=self.production.id,
                active_ids=[self.production.id],
            )
        )
        procure_form.subcontractor_id = self.subcontractor_partner2
        wizard = procure_form.save()
        wizard.action_done()
        to_confirm_po_ids = self.env['purchase.order'].search([
            ('order_line.product_id', 'in', self.top_product.ids),
        ])
        self.assertEqual(len(to_confirm_po_ids), 1)
        # check vendor is equal to selected subcontractor
        self.assertEqual(to_confirm_po_ids.partner_id, self.subcontractor_partner2)
        self.assertEqual(len(to_confirm_po_ids.mapped('order_line')), 1)
        to_confirm_po_ids.button_confirm()
        self.assertEqual(to_confirm_po_ids.state, 'purchase')

    def test_02_normal_mo_from_sale_with_mto(self):
        product_qty = 3
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
        })
        self._create_sale_order_line(sale_order, self.top_product, product_qty)
        sale_order.with_context(
            test_mrp_manual_procurement_subcontractor=True
        ).action_confirm()
        # check procurement has not created RDP, even launching scheduler (which will
        # do nothing anyway)
        with mute_logger('odoo.addons.stock.models.procurement'):
            self.procurement_model.run_scheduler()
        self.production = self.env['mrp.production'].search(
            [('product_id', '=', self.top_product.id)])
        self.assertTrue(self.production.is_stopped)
        po_ids = self.env['purchase.order'].search([
            ('state', '=', 'draft'),
            ('order_line.product_id', 'in', self.top_product.ids),
        ])
        self.assertFalse(po_ids)
        # continue with normal production
        self.production.with_context(
            test_mrp_manual_procurement_subcontractor=True
        ).button_start_procurement()
        # run scheduler to start orderpoint rule to check RDP are not created
        # for top product
        with mute_logger('odoo.addons.stock.models.procurement'):
            self.procurement_model.run_scheduler()
        to_confirm_po_ids = self.env['purchase.order'].search([
            ('order_line.product_id', 'in', self.top_product.ids),
        ])
        self.assertFalse(to_confirm_po_ids)

    def test_03_mo_from_sale_with_subcontracting_and_orderpoint(self):
        # remove mto route from top product and create an orderpoint
        self.top_product.write({
            'route_ids': [
                (3, self.env.ref('stock.route_warehouse0_mto').id),
            ],
        })
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'OPx',
            'product_id': self.top_product.id,
            'product_min_qty': 0,
            'product_max_qty': 0,
        })
        # do test
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
        })
        self._create_sale_order_line(sale_order, self.top_product, 3)
        sale_order.with_context(
            test_mrp_manual_procurement_subcontractor=True
        ).action_confirm()
        # check procurement has not created RDP, even launching scheduler
        # (which will do nothing anyway)
        with mute_logger('odoo.addons.stock.models.procurement'):
            self.procurement_model.run_scheduler()
        self.production = self.env['mrp.production'].search(
            [('product_id', '=', self.top_product.id)])
        self.assertTrue(self.production)
        self.assertTrue(self.production.is_stopped)
        po_ids = self.env['purchase.order'].search([
            ('state', '=', 'draft'),
            ('order_line.product_id', 'in', self.top_product.ids),
        ])
        self.assertFalse(po_ids)
        # continue production with subcontrator
        procure_form = Form(
            self.env["mrp.production.procure.subcontractor"].with_context(
                active_id=self.production.id,
                active_ids=[self.production.id],
            )
        )
        procure_form.subcontractor_id = self.subcontractor_partner2
        wizard = procure_form.save()
        wizard.action_done()
        to_confirm_po_ids = self.env['purchase.order'].search([
            ('order_line.product_id', 'in', self.top_product.ids),
        ])
        self.assertEqual(len(to_confirm_po_ids), 1)
        # check vendor is equal to selected subcontractor
        self.assertEqual(to_confirm_po_ids.partner_id,
                         self.subcontractor_partner2)
        self.assertEqual(len(to_confirm_po_ids.mapped('order_line')), 1)
        to_confirm_po_ids.button_confirm()
        self.assertEqual(to_confirm_po_ids.state, 'purchase')

    def test_04_normal_mo_from_sale_with_orderpoint(self):
        # remove mto route from top product and create an orderpoint
        self.top_product.write({
            'route_ids': [
                (3, self.env.ref('stock.route_warehouse0_mto').id),
            ],
        })
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'OPx',
            'product_id': self.top_product.id,
            'product_min_qty': 0,
            'product_max_qty': 0,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
        })
        self._create_sale_order_line(sale_order, self.top_product, 3)
        sale_order.with_context(
            test_mrp_manual_procurement_subcontractor=True
        ).action_confirm()
        # check procurement has not created RDP, even launching scheduler
        # (which will do nothing anyway)
        with mute_logger('odoo.addons.stock.models.procurement'):
            self.procurement_model.run_scheduler()
        self.production = self.env['mrp.production'].search(
            [('product_id', '=', self.top_product.id)])
        self.assertTrue(self.production.is_stopped)
        po_ids = self.env['purchase.order'].search([
            ('state', '=', 'draft'),
            ('order_line.product_id', 'in', self.top_product.ids),
        ])
        self.assertFalse(po_ids)
        # continue with normal production
        self.production.with_context(
            test_mrp_manual_procurement_subcontractor=True
        ).button_start_procurement()
        # run scheduler to start orderpoint rule to check RDP are not created
        # for top product
        with mute_logger('odoo.addons.stock.models.procurement'):
            self.procurement_model.run_scheduler()
        to_confirm_po_ids = self.env['purchase.order'].search([
            ('order_line.product_id', 'in', self.top_product.ids),
        ])
        self.assertFalse(to_confirm_po_ids)
