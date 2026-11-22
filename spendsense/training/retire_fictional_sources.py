"""One-time reversible retirement of known fictional sources, never personal rows."""
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = Path('E:/extra curricular/SpendSense-retired-fictional-20261119').resolve()


def main():
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / 'eval/spending_mix_v1/retirement.json'
    if manifest_path.exists():
        print('Retirement already recorded; no repeated mutation.')
        return
    names = ['data/student_profiles_synthetic.csv', 'data/student_student_spending (1).csv',
             'data/student_transactions_synthetic.csv', 'data/student_monthly_expenses.csv',
             'data/campus_demo_training.csv', 'models/campus', 'models/demo',
             'models/research/personas.joblib', 'models/research/personas.json',
             'models/kaggle_reference/personas.joblib', 'models/kaggle_reference/personas.json',
             'models/evaluation_report.json', 'demo.py']
    retired = []
    for name in names:
        source = ROOT / name
        if not source.exists():
            continue
        # models is an intentional junction; validate its resolved root separately.
        allowed = (ROOT / ('models' if name.startswith('models/') else '.')).resolve()
        if not source.resolve().is_relative_to(allowed):
            raise ValueError('Source outside expected project root: ' + name)
        destination = (ARCHIVE / name).resolve()
        assert destination.is_relative_to(ARCHIVE) and not destination.exists()
        files = sorted(source.rglob('*')) if source.is_dir() else [source]
        for path in files:
            if path.is_file():
                retired.append({'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
    db = ROOT / 'data/spendsense.db'
    with sqlite3.connect(db) as conn:
        with sqlite3.connect(ARCHIVE / 'pre_retirement_spendsense.db') as backup:
            conn.backup(backup)
        keep_sql = "NOT ((workspace='Campus demo' AND source='fictional campus scenario') OR (workspace='Demo' AND source='synthetic'))"
        before = conn.execute('SELECT * FROM transactions WHERE ' + keep_sql + ' ORDER BY id').fetchall()
        removed = conn.execute('SELECT workspace,source,COUNT(*) FROM transactions WHERE NOT (' + keep_sql + ') GROUP BY workspace,source').fetchall()
        conn.execute('DELETE FROM transactions WHERE NOT (' + keep_sql + ')')
        after = conn.execute('SELECT * FROM transactions WHERE ' + keep_sql + ' ORDER BY id').fetchall()
        assert before == after
    manifest_path.write_text(json.dumps({'archive_outside_project': str(ARCHIVE), 'retired_files': retired,
        'removed_known_generated_transaction_groups': removed, 'all_other_transaction_rows_unchanged': before == after,
        'wallets_and_user_entered_records': 'Not changed; demo workspaces removed from UI, so their retired setup cannot seed or appear as a sample.',
        'unverified_student_survey': 'Also removed; never approved as real transaction training data.'}, indent=2), encoding='utf-8')
    print('Retired', len(retired), 'files; preserved all other transaction rows.')


if __name__ == '__main__':
    main()
