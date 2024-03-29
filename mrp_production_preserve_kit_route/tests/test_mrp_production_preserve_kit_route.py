# Copyright 2020 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import Form

from odoo.addons.mrp_production_demo.tests.common_data import TestProductionData


class TestMrpProductionPreserveKitRoute(TestProductionData):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        vendor = cls.env["res.partner"].create(
            {
                "name": "Partner #2",
            }
        )
        supplierinfo = cls.env["product.supplierinfo"].create(
            {
                "name": vendor.id,
            }
        )
        # Acoustic Bloc Screens, 16 on hand
        cls.product1 = cls.env.ref("product.product_product_25")
        # Large Cabinet, 250 on hand
        cls.product3 = cls.env.ref("product.product_product_6")
        # Drawer Black, 0 on hand
        cls.product4 = cls.env.ref("product.product_product_16")
        cls.product2 = cls.env["product.product"].create(
            {
                "name": "Component product",
                "default_code": "code1234",
                "type": "product",
                "purchase_ok": True,
                "route_ids": [
                    (4, cls.env.ref("purchase_stock.route_warehouse0_buy").id),
                    (4, cls.env.ref("stock.route_warehouse0_mto").id),
                ],
                "seller_ids": [(6, 0, [supplierinfo.id])],
            }
        )
        cls.product_bom = cls.env["product.product"].create(
            {
                "name": "Product with bom",
                "route_ids": [
                    (4, cls.env.ref("mrp.route_warehouse0_manufacture").id),
                    (4, cls.env.ref("stock.route_warehouse0_mto").id),
                ],
                "default_code": "code123",
                "type": "product",
                "sale_ok": True,
            }
        )
        cls.product_kit = cls.env["product.product"].create(
            {
                "name": "Product with kit bom",
                "route_ids": [
                    (4, cls.env.ref("mrp.route_warehouse0_manufacture").id),
                    (4, cls.env.ref("stock.route_warehouse0_mto").id),
                ],
                "default_code": "code1234",
                "type": "product",
                "sale_ok": True,
            }
        )
        kit_component_values = [
            {
                "product_id": x.id,
                "product_qty": 1,
            }
            for x in cls.product1 | cls.product2
        ]
        cls.kit = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.product_kit.product_tmpl_id.id,
                "code": cls.product_kit.default_code,
                "type": "phantom",
                "product_qty": 1,
                "product_uom_id": cls.env.ref("uom.product_uom_unit").id,
                "bom_line_ids": [(0, 0, x) for x in kit_component_values],
            }
        )
        bom_component_values = [
            {
                "product_id": x.id,
                "product_qty": 1,
            }
            for x in cls.product3 | cls.product4 | cls.product_kit
        ]
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.product_bom.product_tmpl_id.id,
                "code": cls.product_bom.default_code,
                "type": "normal",
                "product_qty": 1,
                "product_uom_id": cls.env.ref("uom.product_uom_unit").id,
                "bom_line_ids": [(0, 0, x) for x in bom_component_values],
            }
        )

    def test_so_bom_kit(self):
        man_order_form = Form(self.env["mrp.production"])
        man_order_form.product_id = self.product_bom
        man_order_form.product_uom_id = self.product_bom.uom_id
        man_order_form.bom_id = self.bom
        man_order_form.product_qty = 1
        man_order = man_order_form.save()
        man_order.action_confirm()
        self.assertEqual(len(man_order.move_raw_ids), 4)
        self.assertEqual(
            set(
                man_order.move_raw_ids.filtered(
                    lambda x: x.product_id != self.product2
                ).mapped("procure_method")
            ),
            {"make_to_stock"},
        )
        self.assertEqual(
            set(
                man_order.move_raw_ids.filtered(
                    lambda x: x.product_id == self.product2
                ).mapped("procure_method")
            ),
            {"make_to_order"},
        )
