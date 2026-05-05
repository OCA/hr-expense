import {X2ManyField, x2ManyField} from "@web/views/fields/x2many/x2many_field";
import {registry} from "@web/core/registry";

export class ExpenseLinesWidget extends X2ManyField {
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

export const expenseLinesWidget = {
    ...x2ManyField,
    component: ExpenseLinesWidget,
    additionalClasses: ["o_field_many2many"],
};

registry.category("fields").add("expense_lines_widget", expenseLinesWidget);
