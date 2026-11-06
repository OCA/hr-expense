import {AttachmentView} from "@mail/core/common/attachment_view";
import {patch} from "@web/core/utils/patch";

patch(AttachmentView.prototype, {
    get displayName() {
        if (this.state.thread.model === "hr.expense.sheet") {
            return (
                this.state.thread.message_main_attachment_id.res_name ||
                this.state.thread.name
            );
        }
        return super.displayName;
    },
});
