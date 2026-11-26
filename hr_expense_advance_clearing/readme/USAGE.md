Configure the **Employee Advance** product and the **Default Clearing Journal**
before using this module.

**Create and pay an employee advance**

1. Go to **Expenses → My Expenses → My Advances** and click **New**.
2. Check the employee, enter the advance amount and leave **Paid by** set to
   **Employee**. If you already know the expense category the
   employee will use, select it in **Clearing Product**. Odoo will fill in that
   category when you create the clearing expense.
3. Submit the advance and approve it. Approving creates a draft receipt for the
   employee.
4. Click the **Journal Entry** smart button and **Confirm** the receipt. Its
   **Amount Due** shows how much the company owes the employee.
5. Click **Pay** and register the payment in the bank or cash journal used to
   pay the employee. If the receipt remains **In Payment**, reconcile the
   payment with the bank transaction. Return to **My Advances** and check that
   the advance is **Paid**.

For example, after the company pays a 100 EUR advance, **Remaining to Clear**
on the advance still shows 100 EUR. The employee has received the money and
can now submit expenses against it or return the unused amount.

**Clear a paid advance**

You can create the clearing expense from either menu:

- **From My Advances:** open a **Paid** advance with a positive **Remaining to
  Clear** balance and click **Clear Advance**. Odoo opens a new expense with
  the employee and the advance already selected. If you set a **Clearing
  Product** on the advance, Odoo also fills in the expense category.
- **From My Clearings:** go to **Expenses → My Expenses → My Clearings** and
  click **New**. Select the employee, then select their advance in **Clear
  Advance**.

Once the expense is open:

1. Check the expense category and enter the full amount the employee spent.
   For example, if the employee received 100 EUR and spent 130 EUR, enter
   **130 EUR**.
2. Submit the expense and approve it. Approving posts the clearing entry in the
   **Default Clearing Journal** and reconciles it with the advance: there is no
   receipt to confirm.
3. Check the clearing expense to see whether the employee is owed a payment.
   Open the original advance to check **Remaining to Clear**.

Examples for a paid advance of 100 EUR:

| Expense amount | Result after approval | Next step |
|----|----|----|
| 100 EUR | The clearing expense is **Paid** and **Remaining to Clear** on the advance is zero. | The advance is fully cleared. |
| 130 EUR | **Remaining to Clear** is zero. The clearing expense shows **Amount to Pay** of 30 EUR. | Click **Pay** on the clearing expense and register the 30 EUR payment to the employee. The clearing expense then shows **Paid**. |
| 70 EUR | The clearing expense is **Paid**. **Remaining to Clear** on the advance is 30 EUR. | When the employee returns the 30 EUR, record it with **Return Advance**. |

If the employee paid a vendor bill with the advance, enable **A bill is sent
separately** on the clearing and select the vendor. The clearing then moves the
vendor's debt to the advance instead of booking the expense, and the bill is
matched with it when it is registered.

**Record money returned by the employee**

1. When the employee returns unused funds, go to **My Advances** and open the
   original advance. It must be **Paid** and have a positive **Remaining to
   Clear** balance.
2. Click **Return Advance**. This button needs accounting rights. In the
   payment wizard, select the bank or cash journal where the company received
   the money.
3. Enter the amount received and click **Create Payment**. The amount cannot
   exceed **Remaining to Clear**.
4. On the advance, click the **Return** smart button to view the incoming
   payment. After the employee returns the full outstanding amount,
   **Remaining to Clear** is zero.
