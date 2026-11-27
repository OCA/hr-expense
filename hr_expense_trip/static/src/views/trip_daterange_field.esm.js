import {DateTimeField, dateRangeField} from "@web/views/fields/datetime/datetime_field";
import {DateTimePicker} from "@web/core/datetime/datetime_picker";
import {Time} from "@web/core/l10n/time";
import {patch} from "@web/core/utils/patch";
import {registry} from "@web/core/registry";

/**
 * Optional time used by the picker for empty values, instead of the current
 * hour. Without the prop, the standard behaviour is kept.
 */
patch(DateTimePicker.props, {
    defaultTime: {type: Object, optional: true},
});

patch(DateTimePicker.prototype, {
    getTimeValues(props) {
        const timeValues = super.getTimeValues(props);
        if (props.defaultTime) {
            for (const [index, value] of this.values.entries()) {
                if (!value && timeValues[index]) {
                    timeValues[index] = new Time(props.defaultTime);
                }
            }
        }
        return timeValues;
    },
});

export class TripDateRangeField extends DateTimeField {
    setup() {
        super.setup();
        // Trips start and end at midnight unless the user sets another time.
        this.state.defaultTime = {hour: 0, minute: 0, second: 0};
    }
}

export const tripDateRangeField = {
    ...dateRangeField,
    component: TripDateRangeField,
};

registry.category("fields").add("trip_daterange", tripDateRangeField);
