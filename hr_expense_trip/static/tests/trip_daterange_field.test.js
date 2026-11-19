import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
} from "@web/../tests/web_test_helpers";
import {describe, expect, test} from "@odoo/hoot";
import {mockDate, mockTimeZone} from "@odoo/hoot-mock";
import {defineMailModels} from "@mail/../tests/mail_test_helpers";
import {queryAllValues} from "@odoo/hoot-dom";

describe.current.tags("desktop");

class Trip extends models.Model {
    _name = "hr.trip";

    start_date = fields.Datetime({string: "Start", required: true});
    end_date = fields.Datetime({string: "End", required: true});

    _records = [{id: 1, start_date: "2026-03-02 08:30:00", end_date: false}];
}

defineMailModels();
defineModels([Trip]);

const arch = `
    <form>
        <field name="start_date" widget="trip_daterange"
               options="{'end_date_field': 'end_date'}"/>
    </form>`;

describe("hr_expense_trip", () => {
    test("empty start and end dates default to midnight", async () => {
        mockDate("2026-03-10 14:37:00", 0);
        mockTimeZone(0);
        await mountView({type: "form", resModel: "hr.trip", arch});

        await contains("[data-field=start_date]").click();
        expect(queryAllValues(".o_time_picker_input")).toEqual(["0:00", "0:00"]);

        await contains(".o_date_item_cell:text(12)").click();
        await contains(".o_date_item_cell:text(14)").click();
        // Values that are not being edited are shown as buttons
        expect("[data-field=start_date]").toHaveText("Mar 12, 12:00 AM");
        expect("[data-field=end_date]").toHaveValue("03/14/2026 00:00:00");
    });

    test("existing time is kept", async () => {
        mockDate("2026-03-10 14:37:00", 0);
        mockTimeZone(0);
        await mountView({type: "form", resModel: "hr.trip", resId: 1, arch});

        await contains("[data-field=start_date]").click();
        expect(queryAllValues(".o_time_picker_input")).toEqual(["8:30", "0:00"]);
    });
});
