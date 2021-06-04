# Copyright 2021 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import time
from odoo import api, fields, models, _


class ReplenishmentCost(models.Model):
    _name = 'replenishment.cost'
    _description = 'Product Replenishment Cost'

    name = fields.Char()
    last_update = fields.Datetime()
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.user.company_id,
    )
    product_ctg_ids = fields.Many2many(
        comodel_name='product.category',
        string='Product Categories'
    )
    log = fields.Text()

    @api.multi
    def update_products_standard_price(self):
        res = self.with_context(
            update_standard_price=True
        ).update_products_replenishment_cost()
        return res

    @api.multi
    def update_products_replenishment_cost(self):
        for repl in self:
            domain = [('type', 'in', ['product', 'consu'])]
            if repl.product_ctg_ids:
                domain.append(('categ_id', 'in', repl.product_ctg_ids.ids))
            products = self.env['product.product'].search(domain)
            started_at = time.time()
            products.update_managed_replenishment_cost()
            duration = time.time() - started_at
            repl.last_update = fields.Datetime.now()
            if not repl.name:
                repl.name = _('Update of %s' % repl.last_update)
            repl.log = 'Updated %s for %s products in %.2f minutes.' % (
                'replenishment cost and standard price'
                if self.env.context.get('update_standard_price')
                else 'replenishment cost',
                len(products),
                duration / 60,
            )
        return True