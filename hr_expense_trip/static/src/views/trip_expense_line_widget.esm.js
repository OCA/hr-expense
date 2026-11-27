/*
 * Based on the "expense_lines_widget" field widget of hr_expense in
 * odoo/odoo 18.0 (addons/hr_expense/static/src/views/expense_line_widget.js),
 * which was dropped from hr_expense in 19.0.
 *
 * hr_expense_sheet ports the same widget and registers it under the original
 * "expense_lines_widget" key, so this module uses its own names
 * ("trip_expense_lines_widget", TripExpenseLinesWidget) to avoid a duplicate
 * key in the fields registry when both modules are installed.
 */
import {X2ManyField, x2ManyField} from "@web/views/fields/x2many/x2many_field";
import {registry} from "@web/core/registry";

export class TripExpenseLinesWidget extends X2ManyField {
    setup() {
        super.setup();
        // Allow clicking a row to open the hr.expense form view.
        this.canOpenRecord = true;
    }

    get isMany2Many() {
        // Treat the field like a Many2many so the "Add" button opens a
        // selection dialog that lets users pick existing hr.expense records.
        return true;
    }
}

export const tripExpenseLinesWidget = {
    ...x2ManyField,
    component: TripExpenseLinesWidget,
    additionalClasses: ["o_field_many2many"],
};

registry.category("fields").add("trip_expense_lines_widget", tripExpenseLinesWidget);
