from odoo import models, fields, api

class res_partners(models.Model):
    _inherit = 'res.partner'

    is_Patient = fields.Boolean(string='Is Patient', default=True)
    contract_ids = fields.One2many(comodel_name='medical.patient.contract', inverse_name='partner_id', string='Contracts')



class patient_contract(models.Model):
    _name = 'medical.patient.contract'

    ref = fields.Char('Contract Reference', required=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string='Patient', required=True)
    start_date = fields.Date('Start Date', required=True, default=fields.Date.today())


class patient(models.Model):
    _name = 'medical.patient'
    _description = 'Patient'
    # naming field as name will break the image preview
    _rec_name = 'partner_id'
    # this field is alternative to the name field
    # it is reserved for pre-defined behaviors, it is connected with the display_name field, 
    # display_name is the name shown in the web client, and by default it follows the _rec_name field’s value, unless you override _compute_display_name.
    # _rec_name = 'partner_id' means that the display_name field will follow the partner_id field's value (patient name)

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Patient',
        required=True,
        domain=[('is_Patient', '=', True)],
        oldname='name',
    )
    sex = fields.Selection([('m', 'Male'), ('f', 'Female')], string='Sex', required=True)
    patient_id = fields.Char('ID', size=64, required=True)
    #photo = fields.Binary('Picture')
    photo = fields.Image(string='Photo')
    
