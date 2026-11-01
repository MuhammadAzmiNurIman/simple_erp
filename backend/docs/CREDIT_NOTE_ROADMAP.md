# Credit note and refund roadmap

## Current MVP boundary

A posted sales return records returned items and restores only items marked
`RESTOCK`. It does not change the invoice total, payment allocations, or
receivable balance. This is intentional for the current MVP and must remain
visible in the operator workflow until financial returns are implemented.

## Proposed workflow

1. Create a return draft against a posted shipment and validate each returned
   quantity against the unreturned shipped quantity.
2. Review and approve the return. Capture disposition, reason, operator, and
   approval timestamp in the audit trail.
3. Post the inventory effect and create a credit note in one database
   transaction. A credit note must reference the originating invoice and return.
4. Allocate the credit note to the invoice's open balance, or leave it as an
   unapplied customer credit. Enforce that total allocations never exceed the
   credit amount or the invoice's remaining balance.
5. For an already-paid invoice, leave the credit available for a future invoice
   or create a separately approved refund. A refund must be its own financial
   transaction with method, date, reference, poster, and idempotency protection.

## Accounting and balance rules

- Credit value should use the original invoiced unit price for accepted
  quantities. Damaged goods can receive a different financial treatment only
  under an explicit business policy.
- A credit note reduces receivables only when posted and allocated. A draft or
  approved note does not change customer balances.
- Posted payment allocations are immutable. Corrections use reversal records
  and new allocations; never edit the historical allocation in place.
- Credits must be capped at the invoice's remaining refundable value, with
  explicit policy for taxes, discounts, shipping, and partial quantities.
- Refunds cannot exceed unapplied customer credit. The refund and credit
  allocation must be linked and auditable.

## Suggested data and API design

- `credit_notes`: code, customer, source invoice, source return, status
  (`DRAFT`, `APPROVED`, `POSTED`, `VOID`), currency, subtotal/tax/total,
  reason, creator, approver, poster, and timestamps.
- `credit_note_items`: source shipment item, returned quantity, unit price,
  disposition, and credited amount.
- `credit_note_allocations`: credit note, invoice, allocated amount, and
  created-by metadata.
- `customer_refunds`: customer, credit note, amount, method, external reference,
  status, idempotency key, and posting/audit metadata.
- Endpoints should mirror existing document lifecycle conventions:
  create, approve, post, allocate, and post refund. Posting should be
  idempotent and use row locks while recalculating available invoice and credit
  balances.

## Delivery phases

1. Confirm tax, discount, shipping, damaged-goods, and overpayment policies.
2. Approve accounting entries and credit/refund authorization permissions.
3. Add schema migrations, immutable audit events, and balance calculations.
4. Add API contracts and domain tests for partial returns, concurrent posting,
   duplicate requests, over-allocation, and paid invoices.
5. Add frontend review, approval, credit allocation, and refund screens.
6. Reconcile historical data and deploy behind a feature flag with finance
   sign-off.
