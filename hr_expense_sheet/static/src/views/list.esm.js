import {ExpenseListController} from "@hr_expense/views/list";
import {ListController} from "@web/views/list/list_controller";
import {ListRenderer} from "@web/views/list/list_renderer";
import {listView} from "@web/views/list/list_view";
import {onWillStart} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {user} from "@web/core/user";

patch(ExpenseListController.prototype, {
    displayCreateReport() {
        const usesSampleData = this.model.useSampleModel;
        const records = this.model.root.records;
        return (
            !usesSampleData &&
            records.length &&
            records.some((record) => record.data.state === "draft") &&
            records.every((record) => !record.data.sheet_id)
        );
    },
    displaySubmit() {
        const records = this.model.root.selection;
        return (
            super.displaySubmit() && records.every((record) => !record.data.sheet_id)
        );
    },
    displayApprove() {
        const records = this.model.root.selection;
        return (
            super.displayApprove() && records.every((record) => !record.data.sheet_id)
        );
    },
    displayPost() {
        const records = this.model.root.selection;
        return super.displayPost() && records.every((record) => !record.data.sheet_id);
    },
    async action_show_expenses_to_submit() {
        const records = this.model.root.selection;
        const res = await this.orm.call(
            this.model.config.resModel,
            "get_expenses_to_submit",
            [records.map((record) => record.resId)]
        );
        if (res) {
            await this.actionService.doAction(res, {});
        }
    },
});

export class ExpenseSheetListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        onWillStart(async () => {
            this.userIsExpenseTeamApprover = await user.hasGroup(
                "hr_expense.group_hr_expense_team_approver"
            );
            this.userIsAccountInvoicing = await user.hasGroup(
                "account.group_account_invoice"
            );
        });
    }
    displaySubmit() {
        const records = this.model.root.selection;
        return (
            records.length && records.every((record) => record.data.state === "draft")
        );
    }
    displayApprove() {
        const records = this.model.root.selection;
        return (
            this.userIsExpenseTeamApprover &&
            records.length &&
            records.every((record) => record.data.state === "submitted")
        );
    }
    async onClick(action) {
        const records = this.model.root.selection;
        const recordIds = records.map((a) => a.resId);
        const model = this.model.config.resModel;
        const context = {};
        if (action === "action_approve") {
            context.validate_analytic = true;
        }
        const res = await this.orm.call(model, action, [recordIds], {context: context});
        if (res) {
            await this.actionService.doAction(res, {
                additionalContext: {
                    dont_redirect_to_payments: 1,
                },
                onClose: async (closeParams) => {
                    if (closeParams?.noReload) {
                        return;
                    }
                    await this.model.root.load();
                    this.render(true);
                },
            });
        }
        await this.model.root.load();
    }
}
registry.category("views").add("hr_expense_sheet_tree", {
    ...listView,
    buttonTemplate: "hr_expense_sheet.ListButtons",
    Controller: ExpenseSheetListController,
    Renderer: ListRenderer,
});
