# Copyright 2022 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'Purchase sale link with mrp compatibility',
    'version': '12.0.1.0.2',
    'category': 'Purchase',
    'license': 'AGPL-3',
    'author': 'Sergio Corato',
    'website': 'https://efatto.it',
    'maintainers': ['sergiocorato'],
    'depends': [
        'crm_lead_product',
        'mrp_bom_evaluation',
        'purchase_stock',
        'sale_crm',
        'sale_stock',
    ],
    'data': [
        'views/purchase.xml',
        'views/crm_lead_line.xml',
    ],
    'installable': True,
}
