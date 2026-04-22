from odoo import models, fields, api


def _give_last_birthday(dob, year):
    try:
        return dob.replace(year=year)
    except ValueError:
        # Only fails for 29 Feb when `year` is not a leap year; use 28 Feb.
        return dob.replace(year=year, day=dob.day - 1)



class res_partners(models.Model):
    _inherit = 'res.partner'

    # Partner form: user sets the toggle. Many2one quick-create passes context default_is_patient (see medical.patient.partner_id).
    is_patient = fields.Boolean(string='Pacijent', default=False)
    is_institution = fields.Boolean(string='Institucija', default=False)

    # if partner is patient contract are shown on the form
    medical_patient_ids = fields.One2many(
        comodel_name='medical.patient',
        inverse_name='partner_id',
        string='Geriatrics patient records',
    )
    contract_as_patient_ids = fields.One2many(
        comodel_name='medical.patient.contract',
        inverse_name='patient_partner_id',
        string='Ugovori (korisnik)',
    )




    # partner according to the contract model can be a contractor and/or a requestor
    # contractor and requestor roles are derived here from medical.patient.contract roles (not set manually).
    # for them contracts are shown on the partner form
    contract_as_requestor_ids = fields.One2many(
        comodel_name='medical.patient.contract',
        inverse_name='requested_by',
        string='Ugovori (podnosilac)',
    )
    contract_as_contractor_ids = fields.One2many(
        comodel_name='medical.patient.contract',
        inverse_name='contractor',
        string='Ugovori (potpisnik)',
    )
    is_requestor = fields.Boolean(
        string='Podnosilac (iz ugovora)',
        compute='_compute_signatory_flags',
        store=True,
    )
    is_contractor = fields.Boolean(
        string='Potpisnik (iz ugovora)',
        compute='_compute_signatory_flags',
        store=True,
    )

    contract_as_signatory_ids = fields.Many2many(
        comodel_name='medical.patient.contract',
        compute='_compute_contract_as_signatory_ids',
        string='Ugovori',
    )

    @api.depends('contract_as_contractor_ids', 'contract_as_requestor_ids')
    def _compute_signatory_flags(self):
        for partner in self:
            partner.is_contractor = bool(partner.contract_as_contractor_ids)
            partner.is_requestor = bool(partner.contract_as_requestor_ids)

    @api.depends('contract_as_requestor_ids', 'contract_as_contractor_ids')
    def _compute_contract_as_signatory_ids(self):
        for partner in self:
            partner.contract_as_signatory_ids = (
                partner.contract_as_requestor_ids | partner.contract_as_contractor_ids
            )

    # special form layout if partner is in geriatric role
    is_geriatrics = fields.Boolean(
        string='Geriatrics element',
        compute='_compute_is_geriatrics',
    )

    @api.depends(
        'is_patient',
        'is_institution',
        'contract_as_contractor_ids',
        'contract_as_requestor_ids',
        'contract_as_patient_ids',
    )
    def _compute_is_geriatrics(self):
        for partner in self:
            partner.is_geriatrics = bool(
                partner.is_patient
                or partner.is_institution
                or partner.contract_as_contractor_ids
                or partner.contract_as_requestor_ids
                or partner.contract_as_patient_ids
            )


    # default country = Bosnia and Herzegovina
    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if 'country_id' in fields_list and not values.get('country_id'):
            ba = self.env['res.country'].search([('code', '=', 'BA')], limit=1)
            if ba:
                values['country_id'] = ba.id
        return values

    # user selects if partner is patient or institution (can choose one or none) 
    @api.onchange('is_institution')
    def _onchange_is_institution(self):
        if self.is_institution:
            self.is_patient = False

    @api.onchange('is_patient')
    def _onchange_is_patient(self):
        if self.is_patient:
            self.is_institution = False

    @api.constrains('is_patient', 'is_institution')
    def _check_patient_institution_exclusive(self):
        for partner in self:
            if partner.is_patient and partner.is_institution:
                raise ValidationError(_('Kontakt ne može biti i pacijent i institucija.'))





class patient_contract(models.Model):
    _name = 'medical.patient.contract'
    _description = 'Patient contract'

    # use contract_ref as display name
    _rec_name = 'contract_ref'
    
    contract_ref = fields.Char(string='Oznaka ili broj ugovora', required=True)
    contract_type = fields.Selection([('dependent', 'Zavisan'), ('independent', 'Nezavisan')], string="Tip")

    patient = fields.Many2one(comodel_name='medical.patient', string='Korisnik ugovora', required=True)
    patient_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Kontakt korisnika',
        related='patient.partner_id',
        store=True,
        index=True,
    )
    requested_by = fields.Many2one(comodel_name='res.partner', string='Podnosilac zahtjev')
    contractor = fields.Many2one(comodel_name='res.partner', string='Potpisnik ugovora', required=True)
    start_date = fields.Date(string='Početak ugovora', required=True, default=fields.Date.today())
    end_date = fields.Date(string='Kraj ugovor')
    status = fields.Selection([('draft','U pripremi'),('open', 'Aktivan'),('closed','Završen')], string='Status', default='draft')
    notes = fields.Text(string='Napomene')
    create_uid = fields.Many2one(comodel_name='res.users', string='Kreirao')
    create_date = fields.Datetime(string='Kreirano', readonly=True)

    def action_activate_contract(self):
        self.filtered(lambda c: c.status == 'draft').write({'status': 'open'})
        return True

    def action_terminate_contract(self):
        today = fields.Date.today()
        # self can contain several contract, so first filter open one
        self.filtered(lambda c: c.status == 'open').write({'status': 'closed', 'end_date': today})
        return True

    @api.constrains('patient', 'status')
    def _check_one_open_contract_per_patient(self):
        for contract in self:
            if contract.status != 'open':
                continue
            dup = self.search_count(
                [
                    ('id', '!=', contract.id),
                    ('patient', '=', contract.patient.id),
                    ('status', '=', 'open'),
                ]
            )
            if dup:
                raise ValidationError(
                    _('Već postoji aktivan ugovor za ovog korisnika (medicinski pacijent).')
                )

    @api.constrains('contractor', 'status')
    def _check_one_open_contract_per_contractor(self):
        for contract in self:
            if contract.status != 'open' or not contract.contractor:
                continue
            dup = self.search_count(
                [
                    ('id', '!=', contract.id),
                    ('contractor', '=', contract.contractor.id),
                    ('status', '=', 'open'),
                ]
            )
            if dup:
                raise ValidationError(
                    _('Već postoji aktivan ugovor gdje je ovaj kontakt potpisnik.')
                )




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
        domain=[('is_patient', '=', True)],         # filters only partners that are patients
        context={'default_is_patient': True},       # for a new created patient set is_patient=true
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