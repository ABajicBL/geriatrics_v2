How the explicit "Edit" button is added (Geriatrics v2, Odoo 19)
================================================================

Goal
----
When patients are opened from the Geriatrics menu action, existing records
should appear in view-first (readonly) mode. The standard Odoo 19 form UI
does not always make "switch to edition" obvious, so we add a visible Edit
button only in that situation.

Overview (three pieces)
-----------------------
1. Context flag on the window action  ->  tells the client "this flow wants
   readonly-first for existing records".

2. A small JS patch on the form model  ->  sets relational model mode to
   "readonly" when that flag is set and a record id exists (Create stays
   editable because new records have no resId).

3. Custom form view (js_class)        ->  duplicate of the stock FormView
   template plus a bar with an Edit button, and a controller subclass that
   shows the bar and calls switchMode('edit') on click.

Details
-------

A) Action context (views/menu.xml)
   The act_window record action_geriatrics_patient has:
     context: {'open_form_readonly': True}
   That dict is merged into props.context for list/form controllers when the
   user opens the action.

B) Readonly-first without locking the form forever (static/src/js/
   geriatrics_act_window_readonly.js)
   FormController.modelParams is patched so that when open_form_readonly is
   truthy and resId is set, the form relational model is started in
   config.mode = "readonly". We avoid putting readonly on the action or list in
   a way that maps to props.readonly on the form, because that can keep fields
   readonly even after trying to edit.

C) Tie the patient form to our client-side implementation (views/views.xml)
   The medical.patient form view root element includes:
     js_class="geriatrics_patient_form"
   The web client looks up js_class in the views registry.

D) Register the custom form view (static/src/js/geriatrics_patient_form_
   controller.js)

   What we do (checklist)
   - Import formView from @web/views/form/form_view and FormController from
     @web/views/form/form_controller.
   - Define GeriatricsPatientFormController extending FormController with:
       static template = "geriatrics.GeriatricsPatientFormView"
     Because the template is not the default web.FormView, we must set
       static components = { ... }
     with the same components as stock FormController (Layout, Field,
     FormStatusIndicator, CogMenu, ButtonBox, ViewButton, Widget). Otherwise
     Owl can throw lifecycle errors when rendering the duplicated template.
   - Getter showGeriatricsEditButton: true when context has open_form_readonly,
     the record is not new, the record is not already in edition, and canEdit.
     Uses this.model?.root so the getter is safe before the model is ready.
   - Method onGeriatricsEditClick: await this.model.root.switchMode("edit").
   - registry.category("views").add("geriatrics_patient_form", {
       ...formView,
       Controller: GeriatricsPatientFormController,
     });

   Why step D is necessary (not optional glue)
   ----------------------------------------------------------------
   1) js_class is only a name; something must implement it
      Step C puts js_class="geriatrics_patient_form" on the form arch. The web
      client does not magically know what that string means. It resolves the
      name in registry.category("views"). If nothing is registered under that
      key, you get a broken or fallback form. Step D is the implementation that
      ties the database view to real Owl code.

   2) The Edit button needs a FormController subclass, not only XML
      Steps A and B only change context and how the relational model starts
      (readonly vs edit). They do not add DOM or click handlers. The form arch
      in the database cannot call this.model.root.switchMode("edit") or read
      reactive getters on the controller. Putting a bare <button> in the arch
      would be a server-side button action, not the same as switching the OWL
      form controller mode. So we extend FormController and add methods and a
      getter the QWeb template can bind to (t-if, t-on-click).

   3) We must register a full form view definition, not only a class
      Odoo's form view is a bundle: Controller, Renderer, Compiler, default
      props, hooks, etc. The export `formView` from @web/views/form/form_view
      is that bundle. We spread ...formView and replace only Controller so all
      the stock behaviour (field rendering, notebook, buttons, status indicator
      wiring) stays identical. If you skipped this and tried to hand-roll a
      minimal registry entry, you would likely omit required pieces and break
      the form.

   4) A custom static template forces the static components map
      Stock FormController uses static template = "web.FormView". Our template
      duplicates that markup but adds the Edit bar and lives under another
      t-name ("geriatrics.GeriatricsPatientFormView"). In Owl, subcomponents used
      in a template (Layout, Field, CogMenu, ...) must be known on the class that
      owns that template. When you point a subclass at a different template
      string, relying on inheritance alone to supply static components is
      fragile; re-declaring static components to match stock FormController
      ensures every tag in the copied QWeb resolves and avoids uncaught Owl
      lifecycle errors.

   5) The registry key must match js_class exactly
      The string in views.xml (geriatrics_patient_form) and the first argument
      to registry.category("views").add(...) must be the same. That is the only
      link between the XML view definition loaded from the server and the
      client-side view class loaded from assets.

E) Template with the Edit bar (static/src/xml/geriatrics_patient_form.xml)
   - t-name="geriatrics.GeriatricsPatientFormView" matches the controller
     static template string.
   - Above the standard Layout block, a div with t-if="showGeriatricsEditButton"
     contains a primary button with t-on-click="onGeriatricsEditClick".
   - The rest of the file is a full copy of the stock FormView structure so we
     do not rely on fragile primary inheritance + xpath against core XML.

F) Assets order (__manifest__.py)
   Under web.assets_backend, list the QWeb/XML template file BEFORE the
   controller JS that references it, so the template is compiled and
   available when the module loads.

Behaviour summary
-----------------
- Open patient from Geriatrics action with an existing id: form loads in
  readonly mode; Edit bar appears; click Edit -> switchMode('edit').
- Create new patient: no resId, patch does not force readonly mode; Edit bar
  hidden (isNew); user works in edit mode as usual.

Optional follow-ups
-------------------
- Wrap the button label with _t("Edit") in the template or pass from JS for
  full translation.
- Adjust SCSS (static/scss/geriatrics_form.scss) for spacing or bar styling.
