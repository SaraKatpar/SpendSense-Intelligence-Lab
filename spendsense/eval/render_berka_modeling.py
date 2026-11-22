"""Render completed real-data modeling results from cached metrics only."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'training'))
from berka_experiment import OUT,MODELS,read,save,sha


def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|',*['| '+' | '.join(str(v) for v in row)+' |' for row in rows]])
def ci(value,bounds):return f'{value:.3f} [{bounds[0]:.3f}, {bounds[1]:.3f}]'


def render():
    result=read(OUT/'regression_results.json');binary=read(OUT/'exploratory_binary_results.json')['logistic_regularized']
    cv=read(OUT/'regression_cv.json');bcv=read(OUT/'binary_cv.json');lock=read(OUT/'configuration_lock.json');ledger=read(OUT/'test_evaluation_ledger.json')
    bias=read(OUT/'selection_bias.json');verification=read(OUT/'verification.json')
    all_cases=result['primary_all_available_cases'];common=result['paired_common_cases'];ridge=all_cases['ridge']
    reg_table=lambda data:table(['Model','Accounts / months','Account-macro MAE [95% CI]','Account-macro RMSE [95% CI]'],
        [[name.replace('_',' '),f"{m['accounts']} / {m['months']}",ci(m['mae'],m['mae_ci95']),ci(m['rmse'],m['rmse_ci95'])] for name,m in data.items()])
    def bias_stat(partition,status,metric):
        row=next(x for x in bias['summaries'] if x['partition']==partition and x['status']==status)
        value=row[metric]
        return 'N/A' if value is None else f"{value['median']:.3f} [{value['q25']:.3f}, {value['q75']:.3f}]"
    limitations=("The continuous target is the month-end closing-balance/outflow ratio, whereas low-balance event B is an observed dip below 5% of prior typical outflow before the last calendar day; thresholding a month-end prediction does not identify every earlier dip or prove that a person lacks money elsewhere. The binary test outcome contains only seven positive account-months across four accounts, so the classifier results are exploratory and support no performance or deployment claims; 34 of 2,000 account-cluster bootstrap draws contained no positives, and undefined metrics were disclosed rather than replaced with zeros or resampled away. Only 639 of the fixed 832 accounts have exact targets in their assigned periods; 193 remain unscorable, and the scorable group has longer observed histories and higher median balance/outflow ratios, limiting population representativeness. Some closing balances cannot be uniquely ordered from dated transactions and are not imputed. Ratio errors are sensitive to small outflow denominators, producing a wide full-target RMSE interval; no test-driven clipping or threshold changes were made. Berka describes a non-student Czech banking population in 1993–1998, not contemporary Pakistani students; normalized features remove currency units but do not remove geographic, temporal or behavioral domain shift.")
    (OUT/'LIMITATIONS.md').write_text(limitations+'\n',encoding='utf-8')
    lines=['# Berka monthly low-balance modeling — completed evaluation',
        '**Primary:** month-end balance/outflow ratio regression. **Secondary:** exploratory low-balance event B. The frozen definition, 5% thresholds, relaxed coverage, 832-account registry and account/time assignments are unchanged. All estimators were fitted from scratch; no pretrained models, recurrent networks, fictional rows, oversampling or target imputation were used.',
        '## Authorization and development/test separation',
        f"The latest user instruction authorized training and account-grouped CV on pooled original train+validation data. This is recorded separately in `training_authorization_and_plan.json`; the original freeze JSON was not edited. Its historical `training_authorized=false` describes the earlier freeze stage, not a refusal of the later user authorization. Configuration lock: **{lock['locked_at']}**. Single final test prediction pass: **{ledger['started_at']}**. Each locked estimator made exactly one test prediction call; all subsequent metrics, plots and verification read `test_predictions_ONCE.csv`.",
        'Outer split remains account-disjoint: original training targets through 1996, validation targets in 1997, test targets in 1998. Pooling train+validation was expressly authorized for this run; no account was reassigned and no target period was extended. The three-positive fixed validation subset was not used as an isolated tuning set.',
        'Inner selection uses three deterministic account groups and forward validation years 1995, 1996 and 1997, giving nine possible folds. In each fold, fit only on other accounts with outcomes before the validation year. Thus validation accounts are unseen by that fold model, and its training targets precede its validation targets. All monthly features precede prediction origin. Scale parameters are fitted within each training fold; final models refit on development only. Each training account has equal total sample weight.',
        '## Features and estimators',
        'Eight regression features are all dimensionless: previous closing-balance lower/reference and upper/reference bounds; median previous-three-month net-flow/reference and credit/reference; previous-month net-flow/reference; and outflow/reference lags 1, 2 and 3. The exploratory binary model uses only the first five listed in `training_authorization_and_plan.json` (five actual columns: previous lower/upper, median net flow, lag-1 outflow, median credit). No current-month flow, future balance, identifiers or raw CZK value is a predictor. Unknown-operation credits remain in cash-flow/closing calculations and outside spending/anomaly/persona feature aggregates.',
        'Unresolved previous closing snapshots are represented by observed interval bounds for learned models; no midpoint or exact closing balance is invented. Persistence and pace require a previous exact closing balance and therefore have slightly less coverage. Current-month unresolved targets are never imputed or scored as exact targets. No outputs were clipped.',
        table(['Family','Pre-test configuration'],[
            ['Persistence','Previous exact closing/reference scale known at origin.'],
            ['Pace','Previous exact closing + median past-three-month net cash flow, divided by the same reference.'],
            ['Linear regression','Unregularized linear baseline on standardized monthly ratios; equal-account weights.'],
            ['Ridge',str(lock['models']['ridge']['spec']['params'])],
            ['Shallow regression gradient boosting',str(lock['models']['gradient_boosting']['spec']['params'])],
            ['Exploratory logistic regression',str(lock['models']['logistic_regularized']['spec']['params'])+'; five features, L2 regularization, no class oversampling.']]),
        'Ridge candidates used alpha 0.1/1/10/100/1000; shallow regressor candidates had depth 1–2, 100 estimators and leaf minima 50–100. Logistic C candidates were 0.001/0.01/0.1, all regularized more strongly than the usual C=1 default. Selection criteria and the binary-boost gate were recorded before inspecting test predictions.',
        '## Development results and locked choices',
        table(['Model','Grouped forward-CV common-case MAE','Grouped forward-CV common-case RMSE'],[[name,f"{m['mae']:.4f}",f"{m['rmse']:.4f}"] for name,m in cv['common_case_comparison'].items()]),
        f"The development-selected primary pipeline was **{lock['development_preference']}**, fixed before test. The shallow binary booster improved development Brier by only {bcv['boost_gate']['relative_brier_improvement']*100:.3f}% versus the selected logistic model, its paired difference CI crossed zero and its average precision decreased. It failed the predeclared >=5%/paired-CI/AP gate, so no final binary booster was retained or tested. This decision did not use the seven test positives.",
        '## Primary test result: all available exact targets',
        '**Lead with this population, not the more favorable complete-baseline subset.** All methods below use their actual available exact targets. Coverage differs, so losses across different month sets are not a paired performance comparison.',
        reg_table(all_cases),
        f"Development-selected ridge has full-target MAE **{ci(ridge['mae'],ridge['mae_ci95'])}** and RMSE **{ci(ridge['rmse'],ridge['rmse_ci95'])}**, on {ridge['months']} months in {ridge['accounts']} held-out accounts. Units are ratios of typical monthly outflow, not CZK or PKR. The large RMSE and wide interval are material results, not hidden outliers.",
        'One exact test ratio is approximately 303.57 and the locked ridge prediction is approximately 563.32. This case is among the 17 months where exact previous-closing inputs are unavailable to the persistence/pace baselines. It strongly affects the learned models\' full-target RMSE. No case was removed, clipped, winsorized or used to refit a model. `post_lock_extreme_ratio_diagnostic.csv` and `extreme_ratio_notes.json` are post-lock descriptive diagnostics only.',
        '![All available exact targets](plots/regression_all_available_bootstrap.png)',
        '## Fair paired comparison: common baseline cases',
        'All five locked regression methods can be compared on the same 1,558 exact-target months in 142 test accounts. This supplementary common-case table does not replace the full-target results above.',
        reg_table(common),
        table(['Paired difference: locked ridge minus baseline','MAE difference [95% CI]','RMSE difference [95% CI]'],[[name,ci(m['mae_difference'],m['mae_difference_ci95']),ci(m['rmse_difference'],m['rmse_difference_ci95'])] for name,m in result['paired_differences_selected_minus_baseline'].items()]),
        'The paired MAE and RMSE difference intervals versus persistence both include zero: **no clear improvement over persistence is established**. The paired intervals versus the specified pace rule are below zero on these common cases, but this is a result for this selected historical cohort and rule, not evidence of student-app generalization. The model preference remains the pre-test CV choice; it was not changed after seeing this table.',
        '![Common-case paired regression comparison](plots/regression_bootstrap.png)',
        '## Secondary binary B — EXPLORATORY only',
        f"The locked logistic model is scored on {binary['months']} test account-months in {binary['accounts']} accounts. There are **7 positive months across 4 accounts**. These are too few for a reliable performance claim. Numbers below are descriptive only. The probability threshold remains 0.5, distinct from the 0.05 balance-ratio threshold.",
        table(['Descriptive metric','Value / treatment'],[
            ['Account-weighted average precision',f"{binary['account_weighted_average_precision']:.4f}; valid-draw CI {binary['intervals']['average_precision']['ci95']}"],
            ['Account-macro Brier',f"{binary['account_macro_brier']:.6f}; CI {binary['intervals']['brier']['ci95']}"],
            ['Raw confusion at probability 0.5',str(binary['raw_confusion_at_0_5'])],
            ['Zero-positive bootstrap draws',f"{binary['zero_positive_draws']} / 2000"],
            ['Zero-negative bootstrap draws',f"{binary['zero_negative_draws']} / 2000"],
            ['AP undefined / valid draws',f"{binary['intervals']['average_precision']['undefined_draws']} / {binary['intervals']['average_precision']['valid_draws']}"],
            ['Precision undefined / valid draws',f"{binary['intervals']['precision_at_0_5']['undefined_draws']} / {binary['intervals']['precision_at_0_5']['valid_draws']}; interval unavailable (>5% undefined)."],
            ['Recall undefined / valid draws',f"{binary['intervals']['recall_at_0_5']['undefined_draws']} / {binary['intervals']['recall_at_0_5']['valid_draws']}; valid-draw interval [0, 0]."],
            ['Brier valid draws','2000; mathematically defined even on single-class resamples.']]),
        'At the frozen cutoff, the exploratory classifier has zero true positives and seven false negatives; it is not a validated warning system. AP is non-interpolated account-weighted average precision, not trapezoidal PR area. Single-class draws are left undefined for AP; recall without actual positives and precision without predicted positives are undefined. They were not replaced with zeros or resampled until positives appeared. AP/recall intervals condition on the 1,966 defined draws and remain fragile with only four positive accounts. Precision has 728 undefined draws (36.4%), so its interval is withheld under the frozen >5% rule. Every draw is saved for audit.',
        '![Exploratory binary scores](plots/exploratory_binary_scores.png)',
        'Month-end warnings derived by thresholding continuous predictions are evaluated against month-end low-ratio truth in `derived_month_end_warning.json`. That is a different outcome from earlier-month B; its confusion counts are not used to tune the threshold or claim event-detection performance.',
        '## Scorable versus unscorable accounts and selection bias',
        table(['Partition','Registered','Scorable','Unscorable'],[['Train',577,400,177],['Validation',113,97,16],['Test',142,142,0],['Total',832,639,193]]),
        'Of the 193 unscorable accounts, 192 lack an eligible origin inside their assigned target period and one has only unresolved assigned targets. They are retained in the registry and are not treated as safe negatives or assigned invented regression errors. Here scorable refers to the continuous primary target: B can be observed without a uniquely resolved month-end closing balance, so one additional validation account remains available to the binary model. Model-specific common-case coverage is also reported: only 637 accounts across all partitions have exact inputs for the deterministic baselines, versus 639 with at least one exact target for learned models.',
        table(['Whole-source account median [IQR]','Scorable','Unscorable'],[
            ['Observed full months',bias_stat('all','scorable','full_span_months'),bias_stat('all','unscorable','full_span_months')],
            ['Eligible debit records/month',bias_stat('all','scorable','full_month_debit_mean'),bias_stat('all','unscorable','full_month_debit_mean')],
            ['Ledger records/month',bias_stat('all','scorable','full_month_ledger_mean'),bias_stat('all','unscorable','full_month_ledger_mean')],
            ['Active debit-month fraction',bias_stat('all','scorable','active_debit_fraction'),bias_stat('all','unscorable','active_debit_fraction')],
            ['Median month-end balance/outflow ratio',bias_stat('all','scorable','median_month_end_ratio_all_source'),bias_stat('all','unscorable','median_month_end_ratio_all_source')]]),
        table(['Partition/group','Accounts','Median debits/month [IQR]','Median closing ratio [IQR]'],[[x['partition']+'/'+x['status'],x['accounts'],bias_stat(x['partition'],x['status'],'full_month_debit_mean'),bias_stat(x['partition'],x['status'],'median_month_end_ratio_all_source')] for x in bias['summaries'] if x['partition']!='all']),
        'Scorable accounts have median first observation in November 1993 versus May 1996 for unscorable accounts, median 61 versus 31 full months, and median closing/outflow ratio approximately 1.99 versus 1.51. The evaluated sample favors longer-established, higher-buffer accounts. This is evidence of selection differences, not a causal effect or a quantified error rate for excluded accounts. Ever-negative counts are 34/639 versus 11/193, but observation spans differ; those proportions are not exposure-adjusted comparisons. Standardized mean differences and per-account summaries are saved. These whole-source diagnostics include dates beyond modeling cutoffs and were not used as training features or selection objectives. Boxplots omit flier markers for readability only; no records are removed from summaries or metrics.',
        '![Account coverage](plots/account_coverage.png)\n\n![Selection bias](plots/selection_bias.png)',
        '## Bootstrap and audit details',
        'Every reported regression interval uses 2,000 account-cluster bootstrap draws (seed 20261119), retaining all observed months for each sampled account. Compute mean monthly loss inside each account, then average accounts equally; RMSE is the square root of the account-macro squared loss. Paired common-case comparisons reuse identical draws. No month-level IID bootstrap or synthetic training rows are used. The draw-level MAE/RMSE and binary diagnostics are saved. Intervals are conditional on the sampled historical bank/calendar periods and do not capture all domain shift or cross-account shared economic shocks.',
        f"Verification passed: {verification['verified_forward_account_disjoint_cv_fits']} grouped forward CV fits checked, {verification['final_development_refits']} final development refits, fold/outer-account separation, development-only scaler means, source/protocol/cohort/split hashes, one test pass and independently reconstructed cached bootstrap intervals. The original frozen JSON SHA-256 remains `{lock['protocol_sha256']}`. Reporting was updated to lead with all available exact targets; no estimator was rescored or changed during that reporting update.",
        '## Paste-ready limitations paragraph',limitations,
        '## Files and safe reproduction',
        'Metrics: `regression_all_available_metrics.csv`, `regression_test_metrics.csv` (common cases), `regression_results.json`, `exploratory_binary_results.json`, `derived_month_end_warning.json`. Selection: `training_authorization_and_plan.json`, `cv_design.json`, both CV JSONs, configuration lock/digest and `pre_test_verification.json`. Audit: `test_evaluation_ledger.json`, saved predictions, bootstrap draw CSVs, `selection_bias.json`, `account_selection_bias.csv`, post-lock diagnostic and `verification.json`. Standalone plots are in `plots/`. Trained model bundles/cards are in `models/berka_low_balance_v1/`.',
        'The development/preparation/scoring commands are documented in source, but **do not rerun the test scorer or retune models on this test**. Its exclusive ledger prevents a second scoring pass. To reproduce tables, checks and plots from the already saved predictions, from `spendsense`:\n\n```powershell\n../.venv/Scripts/python.exe eval/analyze_berka_models.py\n../.venv/Scripts/python.exe eval/verify_berka_modeling.py\n../.venv/Scripts/python.exe eval/render_berka_modeling.py\n```']
    body='\n\n'.join(lines)+'\n'
    (OUT/'REPORT.md').write_text(body,encoding='utf-8')
    card={'source':'Real original Berka ASC files only','target':'Month-end balance/outflow ratio; exploratory B secondary',
        'protocol_sha256':lock['protocol_sha256'],'models':lock['models'],'evaluation':'eval/berka_modeling_v1/REPORT.md',
        'development_selected_pipeline':lock['development_preference'],'one_test_pass':True,'student_validation':False,
        'regression_test_all_available':all_cases,'event_classifier':'EXPLORATORY, no performance claim; 7 positive test months across 4 accounts',
        'limitations':limitations}
    save(MODELS/'model_card.json',card);(MODELS/'LIMITATIONS.md').write_text(limitations+'\n',encoding='utf-8')
    audit=ROOT/'docs'/'DATA_AUDIT.md';text=audit.read_text(encoding='utf-8')
    start='<!-- BERKA_MODELING_V1_START -->';end='<!-- BERKA_MODELING_V1_END -->'
    audit_body=body.replace('# Berka monthly low-balance modeling — completed evaluation','## Berka monthly low-balance modeling — completed evaluation',1)
    # Keep image paths correct when the same report is embedded under docs/.
    audit_body=audit_body.replace('](plots/','](../eval/berka_modeling_v1/plots/')
    block=start+'\n'+audit_body+end
    if start in text:
        first=text.index(start);last=text.index(end,first)+len(end);text=text[:first]+block+text[last:]
    else:
        marker='<!-- BERKA_LOW_BALANCE_V1_START -->';text=text.replace(marker,block+'\n\n---\n\n> The following freeze section is a historical snapshot. The training results above reflect the later explicit authorization; frozen definitions and hashes are unchanged.\n\n'+marker)
    audit.write_text(text,encoding='utf-8')
    print('Saved completed modeling report, model card and paste-ready limitations.')


if __name__=='__main__':render()
