# -*- encoding: utf-8 -*-

{
    'name': 'Custom Fields Import',
    "summary": "Fields import with csv/xlsx file",
    'description': """
		Fields import option with csv/xlsx file
    """,
    'version': '15.0.1.0.0',
    'category': 'Uncategorized',
    'author': 'Ranga Dharmapriya',
    'email': 'rangadharmapriya@gmail.com',
    'depends': [
        'sh_global_custom_fields',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/field_import_wizard_view.xml',
        'wizards/invalid_import_lines_wizard_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
