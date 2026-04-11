{
    "name": "Geriatrics BL v2",
    "description": """
                    Hospital management system for Geriatrics clinics BL
                    """,
    "version": "0.15",
    "author": "Komiti / plusPMO",
    "category": "Medical",
    "depends": [
        "base",
        "web",
    ],
    "data": [
        "data/geriatrics_sequences.xml",
        "security/ir.model.access.csv",
        "views/menu.xml",
        "views/views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "geriatrics_v2/static/scss/geriatrics_form.scss",
            "geriatrics_v2/static/src/xml/geriatrics_patient_form.xml",
            "geriatrics_v2/static/src/js/geriatrics_act_window_readonly.js",
            "geriatrics_v2/static/src/js/geriatrics_patient_form_controller.js",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
