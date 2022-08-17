# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class InvalidImportLinesWizard(models.TransientModel):
    _name = 'invalid.import.lines.wizard'
    _description = 'Invalid Import Lines Wizard'

    successful = fields.Boolean('Successful')
    successful_lines_message = fields.Char('Successful Lines Message')
    line_ids = fields.One2many('invalid.import.lines', 'wizard_id', string='Invalid Lines')


class InvalidImportLines(models.TransientModel):
    _name = 'invalid.import.lines'
    _description = 'Invalid Import Lines'

    file = fields.Char('File Name')
    line = fields.Char('Line')
    reason = fields.Text('Reason')
    wizard_id = fields.Many2one('invalid.lines.wizard', string='Wizard')
