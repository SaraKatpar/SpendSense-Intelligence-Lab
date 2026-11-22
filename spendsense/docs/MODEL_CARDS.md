# Current model cards

## Spending-mix clusters (research only)

K-Means on six dimensionless debit timing/concentration features. Fixed K=3; entity-weighted fitting; 20 initialization seeds and 20 entity subsamples. See [full card and stability](../eval/spending_mix_v1/REPORT.md). No student identities, merchant-category inference or app deployment.

## Berka monthly benchmark (completed, frozen)

See [completed regression and exploratory event evaluation](../eval/berka_modeling_v1/REPORT.md). No changes, deployment or frozen-test reruns are permitted. Monthly features only. Research evidence does not validate contemporary student outcomes.

## Other existing components

Household/personal-reference LSTM, autoencoder and text-classifier artifacts remain legacy research components. Their older one-day errors do not establish multi-day wallet survival accuracy. DistilBERT candidates require the shared untouched benchmark requested in step 5. Personalization learning curves and hybrid survival evaluation remain pending. No source-currency monetary model is substituted for a PKR wallet.

Known generated sources and their derived models/scores have been retired from active documentation and application samples. Reversible retirement hashes are in eval/spending_mix_v1/retirement.json.
