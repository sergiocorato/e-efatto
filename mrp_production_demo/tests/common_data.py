# Copyright 2020 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import SavepointCase


class TestProductionData(SavepointCase):
    @classmethod
    def setUpClass(cls):
        """
        #  top product [MANUF] (bom):
        #    -> 2pc subproduct2 [MANUF 1-2] = 2pc (bom) * produced_qty:
        #       -> 3pc subproduct_1_1 [MANUF 1-1-1] = 6pc * produced_qty
        #       -> 4pc subproduct_2_1 [MANUF 1-2-1] = 8pc * produced_qty
        #    -> 5pc subproduct1 [MANUF 1-1] = 5pc (bom):
        #       -> 2pc subproduct_1_1 [MANUF 1-1-1] = 10pc * produced_qty
        """
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.user_model = cls.env["res.users"].with_context(no_reset_password=True)
        cls.production_model = cls.env["mrp.production"]
        cls.procurement_model = cls.env["procurement.group"]
        cls.bom_model = cls.env["mrp.bom"]
        cls.stock_location_stock = cls.env.ref("stock.stock_location_stock")
        cls.manufacture_route = cls.env.ref("mrp.route_warehouse0_manufacture")
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.user.company_id.id)],
            limit=1,
        )
        cls.top_product = cls.env.ref(
            "mrp_production_demo.product_product_manufacture_1"
        )
        cls.warehouse.mto_pull_id.route_id.active = True
        cls.top_product.write(
            dict(
                route_ids=[
                    (
                        6,
                        0,
                        [
                            cls.warehouse.mto_pull_id.route_id.id,
                            cls.warehouse.manufacture_pull_id.route_id.id,
                        ],
                    ),
                ]
            )
        )
        cls.subproduct1 = cls.env.ref(
            "mrp_production_demo.product_product_manufacture_1_1"
        )
        cls.subproduct2 = cls.env.ref(
            "mrp_production_demo.product_product_manufacture_1_2"
        )
        cls.subproduct_1_1 = cls.env.ref(
            "mrp_production_demo.product_product_manufacture_1_1_1"
        )
        cls.subproduct_1_1.write(
            dict(
                route_ids=[
                    (
                        6,
                        0,
                        [
                            cls.warehouse.mto_pull_id.route_id.id,
                            cls.env.ref("purchase_stock.route_warehouse0_buy").id,
                        ],
                    ),
                ]
            )
        )
        cls.subproduct_2_1 = cls.env.ref(
            "mrp_production_demo.product_product_manufacture_1_2_1"
        )
        cls.main_bom = cls.env.ref("mrp_production_demo.mrp_bom_manuf_1")
        cls.sub_bom_phantom_1 = cls.env.ref("mrp_production_demo.mrp_bom_manuf_1_1")
        cls.sub_bom_phantom_2 = cls.env.ref("mrp_production_demo.mrp_bom_manuf_1_2")
        cls.sub_bom_normal_1 = cls.env.ref("mrp_production_demo.mrp_bom_manuf_1_3")
        cls.workcenter1 = cls.env["mrp.workcenter"].create(
            {
                "name": "Base Workcenter",
                "capacity": 1,
                "time_start": 10,
                "time_stop": 5,
                "time_efficiency": 80,
                "costs_hour": 23.0,
            }
        )
        cls.operation1 = cls.env["mrp.routing.workcenter"].create(
            {
                "name": "Operation 1",
                "workcenter_id": cls.workcenter1.id,
                "time_mode": "manual",
                "time_cycle_manual": 90,
                "sequence": 1,
            }
        )
        cls.mrp_user = cls.env.ref("base.user_demo")
        cls.mrp_user.write(
            {
                "groups_id": [(4, cls.env.ref("mrp.group_mrp_user").id)],
            }
        )

    def _update_product_qty(self, product, quantity):
        """Update Product quantity."""
        product_qty = self.env["stock.change.product.qty"].create(
            {
                "product_id": product.id,
                "product_tmpl_id": product.product_tmpl_id.id,
                "new_quantity": quantity,
            }
        )
        product_qty.change_product_qty()
        return product_qty
