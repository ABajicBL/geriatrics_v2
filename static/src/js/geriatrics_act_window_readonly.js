/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

/**
 * Patient window action: open existing records in readonly form, new records in edit.
 *
 * Problem
 * -------
 * Writable users get mono-record forms in "edit" by default. We cannot use `<form edit="0">` on the patient form
 * because creation must stay editable. Injecting `flags` / `readonly` on `ir.actions.act_window` in Python is not
 * sufficient in Odoo 19: `/web/action/load` uses `_get_action_dict()` (see models/ir_actions.py), but the web
 * client's `action_service` does not set the relational model to readonly on list→form by itself.
 *
 * Why not pass props.readonly from the list (switchView)?
 * -------------------------------------------------------
 * `props.readonly` on the form is wired into every Field: widgets stay readonly while that prop is true, even
 * after the record switches to edition. There is no separate "Edit" toolbar button in Odoo 19 like in older
 * webclient; you enter edition by interacting with the record (e.g. focusing a field). With `readonly: true` on
 * the view props, that never works. Initial "view" mode must be done via relational model `config.mode` only.
 *
 * Why menu.xml uses context.open_form_readonly
 * ----------------------------------------------
 * Merged into `props.context` on views; this patch reads it so we do not hardcode action XML ids in JS.
 *
 * Solution
 * ----------
 * `menu.xml`: `context: { open_form_readonly: True }`.
 * Patch `FormController.modelParams` only: when the flag is set and `resId` is set, set `config.mode` to
 * `"readonly"` so the form opens like a saved record, but `props.readonly` stays false so the user can switch
 * to edition normally. No `resId` (Create) keeps default edit behaviour.
 */

patch(FormController.prototype, {
    get modelParams() {
        const params = super.modelParams;
        if (
            this.props.context?.open_form_readonly &&
            this.props.resId &&
            params.config?.isMonoRecord
        ) {
            return {
                ...params,
                config: {
                    ...params.config,
                    mode: "readonly",
                },
            };
        }
        return params;
    },
});
