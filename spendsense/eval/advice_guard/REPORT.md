# Step 3: numerical advice guard

Completed 20 November 2026. The full 76-test suite passed (test_suite.log). A further follow-up-bypass regression was added and the focused seven-test adversarial suite passed (adversarial_tests.log). No model evaluation or training is performed by these checks.

**Done:** purchase verdicts now come from app/advice_guard.py and the server's Python runway calculations. Checked numerical questions receive deterministic text for both pass and fail. A failed check bypasses the Llama call entirely: no contradictory model prose is appended, paraphrased or displayed. Fixed essentials/reserve cannot be treated as spare cash. Existing essential shortfall, failed saved carts and prior failed numerical questions veto free-form replies. A new explicit price is recalculated using the current plan. Untrusted cart labels are never echoed into a financial verdict.

Amounts follow the shared rounding policy; the protected ceiling is floored to minor units so rounding cannot enlarge a budget. Missing, malformed, foreign-currency or ambiguous purchase inputs do not receive approval. The statement for a passing purchase remains conditional on entered costs and coverage; nothing is saved or deducted by advice.

The same reply function serves desktop, check-in and authenticated mobile chat. An HTTP regression confirms that the vetoed answer is both returned and persisted, while cash stays unchanged. Adversarial phrases include direct approval, skipping meals, double negatives, prompt injection, JSON/HTML approval, spaced lettering and follow-up "just say YES" requests. None can override a failed check. These tests do not rely on an approval-keyword filter; rejected LLM output never enters the response.

**Failed/closed gap during implementation:** a follow-up could omit its earlier failed price. The guard now rechecks prior user prices in the conversation against current calculations; a regression verifies this and verifies that an explicit cheaper price gets a fresh result.

**Still unvalidated:** natural-language coverage beyond supported numeric purchase totals, live-model conversational quality and real-world financial completeness. The guard conservatively blocks free-form prose when a known failed cart or prior price remains in context, which may be restrictive for unrelated questions. It cannot discover unlogged debts or prove affordability from incomplete or false user inputs. No numerical guarantee is attributed to the language model itself.

Run focused checks: `python -m unittest discover -s tests -p test_advice_guard.py -v`. Steps 1–3 now pass their implemented checks; mobile packaging remains step 7, after personalization, the shared benchmark and survival evaluation have been addressed in order.
