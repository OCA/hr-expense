import {ExpenseListController} from "@hr_expense/views/list";

if (!ExpenseListController.prototype.displayCreateTrip) {
    ExpenseListController.prototype.displayCreateTrip = function () {
        const records = this.model.root.selection;
        return (
            this.userIsExpenseTeamApprover &&
            records.length &&
            records.every(
                (record) =>
                    ["draft", "submitted", "approved"].includes(record.data.state) &&
                    !record.data.trip_id
            )
        );
    };
}
