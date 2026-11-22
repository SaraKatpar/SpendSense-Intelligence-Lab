# Step 2: P0 accounting fixes

Completed 20 November 2026. Full regression suite: **69 tests passed**; log: test_suite_final.log. The preceding interrupted run used the old slow household import and is not counted as a completed verification run. The sample now imports atomically, preserving real source rows.

| Finding | Result |
|---|---|
| F01 currency detection | One shared detector/validator recognizes common currency codes and symbols, attached amounts such as RM120, and mixed currencies. Foreign receipt/order/wishlist defaults cannot be saved by checking an override box. Start a separate manual entry only with a verified workspace-currency amount. |
| F02 CSV currency | Full batch validated before writing; foreign/mixed units reject the entire batch. Exports carry currency; household remains INR, personal/mobile PKR. No exchange conversion. |
| F03 dates | Each expense clause resolves its own today/yesterday/ISO date. Missing dates default locally to today. Conflicting dates reject; unsupported relative dates request ISO input. Trailing yesterday applies to its own clause, not earlier rows. |
| F04 rounding | Decimal ROUND_HALF_UP to two decimals before both ledger and cash changes. Integer minor-unit arithmetic for cash changes and reversals. 0.005 becomes 0.01 on every save path; 0.004 is rejected as a zero-valued expense. |
| Idempotency | Persistent, workspace-scoped receipts commit atomically with desktop entry/batch/CSV/cart/commitment/snapshot saves. Same token plus different payload rejects. Mobile request receipts and reviewed AI tokens remain transactional. Concurrent retries insert/debit once. Explicit new-intent controls allow a separate identical purchase or a new balance snapshot. |

All transaction insertion paths (manual, receipt/order, CSV, text batch, commitments, reviewed AI and mobile) share storage.insert_entry/validated_entry. Shared policy is app/finance.py. Caps, wallets, planned carts and dues use the same quantization. The existing REAL columns are retained for compatibility; calculations use integer minor units and persist quantized values. This is not a claim that SQLite binary floating-point storage is a decimal database.

Regression checks include foreign symbols/codes, mixed-currency precedence, foreign CSV atomicity, per-clause relative/ISO dates, half-cent ledger/cash/refund/deletion consistency, batch totals, duplicate and conflicting tokens, eight concurrent retries, foreign upload forms, AI and authenticated mobile boundaries. All tests use isolated temporary databases. No personal records were used as test inputs, and no Berka test model was run.

**Failed during development:** currency codes touching digits (RM120) initially escaped detection; alphabetic token boundaries corrected this, and the regression now passes. Earlier generated-seed UI dependencies were replaced with explicit temporary test wallets in step 1.

**Still unvalidated:** historical sub-cent or mislabelled records are not retroactively reconciled; no exchange-rate conversion or bank reconciliation is provided. Missing currency on an explicitly local manual/CSV entry is interpreted as the fixed workspace currency; undisclosed foreign units cannot be inferred from a bare number. Supported symbols/codes are enumerated in app/finance.py; an unknown currency name in free prose may require manual review. Users can explicitly identify a separate legitimate identical purchase. Physical-device/offline retry behavior is reserved for the mobile step.

Run: `python -m unittest discover -s tests -v`. Next: step 3, the numerical advice guard.
