from odoo import models, fields, api


def _give_last_birthday(dob, year):
    try:
        return dob.replace(year=year)
    except ValueError:
        # Only fails for 29 Feb when `year` is not a leap year; use 28 Feb.
        return dob.replace(year=year, day=dob.day - 1)



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
    
    
    # patient_id: official patient identifier, generated from ir.sequence (code: medical.patient.id),
    # e.g. prefix "P" plus the padded number defined on the sequence.
    # ir.sequence is a simple way to reduce duplicate IDs under concurrency; it is not the only or always the best approach (e.g. unique SQL constraints, UUIDs).
    # The default appears when opening a new form; each new form consumes the next number
    # (closing without saving leaves gaps in the sequence).
    def _default_patient_id(self):
        return self.env['ir.sequence'].next_by_code('medical.patient.id')
    
        
    patient_id = fields.Char('ID', size=64, required=True, default=_default_patient_id)
    
    
    #photo = fields.Binary('Picture')
    photo = fields.Image(string='Photo')
    
    # date of birth
    dob = fields.Date(string ='Datum rođenja', required=True)

    # deceased
    deceased = fields.Boolean(string='Preminuo', default=False)

    # death date
    dod = fields.Date(string='Datum smrti')

    age = fields.Char(string='Starost', compute='_compute_age')


    @api.depends('dob', 'dod', 'deceased')
    def _compute_age(self):
        today = fields.Date.today()
        for record in self:
            if not record.dob:
                record.age = False
                continue
            if record.deceased:
                if not record.dod:
                    record.age = False
                    continue
                end = record.dod
                suffix = ' (preminuo)'
            else:
                end = today
                suffix = ''
            start = record.dob
            if end < start:
                record.age = False
                continue

            last_birthday = _give_last_birthday(start, end.year)
            if last_birthday > end:
                last_birthday = _give_last_birthday(start, end.year - 1)

            years = last_birthday.year - start.year
            days = (end - last_birthday).days
            record.age = f"{years} years {days} days{suffix}"
