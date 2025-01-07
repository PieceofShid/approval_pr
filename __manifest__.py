{
    'name': 'ICS Purchase Request',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Custom module purchase request for ICS Group',
    'author': 'pieceoftech, ICS',
    'website': 'https://ics-seafood.com',
    'license': 'AGPL-3',
    'depends': ['base', 'ics_company_unit', 'purchase_request'],
    'data': [
        'report/purchases_request_template.xml',
        'report/purchases_request_report.xml',
        'data/approval_config.xml',
        'data/approval_mail_template.xml',
        'security/purchase_request.xml',
        'security/ir.model.access.csv',
        'wizard/approval_wizard.xml',
        'views/purchase_request_view.xml',
        'views/approval_config.xml'
    ],
    'installable': True,
}