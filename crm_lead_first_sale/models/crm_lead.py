# Copyright 2023 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    first_sale_days = fields.Integer(
        compute="_compute_first_sale_days",
        store=True,
    )

    @api.multi
    @api.depends("create_date", "order_ids.date_sent", "order_ids.date_sent_calculated")
    def _compute_first_sale_days(self):
        for lead in self:
            first_sale_days = 0
            if lead.order_ids:
                dates_sent = lead.order_ids.mapped('date_sent')[0]
                if not dates_sent:
                    dates_sent = lead.order_ids.mapped('date_sent_calculated')
                if dates_sent:
                    first_sale_days = (
                        min(dates_sent)
                        - lead.create_date
                    ).days or 1

            lead.first_sale_days = first_sale_days
