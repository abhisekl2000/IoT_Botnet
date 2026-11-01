'''Audit conflicting MQTTset labels for identical *retained model inputs*.
Run: python src/report_conflicts.py --input data/raw/mqttdatset_reduced.csv --output-dir results/conflicts
'''
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

DROP = ['mqtt.msg', 'mqtt.msgid']
HEX = ['tcp.flags', 'mqtt.hdrflags']

def parse_hex(value):
    if pd.isna(value): return np.nan
    s = str(value).strip()
    if not s or s.lower() in ('nan', 'none'): return np.nan
    try: return int(s,16) if s.lower().startswith('0x') else float(s)
    except ValueError: return np.nan

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, default=Path('results/conflicts'))
    a = p.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(a.input, low_memory=False)
    df.columns = df.columns.str.strip()
    if 'target' not in df: raise ValueError('Missing target column')
    df['target'] = df['target'].astype('string').str.strip().str.lower()
    X = df.dropna(subset=['target']).copy()
    for col in HEX:
        if col in X: X[col] = X[col].map(parse_hex)
    for col in X: X[col] = pd.to_numeric(X[col], errors='coerce')
    X = X.replace([np.inf, -np.inf], np.nan)

    # same feature definition and hash operation as preprocess_mqttset.py
    key = pd.util.hash_pandas_object(X, index=False)
    label_counts = df.groupby(key)['target'].nunique()
    conflict_groups = label_counts[label_counts > 1].index
    mask = key.isin(conflict_groups)

    audit = pd.DataFrame({'group_hash': key.to_numpy(), 'target': df['target'].to_numpy(), 'conflict': mask.to_numpy()})
    class_summary = pd.crosstab(audit['target'], audit['conflict']).rename(columns={False:'nonconflicting_rows', True:'conflicting_rows'})
    for col in ['nonconflicting_rows','conflicting_rows']:
        if col not in class_summary: class_summary[col] = 0
    class_summary['total_rows'] = class_summary['nonconflicting_rows'] + class_summary['conflicting_rows']
    class_summary['conflict_pct'] = (100 * class_summary['conflicting_rows'] / class_summary['total_rows']).round(2)
    class_summary.to_csv(a.output_dir / 'conflicts_by_class.csv')

    conflicted = audit.loc[audit['conflict']]
    table = pd.crosstab(conflicted['group_hash'], conflicted['target'])
    table['total_rows'] = table.sum(axis=1)
    table['number_of_labels'] = (table.drop(columns='total_rows') > 0).sum(axis=1)
    table.sort_values('total_rows', ascending=False).head(100).to_csv(a.output_dir / 'top_100_conflicting_groups.csv')

    if 'mqtt.msgtype' in df:
        pd.crosstab(df.loc[mask, 'mqtt.msgtype'], df.loc[mask, 'target']).to_csv(a.output_dir / 'conflicts_by_mqtt_msgtype.csv')

    summary = [
        f'Total rows: {len(df):,}',
        f'Unique retained-feature groups: {len(label_counts):,}',
        f'Conflicting groups: {len(conflict_groups):,}',
        f'Rows in conflicting groups: {int(mask.sum()):,} ({100 * mask.mean():.2f}%)',
        f'Conflicting groups contatining both legitimate and attack labels: {int((table.get("legitimate", pd.Series(0, index=table.index)) > 0).sum()):,}',
        '', 'IMPORTANT: Identical model inputs with different labels are ambigious at this feature granularity.',
        'This is not proof of ground-truth labels. Do not delete these rows automatically.',
        'Hash values are group identifiers, not interpretable features. Grouping is by the exact',
        'post-conversion input representation used by preprocess_mqttset.py'
        'This audit does not establish caputre-session independence.'
    ]
    (a.output_dir / 'summary.txt').write_text('\n'.join(summary) + '\n')
    print('\n'.join(summary))
    print('\nBy class:\n', class_summary.to_string())
    print('\nFiles saved to:', a.output_dir)

if __name__ == '__main__':
    main()