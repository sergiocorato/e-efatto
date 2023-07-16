from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    is_subcontractable = fields.Boolean(
        compute='_compute_is_subcontractable',
        store=True,
        copy=False)
    proceed_to_production = fields.Boolean()

    @api.multi
    @api.depends('move_raw_ids.state', 'product_id.route_ids', 'state',
                 'product_id.seller_ids', 'proceed_to_production',
                 'purchase_order_id')
    def _compute_is_subcontractable(self):
        # stop procurement for all production order which product has a
        # purchase route and a subcontractor
        buy_route = self.env.ref("purchase_stock.route_warehouse0_buy")
        for production in self:
            # produce route is obviously already present
            is_subcontractable = bool(
                any(
                    x.is_subcontractor for x in
                    production.mapped("product_id.seller_ids")
                )
                and buy_route in production.product_id.route_ids
                and not production.purchase_order_id
                and not production.proceed_to_production
                and production.state == "confirmed"
            )
            production.is_subcontractable = is_subcontractable

    @api.multi
    def button_proceed_to_production(self):
        self.ensure_one()
        self.write({"proceed_to_production": True})
