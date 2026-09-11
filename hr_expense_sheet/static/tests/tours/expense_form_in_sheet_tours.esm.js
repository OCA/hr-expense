import {registry} from "@web/core/registry";
import {stepUtils} from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("do_not_create_zero_amount_expense_in_sheet", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "hr_expense.menu_hr_expense_root",
            "Go to the Expenses app"
        ),
        {
            content: "Go to My Reporting",
            trigger: 'button[data-menu-xmlid="hr_expense.menu_hr_expense_reports"]',
            run: "click",
        },
        {
            content: "Go to Expense Reports",
            trigger:
                '.dropdown-item[data-menu-xmlid="hr_expense_sheet.menu_hr_expense_report"]',
            run: "click",
        },
        {
            content: "Go to a report",
            trigger: '.o_data_row .o_data_cell[data-tooltip="report_for_tour"]',
            run: "click",
        },
        {
            content: "Add an expense line",
            trigger: 'div[name="expense_line_ids"] .o_field_x2many_list_row_add a',
            run: "click",
        },
        {
            content: "Create new expense line",
            trigger: ".modal .modal-footer .o_create_button",
            run: "click",
        },
        {
            content: "Add expense name",
            trigger: ".modal .modal-body .o_field_widget[name=name] input",
            run: "edit expense_for_tour",
        },
        {
            content: "Set total amount to zero",
            trigger:
                ".modal .modal-body .o_field_widget[name=total_amount_currency] input",
            run: "edit 0.0",
        },
        {
            content: "Select category to Expense",
            trigger: ".modal .modal-body .o_field_widget[name=product_id] input",
            run: "edit exp_gen",
        },
        {
            content: "Choose category to Expense",
            trigger:
                ".o_field_widget[name=product_id] .o-autocomplete--dropdown-menu li:contains(EXP_GEN)",
            run: "click",
        },
        {
            content: "Click Save",
            trigger: ".modal .modal-footer .o_form_button_save",
            run: "click",
        },
        {
            content: "Set total amount to ten",
            trigger:
                ".modal .modal-body .o_field_widget[name=total_amount_currency] input",
            run: "edit 10.0",
        },
        {
            content: "Click Save",
            trigger: ".modal .modal-footer .o_form_button_save",
            run: "click",
        },
        {
            content: "Wait the modal is closed",
            trigger: "body:not(:has(.modal))",
        },
        // Save the report
        ...stepUtils.saveForm(),
    ],
});
registry.category("web_tour.tours").add("hr_expense_sheet_access_rights_test_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "hr_expense.menu_hr_expense_root",
            "Go to the Expenses app"
        ),
        {
            content: "Go to My Expenses",
            trigger: 'button[data-menu-xmlid="hr_expense.menu_hr_expense_my_expenses"]',
            run: "click",
        },
        {
            content: "Go to My Reports",
            trigger:
                'a[data-menu-xmlid="hr_expense_sheet.menu_hr_expense_sheet_my_reports"]',
            run: "click",
        },
        {
            content: "Go to First Expense for employee",
            trigger: 'td[data-tooltip="First Expense for employee"]',
            run: "click",
        },
        {
            content: "Click Submit to Manager Button",
            trigger: ".o_expense_sheet_submit",
            run: "click",
        },
        {
            content: "Verify the expene sheet is submitted",
            trigger: '.o_arrow_button_current:contains("Submitted")',
        },
    ],
});
