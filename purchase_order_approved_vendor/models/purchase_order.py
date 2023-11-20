# Copyright 2020-2021 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    state = fields.Selection(selection=[
        ('draft', 'RFQ'),
        ('rfq sent', 'RFQ Sent'),
        ('rfq confirmed', 'RFQ Confirmed'),
        ('sent', 'Order Sent'),
        ('to approve', 'To Approve'),
        ('approved', 'Approved'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ])

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
        'approved': [('readonly', True)],
    }

    # Update the readonly states:
    origin = fields.Char(states=READONLY_STATES)
    date_order = fields.Datetime(states=READONLY_STATES)
    partner_id = fields.Many2one(states=READONLY_STATES)
    dest_address_id = fields.Many2one(states=READONLY_STATES)
    currency_id = fields.Many2one(states=READONLY_STATES)
    order_line = fields.One2many(states=READONLY_STATES)
    company_id = fields.Many2one(states=READONLY_STATES)
    picking_type_id = fields.Many2one(states=READONLY_STATES)

    @api.multi
    def action_rfq_send(self):
        res = super().action_rfq_send()
        if self.env.context.get('send_draft_rfq', False):
            res['context'].update({
                'mark_rfq_as_draft_sent': True,
                'mark_rfq_as_sent': False,
            })
        return res

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_rfq_as_draft_sent'):
            self.filtered(lambda o: o.state == 'draft').write({'state': 'rfq sent'})
        if self.env.context.get('mark_rfq_as_sent'):
            self.filtered(lambda o: o.state == 'approved').write({'state': 'sent'})
        return super(PurchaseOrder, self.with_context(mail_post_autofollow=True)
                     ).message_post(**kwargs)

    @api.multi
    def button_confirm_rfq(self):
        confirm_purchases = self.filtered(
            lambda p: p.company_id.purchase_approve_active)
        confirm_purchases.write({'state': 'rfq confirmed'})
        return super(PurchaseOrder, self - confirm_purchases).button_approve()

    @api.multi
    def button_confirm(self):
        # BUG nel caso questo modulo sia installato, il flag su Approvazione ordini
        # di acquisto non funziona se non è flaggato anche Stato Confermato extra!!!
        rfq_confirmed_orders = self.filtered(
            lambda x: x.state == 'rfq confirmed'
        )
        for order in rfq_confirmed_orders:
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step' \
                    or (order.company_id.po_double_validation == 'two_step'
                        and order.amount_total <
                        self.env.user.company_id.currency_id._convert(
                            order.company_id.po_double_validation_amount,
                            order.currency_id, order.company_id,
                            order.date_order or fields.Date.today())) \
                    or order.user_has_groups('purchase.group_purchase_manager'):
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
        return super(PurchaseOrder, self - rfq_confirmed_orders).button_confirm()

    @api.multi
    def print_quotation(self):
        if self.state == 'draft':
            self.write({'state': "rfq sent"})
        return self.env.ref('purchase.report_purchase_quotation').report_action(self)