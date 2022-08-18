# -*- coding: utf-8 -*-

import xlrd
import csv
import base64

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.sh_global_custom_fields.models.models import ShCustomFieldModel


class FieldImportWizard(models.Model):
    _name = 'field.import.wizard'
    _description = 'Field Import Wizard'

    file = fields.Binary('File To Import', required=False)
    file_name = fields.Char("File Name")

    def _prepare_skipped_line(self, counter, file, reason):
        """
        Prepare skipped line values
        """
        return {
            'line': counter,
            'file': file,
            'reason': reason
        }

    def _read_xlsx_file(self, file, cell_data, file_name, required_columns):
        """
        Read .xlsx type files
        """
        vals = []
        counter = 1
        skipped_line_no = []
        try:
            workbook = xlrd.open_workbook(file_contents=base64.decodebytes(file))
            sheet = workbook.sheet_by_index(0)

            for row in range(sheet.nrows):
                if row >= 1:  # skip header lines
                    try:
                        data = {}
                        line_skipped = False
                        for rec in cell_data:
                            # Append data
                            if sheet.cell(row, rec).value != '' or (cell_data[rec] == 'selection_values' and sheet.cell(row, 2).value == 'selection'):
                                # Check name field is valid
                                if cell_data[rec] == 'name' and not sheet.cell(row, rec).value.startswith('x_'):
                                    skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid field name %s, field name must be starts with x_' % sheet.cell(row, rec).value))
                                    line_skipped = True
                                    continue
                                # Check field type field is valid
                                elif cell_data[rec] == 'field_type':
                                    if (sheet.cell(row, rec).value, sheet.cell(row, rec).value) not in ShCustomFieldModel.get_field_types(self):
                                        skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid field type %s' % sheet.cell(row, rec).value))
                                        line_skipped = True
                                        continue
                                    elif sheet.cell(row, rec).value in ['many2many', 'many2one'] and sheet.cell(row, 3).value not in self.env['ir.model'].search([]).mapped('model'):
                                        skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid model %s' % sheet.cell(row, 3).value))
                                        line_skipped = True
                                        continue
                                # Assign model
                                elif cell_data[rec] == 'ref_model_id':
                                    model_id = self.env['ir.model'].search([('model', '=', sheet.cell(row, rec).value)], limit=1)
                                    if model_id:
                                        data.update({cell_data[rec]: model_id.id})
                                        continue
                                # Check selection values
                                elif cell_data[rec] == 'selection_values':
                                    if sheet.cell(row, 2).value == 'selection':
                                        values = sheet.cell(row, rec).value.split(',')
                                        if not bool(sheet.cell(row, rec).value):
                                            skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid data for selection values %s. Selection values must be seperated with commas. eg: val 1, val 2, val 3' % sheet.cell(row, rec).value))
                                            line_skipped = True
                                        else:
                                            data.update({cell_data[rec]: [(0, 0, {'value': x.lower(), 'name': x.title()}) for x in values]})
                                        continue
                                # Check tab list field is valid
                                elif cell_data[rec] == 'tab_list' and (sheet.cell(row, rec).value, sheet.cell(row, rec).value) not in ShCustomFieldModel.get_tab_list(self):
                                    skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid tab %s' % sheet.cell(row, rec).value))
                                    line_skipped = True
                                    continue
                                # Check position field is valid
                                elif cell_data[rec] == 'sh_position_field':
                                    model_id = self.env['ir.model'].search([('model', '=', self._context['active_model'])], limit=1)
                                    field_id = self.env['ir.model.fields'].search([('field_description', '=', sheet.cell(row, rec).value), ('model_id', '=', model_id.id)], limit=1)
                                    if field_id:
                                        data.update({cell_data[rec]: field_id.id})
                                    else:
                                        skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid position field %s' % sheet.cell(row, rec).value))
                                        line_skipped = True
                                    continue
                                # Check position is valid
                                elif cell_data[rec] == 'sh_position' and sheet.cell(row, rec).value not in ['before', 'after']:
                                    skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid position %s' % sheet.cell(row, rec).value))
                                    line_skipped = True
                                    continue
                                # Check required or copy value is valid
                                elif cell_data[rec] in ['required', 'copy'] and sheet.cell(row, rec).value not in [1, 0]:
                                    skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid value for %s. Must be TRUE or FALSE' % cell_data[rec]))
                                    line_skipped = True
                                    continue
                                # Update data if no errors
                                data.update({cell_data[rec]: sheet.cell(row, rec).value})
                            # check the cell is required otherwise skip line
                            elif cell_data[rec] in required_columns:
                                skipped_line_no.append(self._prepare_skipped_line(counter, file_name, '%s column not found' % cell_data[rec]))
                                line_skipped = True
                        # Add data if no line skipped
                        if not line_skipped:
                            vals.append(data)
                    except Exception as e:
                        # skip line if an error occurred
                        skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Value is not valid - %s' % str(e)))
                counter += 1

        except Exception:
            raise UserError(_("Invalid xlsx file. Please check the file that you are trying to import!"))

        return vals, skipped_line_no

    def _read_csv_file(self, file, cell_data, file_name, required_columns):
        """
        Read .csv type files
        """
        vals = []
        counter = 1
        skipped_line_no = []
        try:
            file = str(base64.decodebytes(file).decode('utf-8'))
            csvreader = csv.reader(file.splitlines())

            i = 0
            for row in csvreader:
                if i >= 1:  # skip header lines
                    try:
                        data = {}
                        line_skipped = False
                        for rec in cell_data:
                            # Append data
                            if row[rec] != '' or (cell_data[rec] == 'selection_values' and row[2] == 'selection'):
                                # Check name field is valid
                                if cell_data[rec] == 'name' and not row[rec].startswith('x_'):
                                    skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid field name %s, field name must be starts with x_' % row[rec]))
                                    line_skipped = True
                                    continue
                                # Check field type field is valid
                                elif cell_data[rec] == 'field_type':
                                    if (row[rec], row[rec]) not in ShCustomFieldModel.get_field_types(self):
                                        skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid field type %s' % row[rec]))
                                        line_skipped = True
                                        continue
                                    elif row[rec] in ['many2many', 'many2one'] and row[3] not in self.env['ir.model'].search([]).mapped('model'):
                                        skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid model %s' % row[rec]))
                                        line_skipped = True
                                        continue
                                # Assign model
                                elif cell_data[rec] == 'ref_model_id':
                                    model_id = self.env['ir.model'].search([('model', '=', row[rec])], limit=1)
                                    if model_id:
                                        data.update({cell_data[rec]: model_id.id})
                                        continue
                                # Check selection values
                                elif cell_data[rec] == 'selection_values':
                                    if row[2] == 'selection':
                                        values = row[rec].split(',')
                                        if not bool(values):
                                            skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid data for selection values %s. Selection values must be seperated with commas. eg: val 1, val 2, val 3' % row[rec]))
                                            line_skipped = True
                                        else:
                                            data.update({cell_data[rec]: [
                                                (0, 0, {'value': x.lower(), 'name': x.title()}) for x in values]})
                                        continue
                                # Check tab list field is valid
                                elif cell_data[rec] == 'tab_list' and (row[rec], row[rec]) not in ShCustomFieldModel.get_tab_list(self):
                                    skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid tab %s' % row[rec]))
                                    line_skipped = True
                                    continue
                                # Check position field is valid
                                elif cell_data[rec] == 'sh_position_field':
                                    model_id = self.env['ir.model'].search([('model', '=', self._context['active_model'])], limit=1)
                                    field_id = self.env['ir.model.fields'].search([('field_description', '=', row[rec]),('model_id', '=', model_id.id)], limit=1)
                                    if field_id:
                                        data.update({cell_data[rec]: field_id.id})
                                    else:
                                        skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid position field %s' % row[rec]))
                                        line_skipped = True
                                    continue
                                # Check position is valid
                                elif cell_data[rec] == 'sh_position' and row[rec] not in ['before', 'after']:
                                    skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid position %s' % row[rec]))
                                    line_skipped = True
                                    continue
                                # Check required or copy value is valid
                                elif cell_data[rec] in ['required', 'copy']:
                                    if row[rec] in ['TRUE', 'FALSE']:
                                        data.update({cell_data[rec]: eval(row[rec].title())})
                                        continue
                                    else:
                                        skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid value for %s. Must be TRUE or FALSE' % cell_data[rec]))
                                        line_skipped = True
                                        continue
                                # Add data if no error occurred
                                data.update({cell_data[rec]: row[rec]})
                            # check the cell is required otherwise skip line
                            elif cell_data[rec] in required_columns:
                                skipped_line_no.append(self._prepare_skipped_line(counter, file_name, '%s column not found' % cell_data[rec]))
                                line_skipped = True
                        if not line_skipped:
                            vals.append(data)
                    except Exception as e:
                        # skip line if an error occurred
                        skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Value is not valid - %s' % str(e)))
                counter += 1
                i += 1

        except Exception:
            raise UserError(_("Invalid csv file. Please check the file that you are trying to import!"))

        return vals, skipped_line_no

    def _process_data(self, data):
        """
        Processing imported data and create fields
        """
        custom_field_model_obj = self.env['sh.custom.field.model']
        for rec in data:
            active_model = self._context.get('active_model', False)
            active_model_id = self.env['ir.model'].search([('model', '=', active_model)])
            rec_data = [{
                'name': rec.get('name', False),
                'field_description': rec.get('field_description', False),
                'field_type': rec.get('field_type', False),
                'ref_model_id': rec.get('ref_model_id', False),
                'tab_list': rec.get('tab_list', False),
                'sh_position_field': rec.get('sh_position_field', False),
                'sh_position': rec.get('sh_position', False),
                'field_help': rec.get('field_help', False),
                'required': rec.get('required', False),
                'copied': rec.get('copied', False),
                'sh_selection_ids': rec.get('selection_values', False),
                'model': active_model,
                'model_id': active_model_id.id,
                'parent_model': active_model,
                'parent_view_id': self.env['ir.ui.view'].sudo().default_view(active_model, 'form'),
            }]
            custom_field = custom_field_model_obj.sudo().with_context(self._context).create(rec_data)
            custom_field.onchage_sh_position_field()
            custom_field.create_fields()

    def action_import(self):
        """
        Import read data to the database
        """
        def _get_data(file, file_data, file_name, req_columns):
            """
            Get data for the given file
            """
            try:
                file_extension = file_name.split('.')[-1]
                if file_extension == 'xlsx':
                    return self._read_xlsx_file(file, file_data, file_name, req_columns)
                elif file_extension == 'csv':
                    return self._read_csv_file(file, file_data, file_name, req_columns)
                else:
                    raise UserError(_('Selected file type is invalid. Only xlsx or csv files can be imported!'))
            except Exception as error:
                raise ValidationError(_("Following error occurred when importing file:\n\n%s" % error))

        if self.file:
            # Read, extract and process field data
            cell_data = {
                0: 'name',
                1: 'field_description',
                2: 'field_type',
                3: 'ref_model_id',
                4: 'tab_list',
                5: 'sh_position_field',
                6: 'sh_position',
                7: 'field_help',
                8: 'required',
                9: 'copied',
                10: 'selection_values'
            }
            required_columns = ['name', 'field_description', 'field_type', 'sh_position_field', 'sh_position']
            data, invalid_lines = _get_data(self.file, cell_data, self.file_name, required_columns)
            # Process data
            self._process_data(data)
        else:
            raise UserError(_('Please add a file to import!'))

        # Prepare invalid lines
        invalid_lines = [(0, 0, x) for x in invalid_lines]

        # return status popup
        return {
            'name': 'Import Status',
            'view_mode': 'form',
            'res_model': 'invalid.import.lines.wizard',
            'domain': [],
            'context': {
                'default_line_ids': invalid_lines,
                'default_successful_lines_message': '%s lines successfully imported' % len(data),
                'default_successful': True if not bool(invalid_lines) else False
            },
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def download_templates(self):
        """
        Download the sample templates
        """
        file_name = 'Field Import Sample.csv' if 'csv' in self._context else 'Field Import Sample.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'name': 'Sample Import Template',
            'url': '/custom_field_import/static/src/samples/' + file_name + '?download=true',
        }
