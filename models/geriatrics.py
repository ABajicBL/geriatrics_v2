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

    # Deferred (nurse / insurance company): finish patient flow first, then uncomment and extend views.
    # is_nurse = fields.Boolean(string='Is Nurse', default=False)
    # is_insurance_company = fields.Boolean(string='Is Insurance Company', default=False)
    #
    # @api.onchange('is_Patient')
    # def _onchange_is_patient_role(self):
    #     if self.is_Patient:
    #         self.is_nurse = False
    #         self.is_insurance_company = False
    #
    # @api.onchange('is_nurse')
    # def _onchange_is_nurse_role(self):
    #     if self.is_nurse:
    #         self.is_Patient = False
    #         self.is_insurance_company = False
    #
    # @api.onchange('is_insurance_company')
    # def _onchange_is_insurance_role(self):
    #     if self.is_insurance_company:
    #         self.is_Patient = False
    #         self.is_nurse = False



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
    sex = fields.Selection([('m', 'Muški'), ('f', 'Ženski')], string='Pol', required=True)
    
    
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
    
    # citizen ID number 
    jmbg = fields.Char(string = "JMBG")

    # state ID document
    id_document = fields.Char(string = "Broj lične karte")

    # state ID expiration 
    id_document_expiration = fields.Date(string = "Datum isteka LK")

    # is state ID document due soon
    id_document_due_soon = fields.Boolean(string="Istek LK")

    # date of birth (fill_dob sets from JMBG when length is 13; invalid data is ignored)
    dob = fields.Date(string="Datum rođenja", required=True)

    @api.onchange("jmbg")
    def fill_dob(self):
        """Soft validation: only require 13 characters; build YYYY-MM-DD from list positions (DD MM YYY)."""
        if not self.jmbg or len(self.jmbg) != 13:
            return
        chars = list(self.jmbg)
        try:
            yyy = int(chars[4] + chars[5] + chars[6])
            year = 1000 + yyy if yyy >= 900 else 2000 + yyy
            jmbg_date = (
                str(year)
                + "-"
                + chars[2]
                + chars[3]
                + "-"
                + chars[0]
                + chars[1]
            )
            self.dob = jmbg_date
        except ValueError:
            return

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

    
    martial_status = fields.Selection([
        ('msingle', 'Neoženjen'),
        ('fsingle', 'Neudata'),
        ('mmarried', "Oženjen"),
        ('fmarried', "Udata"),
        ('mwidowed', "Udovac"),
        ('fwidowed', "Udovica"),
        ('mdivorced', 'Razveden'),
        ('fdivorced', 'Razvedena'),
        ('separated', 'Razdvojeni'),
        ('unknown', 'Nepoznato')
    ], string="Bračno stanje")

    @api.onchange("sex")
    def _onchange_sex_clear_maiden_name(self):
        if self.sex == "m":
            self.maiden_name = False

    maiden_name = fields.Char(string='Djevojačko prezime')
    father_name = fields.Char(string='Ime oca')
    mother_name = fields.Char(string='Ime majke')
    mother_surname = fields.Char(string='Djev. prez. majke')
    husband_name = fields.Char(string='Ime muža / žene')

    # address from res_partners
    # with related it is a proxy to the partner’s address
    city = fields.Char(related="partner_id.city", store=False, readonly=False, string="Grad")
    street = fields.Char(related="partner_id.street", store=False, readonly=False, string="Ulica")
    zip = fields.Char(related="partner_id.zip", store=False, readonly=False, string="Poš. broj")