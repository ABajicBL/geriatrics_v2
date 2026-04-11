from odoo import models


class IrActionsActWindow(models.Model):
    _inherit = "ir.actions.act_window"

    def _get_readable_fields(self):
        # Whitelist extra keys for /web/action/load → _get_action_dict (see web/controllers/utils.clean_action).
        return super()._get_readable_fields() | {"flags"}

    def _get_action_dict(self):
        result = super()._get_action_dict()
        try:
            patient_action = self.env.ref("geriatrics_v2.action_geriatrics_patient")
        except ValueError:
            return result
        if result.get("id") != patient_action.id:
            return result
        # Optional client metadata; do not set result["readonly"] here — that can become props.readonly on the
        # form and blocks switching to edition (see static/src/js/geriatrics_act_window_readonly.js).
        result["flags"] = {"initial_mode": "view"}
        return result
