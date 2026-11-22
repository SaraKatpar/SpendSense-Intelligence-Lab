"""Render immutable low-balance v1 decisions and authorized aggregate counts."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'eval'/'berka_low_balance'
START='<!-- BERKA_LOW_BALANCE_V1_START -->';END='<!-- BERKA_LOW_BALANCE_V1_END -->'


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|',*['| '+' | '.join(str(x) for x in row)+' |' for row in rows]])


def render():
    path=ROOT/'app'/'data'/'low_balance_protocol_v1.json'
    p=json.loads(path.read_text(encoding='utf-8'));q=json.loads((OUT/'target_availability.json').read_text(encoding='utf-8'))
    digest=json.loads((OUT/'freeze_digest.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest['protocol_sha256']
    text=['## Frozen monthly low-balance protocol v1',
        f"**Frozen: {p['frozen_at']} (Asia/Karachi). No model has been trained.** The selected outcome is **low-balance event, definition B**, using **relaxed coverage**. Prior competing definitions/coverage experiments are retired; A is retained only for the explicitly requested aggregate audit. Earlier proposal artifacts are historical, not active target rules.",
        '### Authorized pre-freeze positive counts',
        'The table uses the fixed 832-account population and the unchanged account-disjoint chronological assignment. It reports only positive account-month/account counts, including the explicitly authorized test feasibility check. No test performance metric, threshold search, model fitting or split tuning was performed.',
        table(['Partition','A positive account-months','A positive accounts','B positive account-months','B positive accounts'],[[x['partition'],x['A_positive_account_months'],x['A_positive_accounts'],x['B_positive_account_months'],x['B_positive_accounts']] for x in p['pre_freeze_counts']]),
        '**The test cohort has 7 positive B account-months, below the requested approximately-20 threshold. The binary event classifier is frozen as exploratory.** This does not change definition B, its 5% threshold, the coverage policy or the split. Counts differ from the earlier broader relaxed comparison because this protocol now uses the explicitly requested fixed 832-account population.',
        '### Population and relaxed observation policy',
        f"`eval/berka_low_balance/cohort_832.csv` contains all **832 fixed account IDs**. SHA-256: `{p['cohort']['sha256']}`. Their groups are 577 train, 113 validation and 142 test accounts. These IDs were explicitly retained from the previously reviewed eligibility report; their historical ascertainment used the earlier full-source eligibility analysis. That is population provenance only: the old coverage filter is not reapplied to target months. Consequently this is a retrospective selected cohort, not prospective admission or a claim about every account in the bank.",
        'At each monthly origin require 12 completed prior months, historical mean >=4 eligible debits/month and >=80% active prior full months. A target month uses relaxed coverage: it lies within the observed source span and has **at least two distinct observed transaction dates, with no maximum-gap limit**. Future transaction density is only retrospective outcome-availability metadata, never a model feature. Missing/unobserved events are not proven safe outcomes.',
        'Let S(M) be the **median observed monthly eligible-debit outflow** in the three full calendar months preceding target month M. Each of those three months must contain >=3 eligible debit records, S(M)>0, and the previous month-end balance snapshot must already be observed at the prediction origin. Eligible debit means known operation and raw type VYDAJ or VYBER. This includes debt/service payments until the user separately approves a category mapping; it is not assumed to be discretionary consumption.',
        '### Selected secondary binary event and continuous primary target',
        '**Prediction origin:** 00:00 on the first calendar day of M. Predictors use only prior months.\n\n**Selected binary B:** at least one observed post-transaction balance divided by S(M) is **strictly below 0.05**, on a date **strictly before the last calendar day of M**. Negatives qualify. Name this a **low-balance event**, never a claim about all money a person owns.',
        '**Primary continuous target:** `month_end_ratio(M) = exact closing balance on the last calendar day of M / S(M)`. It is dimensionless, signed, and not clipped or winsorized. The denominator is fixed from information available before M; it is never recomputed from M\'s actual outflow.',
        '**Derived warning:** predicted month-end ratio <0.05. Its ground truth is the measured month-end ratio <0.05. This **month-end warning is distinct from selected B**: an earlier dip can recover before closing, and a closing-day dip can occur without a pre-last-day B event. Do not claim thresholding a month-end prediction detects every earlier-month event. Logistic regression addresses B as an exploratory classifier; it is not a continuous regressor.',
        '### Exact month-end measurement and missing-target disclosure',
        'There are no within-day timestamps, so highest trans_id/file order, averaging last-day snapshots or carrying an old day forward is not permitted. Keep all ledger rows, including bank-generated interest credits, for closing-balance measurement. If every last-day observed balance is equal, closing balance is unambiguous. Otherwise each signed amount and post-balance defines a before→after ledger edge. A connected valid directed Euler trail with a unique terminal vertex identifies closing balance without choosing an arbitrary transaction order. Amounts/balances are checked in integer cents; no source value is changed.',
        table(['All-source month-end measurement status, 832 accounts','Months'],[[k,v] for k,v in q['month_end_measurement_statuses_all_source'].items()]),
        'If no unique terminal can be established, retain min/max last-day balance bounds and mark the scalar target unresolved. Do not impute an operation, midpoint, closing balance or scalar label. These intervals are audit bounds; interval-distance scores must not be presented as ordinary exact-target MAE/RMSE.',
        f"All **832** registered accounts have exact continuous targets somewhere in the original source ({q['all_source_exact_target_months']:,} eligible origin-months). Under the fixed assigned target years, only **{q['assigned_period_accounts_with_exact_targets']} accounts** currently have exact scorable targets. The remaining **{832-q['assigned_period_accounts_with_exact_targets']}** remain in the registry with explicit unscorable status; do not silently drop them or claim 832 accounts were scored. Exact scoring on every one of the 832 is **not achievable under the unchanged split and measurement rules**. Any future change to address this requires a separately documented amendment, not test-informed reshuffling.",
        table(['Partition','Registered accounts','Accounts with valid origins','Exact target months','Accounts with exact targets','Common baseline target months','Accounts with common baseline targets'],[[x['partition'],x['registered_accounts'],x['accounts_with_origins'],x['exact_target_months'],x['accounts_with_exact_targets'],x['common_baseline_target_months'],x['accounts_with_common_baseline_targets']] for x in q['by_partition']]),
        'Publish per-account target availability for the full 832-account registry, unscorable reasons, and actual scored account/month denominators with every later evaluation. The core comparisons use common exact-target/input cases, while separately reporting each method\'s prediction availability. This is a material coverage limitation; it is not resolved by increasing sample size with fictional records.',
        '### Frozen account/time split',
        'Keep `int(SHA256("spendsense-berka-split-v1:" + account_id), 16) % 100`: 0–69 train, 70–84 validation, 85–99 test. The original whole-bank assignment remains unchanged (3,162/664/674 accounts); the fixed 832-account cohort is its subset (577/113/142). Client linkage was checked from original disp.asc: no shared client crosses these groups.',
        table(['Partition','Target dates','Historical input rule'],[
            ['Train','Through 1996-12-31','Only assigned train accounts and observations strictly before each monthly origin.'],
            ['Validation','1997-01-01 to 1997-12-31','Own assigned accounts’ past only; no fitted validation transforms.'],
            ['Test','1998-01-01 to 1998-12-31','Own assigned accounts’ past only; no model/threshold selection on outcomes.']]),
        f"Assignment-file SHA-256: `{p['split']['sha256']}`. Labels must end wholly inside their assigned target periods. Past lookback may cross a year boundary only for that same assigned account. Fit all scaling, encoding, feature selection and estimator parameters on train only; validation may support later predeclared model selection. Test is used once for final evaluation after that selection. The only test outcome release in this step is the user-requested A/B positive count table. No per-row test target values, warning labels, model predictions or performance metrics are exported.",
        '### Monthly features and baseline roles',
        '**Berka has monthly features only. No daily LSTM, GRU or other recurrent Berka model belongs to v1.** Features may be lagged monthly balance/reference, inflow/reference, outflow/reference, net-flow/reference, payment shares, activity ratios or training-fitted z-scores. Account/client/counterparty IDs and raw CZK amounts/balances are not predictors. Preserve the approved unknown-operation exclusions for spending/anomaly/persona features; full ledger cash flow and closing balances retain bank-generated credits. Never import Berka amounts into the PKR wallet.',
        table(['Baseline','Frozen role / definition'],[
            ['Last-month ratio','Previous exact month-end closing balance / current known S(M): persistence on the same target scale.'],
            ['Monthly pace rule','(Previous exact closing balance + median observed net cash flow in the previous 3 months) / S(M). Uses past monthly cash flow, including bank-generated credits; no daily extrapolation.'],
            ['Logistic regression','Exploratory binary classifier for selected B only; cannot predict the continuous primary target.'],
            ['Gradient boosting','Regressor for the continuous primary target; a separate exploratory B classifier may be benchmarked when training is later authorized.']]),
        'A previous closing balance that cannot be resolved remains unavailable to the persistence/pace baselines; no midpoint is substituted. The deterministic baseline values saved for development are calculations, not fitted models or reported model performance. No test baseline predictions are exported. Binary probability reporting uses a fixed 0.5 cutoff; the derived ratio warning uses the separately fixed 0.05 cutoff. Do not confuse probability with a balance ratio.',
        '### Future evaluation and bootstrap confidence intervals — plan only',
        'Primary continuous metrics: **account-macro MAE** and **sqrt(account-macro monthly mean squared error)**, in ratio units. Calculate each account\'s mean monthly loss, then give accounts equal weight. Do not clip large/negative ratios after looking at test results. Report actual scorable accounts and months, rather than implying the whole registry has exact labels.',
        'Use **2,000 account-cluster bootstrap draws**, seed **20261119**, with replacement within each partition, preserving all months for each selected account. Give 95% percentile intervals (2.5%/97.5%). Use the same draws for paired baseline-loss differences on common evaluable accounts. Resampling observed accounts is not generation of new training data. These intervals are conditional on the observed bank/calendar periods and do not prove generalization to student finances.',
        'Report the derived month-end warning against month-end truth separately from the exploratory B classifier. For B, predeclare PR-AUC, Brier score and precision/recall/confusion counts at fixed probability 0.5. Record how many bootstrap draws have no positive/negative examples and yield undefined metrics; never keep resampling until a positive appears. If >5% are undefined, mark that interval unreliable/unavailable. No bootstrap confidence intervals have been computed yet because there are no fitted predictions.',
        '### Freeze integrity, status and reproduction',
        f"Canonical contract: `app/data/low_balance_protocol_v1.json`, SHA-256 `{digest['protocol_sha256']}`. A copy and digest are in `eval/berka_low_balance/`. The freeze script refuses to overwrite v1; changes require an explicit versioned amendment. `training_authorized=false`, `model_fits=0`. The event classifier is exploratory because the authorized test count is below 20; the count was not used to tune definitions or thresholds.",
        'Current artifacts: `cohort_832.csv`, `pre_freeze_AB_counts.json`, `target_availability.json`, `cohort_target_availability.csv`, `monthly_target_availability.csv`, development-only targets/baseline calculations, protocol/digest and verification report. Earlier competing proposals are historical only. Future training remains blocked by the current instruction.',
        'From `spendsense`, check and render without fitting anything:\n\n```powershell\n../.venv/Scripts/python.exe eval/verify_low_balance_protocol.py\n../.venv/Scripts/python.exe eval/render_low_balance_protocol.py\n```']
    body='\n\n'.join(text)+'\n'
    (OUT/'REPORT.md').write_text(body,encoding='utf-8')
    audit=ROOT/'docs'/'DATA_AUDIT.md';old=audit.read_text(encoding='utf-8')
    historic_start='<!-- BERKA_ACCOUNT_FEASIBILITY_START -->';historic_end='<!-- BERKA_ACCOUNT_FEASIBILITY_END -->'
    if historic_start in old:
        first=old.index(historic_start);last=old.index(historic_end,first)+len(historic_end)
        old=old[:first]+START+'\n'+body+END+old[last:]
    elif START in old:
        first=old.index(START);last=old.index(END,first)+len(END);old=old[:first]+START+'\n'+body+END+old[last:]
    else:old=old.replace('## Historical audit — excluded legacy sources and prior design',START+'\n'+body+END+'\n\n## Historical audit — excluded legacy sources and prior design')
    audit.write_text(old,encoding='utf-8')
    print('Rendered frozen low-balance v1 protocol. No training.')


if __name__=='__main__':render()
