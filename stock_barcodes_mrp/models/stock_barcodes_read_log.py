from odoo import fields, models


class StockBarcodesReadLog(models.Model):
    _inherit = 'stock.barcodes.read.log'

    mrp_id = fields.Many2one(
        comodel_name='mrp.production',
        string='Production',
    )
    produced_lot_id = fields.Many2one(
        comodel_name='stock.production.lot',
        string='Lot produced',
    )


class StockBarcodesReadLogLine(models.Model):
    _inherit = 'stock.barcodes.read.log.line'

    stock_move_id = fields.Many2one(
        comodel_name='stock.move',
        string='Stock move',
        readonly=True,
    )