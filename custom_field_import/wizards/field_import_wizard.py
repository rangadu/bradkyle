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
                            if sheet.cell(row, rec).value != '':
                                # Check name field is valid
                                if cell_data[rec] == 'name' and not sheet.cell(row, rec).value.startswith('x_'):
                                    skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid field name %s, field name must be starts with x_' % sheet.cell(row, rec).value))
                                    line_skipped = True
                                    continue
                                # Check field type field is valid
                                elif cell_data[rec] == 'field_type' and (sheet.cell(row, rec).value, sheet.cell(row, rec).value) not in ShCustomFieldModel.get_field_types(self):
                                    skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid field type %s' % sheet.cell(row, rec).value))
                                    line_skipped = True
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
                            if row[rec] != '':
                                # Check name field is valid
                                if cell_data[rec] == 'name' and not row[rec].startswith('x_'):
                                    skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid field name %s, field name must be starts with x_' % row[rec]))
                                    line_skipped = True
                                    continue
                                # Check field type field is valid
                                elif cell_data[rec] == 'field_type' and (row[rec], row[rec]) not in ShCustomFieldModel.get_field_types(self):
                                    skipped_line_no.append(self._prepare_skipped_line(counter, file_name, 'Invalid field type %s' % row[rec]))
                                    line_skipped = True
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
        Processing imported data
        """
        pass

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

        invalid_lines = []
        if self.file:
            # Read, extract and process field data
            cell_data = {
                0: 'name',
                1: 'field_description',
                2: 'field_type',
                3: 'tab_list',
                4: 'sh_position_field',
                5: 'sh_position',
                6: 'field_help',
                7: 'required',
                8: 'copied',
            }
            required_columns = ['name', 'field_description', 'field_type', 'sh_position_field', 'sh_position']
            data, invalid_lines = _get_data(self.file, cell_data, self.file_name, required_columns)
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

    # Download template files
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

    def create_fields(self, field_data=None):
        """
        Create fields from the data coming from excel/ csv file
        """
        if field_data.get('tab_list', False) and field_data.get('sh_position_field', False):
            raise UserError("Please Select Either Tab or Field !")

        if not field_data.get('tab_list', False) and not field_data.get('sh_position_field', False):
            raise UserError("Please Select Tab or Field !")
        groups_obj = self.env['res.groups'].search([])
        grp_str = ''
        cnt = 0

        for res_grp in groups_obj:
            for fld_grp in field_data.get('groups', False):

                dict = fld_grp.get_external_id()
                for k, v in dict.items():

                    if res_grp.id == k:
                        if cnt == 0:
                            grp_str += v
                        else:
                            grp_str += ',' + str(v)

                        cnt += 1
        if field_data.get('sh_position_field', False):
            if not field_data.get('sh_position', False):
                raise UserError("Please Select Position !")

        vals = {
            'name': field_data.get('name', False),
            'field_description': field_data.get('field_description', False),
            'model_id': field_data.get('model_id', False),
            'help': field_data.get('field_help', False),
            'ttype': field_data.get('field_type', False),
            'relation': field_data.get('ref_model_id', False),
            'required': field_data.get('required', False),
            'copied': field_data.get('copied', False),
            'domain': field_data.get('task_domain', False),
        }
        if field_data.get('field_type', False) == 'color':
            vals.update({'ttype': 'char'})
        if field_data.get('field_type', False) == 'signature':
            vals.update({'ttype': 'binary'})
        ir_mdl_flds_obj = self.env['ir.model.fields'].sudo().create(vals)

        # Need to create record for ir model field selection----------
        if field_data.get('sh_selection_ids', False):
            field_selection_obj = self.env['ir.model.fields.selection']
            for selection_id in field_data.get('sh_selection_ids', False):
                field_selection_obj.create({
                    'field_id': ir_mdl_flds_obj.id,
                    'value': selection_id.value,
                    'name': selection_id.name,
                    'sequence': selection_id.sequence
                })

        # FIXME from here
        if ir_mdl_flds_obj:
            self.ir_model_fields_obj = ir_mdl_flds_obj.id

        if self.inherit_view_obj:
            inherit_id = self.inherit_view_obj
        else:
            #             inherit_id = self.env.ref('project.edit_project')
            inherit_id = self.parent_view_id
        group_str_field_arch_base = _('<?xml version="1.0"?>'
                                      '<data>'
                                      '<field name="%s" position="%s">'
                                      '<field name="%s" groups="%s" widget="%s"/>'
                                      '</field>'
                                      '</data>')

        group_str_tab_arch_base = _('<?xml version="1.0"?>'
                                    '<data>'
                                    '<xpath expr="//form/sheet/notebook/page[@name=\'%s\']/group" position="inside">'
                                    '<group><field name="%s" groups="%s" widget="%s"/></group>'
                                    '</xpath>'
                                    '</data>')

        no_group_str_field_arch_base = _('<?xml version="1.0"?>'
                                         '<data>'
                                         '<field name="%s" position="%s">'
                                         '<field name="%s" widget="%s"/>'
                                         '</field>'
                                         '</data>')

        no_group_str_tab_arch_base = _('<?xml version="1.0"?>'
                                       '<data>'
                                       '<xpath expr="//form/sheet/notebook/page[@name=\'%s\']/group" position="inside">'
                                       '<group><field name="%s" widget="%s"/></group>'
                                       '</xpath>'
                                       '</data>')

        if self.field_type == 'selection' and self.widget_selctn_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_selctn_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_selctn_selection)
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_selctn_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_selctn_selection)

        elif self.field_type == 'char' and self.widget_char_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_char_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_char_selection)

            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_char_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_char_selection)
        elif self.field_type == 'float' and self.widget_float_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_float_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_float_selection)

            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_float_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_float_selection)

        elif self.field_type == 'text' and self.widget_text_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_text_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_text_selection)
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_text_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_text_selection)

        elif self.field_type == 'binary' and self.widget_binary_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_binary_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_binary_selection)
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_binary_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_binary_selection)

        elif self.field_type == 'many2many' and self.widget_m2m_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_m2m_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_m2m_selection)
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_m2m_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_m2m_selection)

        elif self.field_type == 'many2one' and self.widget_m2o_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_m2o_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_m2o_selection)

            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_m2o_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_m2o_selection)
        elif self.field_type == 'color':
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, 'color')
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, 'color')
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, 'color')
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, 'color')

        elif self.field_type == 'signature':
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, 'signature')
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, 'signature')
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, 'signature')
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, 'signature')

        else:  # Other Field Types
            if grp_str:
                if self.sh_position_field:
                    arch_base = _('<?xml version="1.0"?>'
                                  '<data>'
                                  '<field name="%s" position="%s">'
                                  '<field name="%s" groups="%s"/>'
                                  '</field>'
                                  '</data>') % (self.sh_position_field.name, self.sh_position, self.name, grp_str)
                else:
                    arch_base = _('<?xml version="1.0"?>'
                                  '<data>'
                                  '<xpath expr="//form/sheet/notebook/page[@name=\'%s\']/group" position="inside">'
                                  '<group><field name="%s" groups="%s" /></group>'
                                  '</xpath>'
                                  '</data>') % (self.tab_list, self.name, grp_str)
            else:
                if self.sh_position_field:
                    arch_base = _('<?xml version="1.0"?>'
                                  '<data>'
                                  '<field name="%s" position="%s">'
                                  '<field name="%s"/>'
                                  '</field>'
                                  '</data>') % (self.sh_position_field.name, self.sh_position, self.name)
                else:
                    arch_base = _('<?xml version="1.0"?>'
                                  '<data>'
                                  '<xpath expr="//form/sheet/notebook/page[@name=\'%s\']/group" position="inside">'
                                  '<group><field name="%s"/></group>'
                                  '</xpath>'
                                  '</data>') % (self.tab_list, self.name)

        model = self.parent_model
        irui_vew_obj = self.env['ir.ui.view'].sudo().create({'name': 'custom.dynamic.fields',
                                                             'type': 'form',
                                                             'model': model,
                                                             'mode': 'extension',
                                                             'inherit_id': inherit_id.id,
                                                             'arch_base': arch_base,
                                                             'active': True})
        if irui_vew_obj:
            self.ir_ui_view_obj = irui_vew_obj.id

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }