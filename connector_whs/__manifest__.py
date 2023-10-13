# Copyright 2020-21 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Connector WHS MSSQL",
    "version": "14.0.1.0.0",
    "author": "Sergio Corato",
    "website": "https://github.com/sergiocorato/e-efatto",
    "category": "other",
    "summary": "Connect Odoo stock with external warehouse management system",
    "depends": [
        "base_external_dbsource_mssql",
        "mrp",
        "product_supplierinfo_for_customer",
        "purchase_delivery_split_date",
        "purchase_stock",
        "repair",
        "sale_delivery_split_date",
        "sale_order_priority",
        "stock_move_line_auto_fill",
        "stock_picking_back2draft",
    ],
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/dbsource.xml",
        "views/hyddemo_mssql_log.xml",
        "views/hyddemo_whs_liste.xml",
        "views/product_template.xml",
        "views/stock.xml",
        "wizard/view_wizard_sync_stock_whs_mssql.xml",
        "data/cron.xml",
    ],
    "installable": True,
}
