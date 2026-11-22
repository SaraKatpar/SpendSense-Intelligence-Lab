"""Research-only real-data K-Means; never reads/scorers the frozen Berka test.

Run: python training/build_spending_mix.py
Fixed K=3, equal entity weight, 20 initialization seeds and entity subsampling.
All selection decisions are written before any fitting. No tuning to silhouette.
"""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from app.data.spending_mix import FEATURES, profile
from app.data.berka_policy import rows_for

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'eval/spending_mix_v1'
ARTIFACT = ROOT / 'models/spending_mix_research_v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')


def protected():
    paths = [ROOT / 'app/data/low_balance_protocol_v1.json',
             ROOT / 'eval/berka_accounts/proposed_account_split.csv']
    paths += sorted((ROOT / 'eval/berka_modeling_v1').glob('*'))
    paths += sorted((ROOT / 'models/berka_low_balance_v1').glob('*'))
    return {str(p.relative_to(ROOT)): sha(p) for p in paths if p.is_file()}


def reference_profiles(path, source):
    frame = pd.read_csv(path, keep_default_na=False)
    frame['date'] = pd.to_datetime(frame.date)
    if frame.currency.nunique() != 1:
        raise ValueError('Reference units must remain isolated.')
    first, last = frame.date.min(), frame.date.max()
    start = first.to_period('M').start_time
    if first > start:
        start += pd.offsets.MonthBegin(1)
    rows = frame.loc[frame.kind.eq('Expense')].copy()
    result = []
    while start + pd.offsets.MonthEnd(6) <= last:
        end = start + pd.offsets.MonthEnd(6)
        values = profile(rows, start, end, first, last)
        if values:
            result.append({'entity_id': source, 'source': source, 'window_start': str(start.date()),
                           'window_end': str(end.date()), **values})
        start += pd.offsets.MonthBegin(6)
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    before = protected()
    write('plan.json', {'timestamp': datetime.now(ZoneInfo('Asia/Karachi')).isoformat(),
        'name': 'spending-mix clusters', 'research_only': True, 'deployed': False,
        'berka': 'Original ASC; TRAIN-assigned accounts only, 1996-07-01 to 1996-12-31. No validation/test account profiles, test cache or outcomes read.',
        'eligibility': 'Six full observed-span months; >=20 eligible positive debits; >=80% active months (at least five). Unknown operations excluded from all features.',
        'reference_windows': 'Nonoverlapping six-full-month windows, same eligibility; one entity per entire reference history, not invented users.',
        'features': FEATURES, 'scaling': 'All shares in [0,1]; no fitted scaling or currency conversion.',
        'weights': 'Each entity total weight 1; multiple reference windows share that one weight. No source oversampling.',
        'k': 3, 'n_init': 20, 'artifact_seed': 42, 'stability_seeds': list(range(20)),
        'subsampling': '20 independent 80% entity subsamples, seed 1000+i; compare assignments of all development profiles. Descriptive stability, no held-out accuracy.',
        'selection': 'K/features/seed/weights fixed before fits. No selection by best silhouette or test metrics.'})
    split = pd.read_csv(ROOT / 'eval/berka_accounts/proposed_account_split.csv')
    train_ids = set(split.loc[split.partition.eq('train'), 'account_id'])
    proof = json.loads((ROOT / 'data/berka_original/provenance.json').read_text(encoding='utf-8'))
    for name, meta in proof['files'].items():
        assert sha(ROOT / 'data/berka_original' / name) == meta['sha256']
    raw = pd.read_csv(ROOT / 'data/berka_original/trans.asc', sep=';', keep_default_na=False)
    # Reading original source is permitted; no held-out account is profiled or scored.
    frame = raw.loc[raw.account_id.isin(train_ids)].copy()
    frame['date'] = pd.to_datetime(frame.date.astype(str), format='%y%m%d')
    frame = frame.loc[frame.date.le('1996-12-31')]
    bounds = frame.groupby('account_id').date.agg(['min', 'max'])
    eligible = rows_for(frame, 'persona')
    eligible = eligible.loc[eligible.type.isin(['VYDAJ', 'VYBER'])]
    records, eligibility = [], []
    for account, group in eligible.groupby('account_id'):
        bound = bounds.loc[account]
        values = profile(group, '1996-07-01', '1996-12-31', bound['min'], bound['max'])
        eligibility.append({'account_id': int(account), 'eligible': values is not None})
        if values:
            records.append({'entity_id': f'berka_{account}', 'source': 'berka',
                'window_start': '1996-07-01', 'window_end': '1996-12-31', **values})
    paths = {'household': ROOT / 'data/household_clean.csv',
             'personal_reference': ROOT / 'data/kaggle/personal_reference_clean.csv'}
    for source, path in paths.items():
        records.extend(reference_profiles(path, source))
    data = pd.DataFrame(records)
    data['weight'] = 1 / data.groupby('entity_id').entity_id.transform('size')
    x, weights = data[FEATURES].to_numpy(), data.weight.to_numpy()
    assert np.isfinite(x).all() and ((x >= 0) & (x <= 1 + 1e-12)).all()
    assert set(data.loc[data.source.eq('berka'), 'entity_id']) <= {f'berka_{a}' for a in train_ids}
    model = KMeans(n_clusters=3, n_init=20, random_state=42).fit(x, sample_weight=weights)
    data['cluster'] = model.labels_
    seed_labels = []
    for seed in range(20):
        fitted = KMeans(n_clusters=3, n_init=20, random_state=seed).fit(x, sample_weight=weights)
        seed_labels.append(fitted.labels_)
    pairwise = [float(adjusted_rand_score(seed_labels[i], seed_labels[j]))
                for i in range(20) for j in range(i)]
    entities = data.entity_id.unique()
    subsample = []
    for i in range(20):
        rng = np.random.default_rng(1000 + i)
        chosen = rng.choice(entities, int(.8 * len(entities)), replace=False)
        mask = data.entity_id.isin(chosen).to_numpy()
        fitted = KMeans(n_clusters=3, n_init=20, random_state=i).fit(x[mask], sample_weight=weights[mask])
        subsample.append(float(adjusted_rand_score(model.labels_, fitted.predict(x))))
    names = {i: f'Spending-mix cluster {i + 1}' for i in range(3)}
    joblib.dump({'model': model, 'features': FEATURES, 'names': names,
                 'research_only': True, 'deployable': False}, ARTIFACT / 'clusters.joblib')
    data.to_csv(OUT / 'profiles.csv', index=False)
    pd.DataFrame(eligibility).to_csv(OUT / 'berka_development_eligibility.csv', index=False)
    centers = pd.DataFrame(model.cluster_centers_, columns=FEATURES)
    centers.index.name = 'cluster'
    centers.to_csv(OUT / 'centers.csv')
    data.groupby(['source', 'cluster']).size().unstack(fill_value=0).to_csv(OUT / 'source_by_cluster.csv')
    manifest = {str(path.relative_to(ROOT)): sha(path) for path in paths.values()}
    manifest['data/berka_original/trans.asc'] = sha(ROOT / 'data/berka_original/trans.asc')
    for source in ('personal-finance', 'daily-household-transactions'):
        path = ROOT / 'data/kaggle' / source / 'metadata.json'
        meta = json.loads(path.read_text(encoding='utf-8'))
        description = meta.get('description', '')
        manifest[str(path.relative_to(ROOT))] = sha(path)
        write(source + '_provenance_review.json', {
            'title': meta.get('title'), 'license_as_reported': meta.get('licenseName'),
            'synthetic_word_matches': [w for w in ('synthetic', 'fictional', 'generated', 'simulated') if w in description.lower()],
            'description': description,
            'assessment': 'Publisher calls transactions real-world; independent collection authenticity and source currency unverified.' if source == 'personal-finance' else
                          'User-approved household reference; metadata has no description. Original collection provenance remains unverified.'})
    result = {'name': 'spending-mix clusters', 'research_only': True, 'deployed': False,
        'profiles': len(data), 'distinct_recorded_entities': len(entities),
        'profiles_by_source': data.source.value_counts().to_dict(),
        'entities_by_source': data.groupby('source').entity_id.nunique().to_dict(),
        'effective_weight_by_source': data.groupby('source').weight.sum().to_dict(),
        'silhouette_unweighted_descriptive': float(silhouette_score(x, model.labels_)),
        'seed_pairwise_ari': {'draws': len(pairwise), 'min': min(pairwise), 'median': float(np.median(pairwise)), 'max': max(pairwise), 'values': pairwise},
        'entity_subsample_ari': {'values': subsample, 'min': min(subsample), 'median': float(np.median(subsample)), 'max': max(subsample)},
        'source_hashes': manifest, 'artifact_sha256': sha(ARTIFACT / 'clusters.joblib'),
        'protected_berka_hashes_unchanged': protected() == before,
        'limitations': ['Timing/concentration mix, not food/shopping categories: Berka has no comparable merchant labels.',
            'Berka total debits include loan repayments, cash withdrawals and bank fees; cash withdrawals do not reveal subsequent purchases.',
            'Calendar weekend meaning differs across countries/eras; first/last observation is not proof of complete logging.',
            'Household and personal windows are repeated observations of two histories, not extra people; equal-entity weights prevent pseudoreplication in fitting.',
            'Population dominated by historical Czech bank accounts; two reference histories cannot establish cross-population or student validity.',
            'Real source records only, no known generated records. Household/personal authenticity cannot be independently certified from supplied metadata.',
            'Stability and silhouette are internal diagnostics, not accuracy, usefulness or psychological/student identity validation.',
            'No frozen test predictions or outcomes read; no out-of-sample persona benchmark claimed. Research artifact is not deployed.']}
    assert result['protected_berka_hashes_unchanged']
    write('metrics.json', result)
    write('protected_berka_hashes.json', before)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout='constrained')
    axes[0].boxplot([pairwise, subsample], tick_labels=['Initialization seeds', '80% entity subsamples'])
    axes[0].set(ylabel='Adjusted Rand index', title='Internal stability (development only)')
    im = axes[1].imshow(model.cluster_centers_, vmin=0, vmax=1, cmap='YlGnBu')
    axes[1].set_xticks(range(len(FEATURES)), ['Days 1–10', 'Days 11–20', 'Days 21+', 'Weekend', 'Top 20% rows', 'HHI'], rotation=35, ha='right')
    axes[1].set_yticks(range(3), list(names.values()))
    axes[1].set_title('Recorded debit timing/concentration shares')
    fig.colorbar(im, ax=axes[1], label='Share / concentration')
    fig.savefig(OUT / 'stability_and_centers.png', dpi=160)
    print(json.dumps({k: result[k] for k in ('profiles', 'distinct_recorded_entities', 'profiles_by_source', 'entities_by_source', 'silhouette_unweighted_descriptive', 'protected_berka_hashes_unchanged')}, indent=2))


if __name__ == '__main__':
    main()
