odoo.define("hr_expense_tax_adjust.ExpenseTaxGroupCustomField", function (require) {
    "use strict";

    var core = require("web.core");
    var session = require("web.session");
    var fieldRegistry = require("web.field_registry");
    var AbstractField = require("web.AbstractField");
    var fieldUtils = require("web.field_utils");
    var QWeb = core.qweb;

    var ExpenseTaxGroupCustomField = AbstractField.extend({
        events: {
            "click .tax_group_edit": "_onClick",
            "keydown .oe_tax_group_editable .tax_group_edit_input input": "_onKeydown",
            "blur .oe_tax_group_editable .tax_group_edit_input input": "_onBlur",
        },

        // --------------------------------------------------------------------------
        // Private
        // --------------------------------------------------------------------------

        /**
         * This method is called by "_setTaxGroups". It is
         * responsible for calculating taxes based on
         * tax groups and triggering an event to
         * notify the ORM of a change.
         *
         * @param {Id} taxGroupId
         * @param {Float} newValue
         * @param {Object} currency
         */
        _changeTaxValueByTaxGroup: function (taxGroupId, newValue, currency) {
            var self = this;
            var amount_by_group_txt = this.record.data.amount_by_group_txt;
            var amount_by_group = amount_by_group_txt
                .replace(/\[|\]|'|"/g, "")
                .split(", ");
            var new_amount_by_group = [];
            var lst_amount = "[]";
            var base_amount = 0.0;
            var tax_amount = 0.0;
            var tax_amount_sign = "";
            var n = 0;
            console.log(amount_by_group_txt);
            console.log(amount_by_group);
            for (var i = 0, len = amount_by_group.length; i < len / 7; i++) {
                n = i * 7;
                tax_amount = fieldUtils.parse.float(amount_by_group[n + 1]);
                base_amount = fieldUtils.parse.float(amount_by_group[n + 2]);
                tax_amount_sign = amount_by_group[n + 3];
                if (amount_by_group[n + 6] == taxGroupId) {
                    // Update tax_amount
                    tax_amount = newValue;
                    // Update tax_amount_sign
                    var formatOptions = {
                        currency: currency,
                        forceString: true,
                    };
                    tax_amount_sign = fieldUtils.format.monetary(
                        tax_amount,
                        {},
                        formatOptions
                    );
                }
                lst_amount = `['${
                    amount_by_group[n]
                }', ${tax_amount}, ${base_amount}, '${tax_amount_sign}', '${
                    amount_by_group[n + 4]
                }', ${amount_by_group[n + 5]}, ${amount_by_group[n + 6]}]`;
                new_amount_by_group.push(lst_amount);
            }
            var new_amount_by_group_str = new_amount_by_group.join(", ");
            var new_amount_by_group_txt = `[${new_amount_by_group_str}]`;
            // Trigger ORM
            self.trigger_up("field_changed", {
                dataPointID: self.record.id,
                changes: {amount_by_group_txt: new_amount_by_group_txt},
            });
        },

        /**
         * This method is part of the widget life cycle and allows you to render
         * the widget.
         *
         * @private
         * @override
         */
        _render: function () {
            var self = this;
            // Display the pencil and allow the event to click and edit only on expense that are not posted and in edit mode.
            // since the field is readonly its mode will always be readonly. Therefore we have to use a trick by checking the
            // formRenderer (the parent) and check if it is in edit in order to know the correct mode.
            var displayEditWidget =
                this.record.data.editable_tax_adjustment &&
                this.getParent().mode === "edit";
            this.$el.html(
                $(
                    QWeb.render("ExpenseAccountTaxGroupTemplate", {
                        lines: self.value,
                        displayEditWidget: displayEditWidget,
                    })
                )
            );
        },

        // --------------------------------------------------------------------------
        // Handler
        // --------------------------------------------------------------------------

        /**
         * This method is called when the user is in edit mode and
         * leaves the <input> field. Then, we execute the code that
         * modifies the information.
         *
         * @param {event} ev
         * @returns {Object}
         */
        _onBlur: function (ev) {
            ev.preventDefault();
            var $input = $(ev.target);
            var newValue = $input.val();
            var currency = session.get_currency(this.record.data.currency_id.data.id);
            try {
                // Need a float for format the value.
                newValue = fieldUtils.parse.float(newValue);
                // Return a string rounded to currency precision
                newValue = fieldUtils.format.float(newValue, null, {
                    digits: currency.digits,
                });
                // Convert back to Float to compare with oldValue to know if value has changed
                newValue = fieldUtils.parse.float(newValue);
            } catch (err) {
                $input.addClass("o_field_invalid");
                return;
            }
            var oldValue = $input.data("originalValue");
            if (newValue === oldValue || newValue === 0) {
                return this._render();
            }
            var taxGroupId = $input
                .parents(".oe_tax_group_editable")
                .data("taxGroupId");
            this._changeTaxValueByTaxGroup(taxGroupId, newValue, currency);
        },

        /**
         * This method is called when the user clicks on a specific <td>.
         * it will hide the edit button and display the field to be edited.
         *
         * @param {event} ev
         */
        _onClick: function (ev) {
            ev.preventDefault();
            var $taxGroupElement = $(ev.target).parents(".oe_tax_group_editable");
            // Show input and hide previous element
            $taxGroupElement.find(".tax_group_edit").addClass("d-none");
            $taxGroupElement.find(".tax_group_edit_input").removeClass("d-none");
            var $input = $taxGroupElement.find(".tax_group_edit_input input");
            // Get original value and display it in user locale in the input
            var formatedOriginalValue = fieldUtils.format.float(
                $input.data("originalValue"),
                {},
                {}
            );
            // Focus the input
            $input.focus();
            // Add value in user locale to the input
            $input.val(formatedOriginalValue);
        },

        /**
         * This method is called when the user is in edit mode and pressing
         * a key on his keyboard. If this key corresponds to ENTER or TAB,
         * the code that modifies the information is executed.
         *
         * @param {event} ev
         */
        _onKeydown: function (ev) {
            switch (ev.which) {
                // Trigger only if the user clicks on ENTER or on TAB.
                case $.ui.keyCode.ENTER:
                case $.ui.keyCode.TAB:
                    // Trigger blur to prevent the code being executed twice
                    $(ev.target).blur();
            }
        },
    });
    fieldRegistry.add("expense-tax-group-custom-field", ExpenseTaxGroupCustomField);
});
