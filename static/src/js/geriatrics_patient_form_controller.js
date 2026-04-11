/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { Layout } from "@web/search/layout";
import { FormStatusIndicator } from "@web/views/form/form_status_indicator/form_status_indicator";
import { FormCogMenu } from "@web/views/form/form_cog_menu/form_cog_menu";
import { ButtonBox } from "@web/views/form/button_box/button_box";
import { ViewButton } from "@web/views/view_button/view_button";
import { Field } from "@web/views/fields/field";
import { Widget } from "@web/views/widgets/widget";

/**
 * Patient form (js_class on medical.patient): explicit Edit when action uses open_form_readonly.
 * Re-declares static components so Owl resolves Layout / FormStatusIndicator / … for the custom template.
 */
export class GeriatricsPatientFormController extends FormController {
    static template = "geriatrics.GeriatricsPatientFormView";
    static components = {
        FormStatusIndicator,
        Layout,
        ButtonBox,
        ViewButton,
        Field,
        CogMenu: FormCogMenu,
        Widget,
    };

    get showGeriatricsEditButton() {
        const root = this.model?.root;
        if (!root) {
            return false;
        }
        return (
            Boolean(this.props.context?.open_form_readonly) &&
            !root.isNew &&
            !root.isInEdition &&
            this.canEdit
        );
    }

    async onGeriatricsEditClick() {
        await this.model.root.switchMode("edit");
    }
}

registry.category("views").add("geriatrics_patient_form", {
    ...formView,
    Controller: GeriatricsPatientFormController,
});
