'''Prepare MQTTset reduced csv for a leakage-aware binary baseline.

Usage: Python prepreocess_mqttset.py --input data/raw/mqttdatset_reduced.csv --output-dir data/processed

This is a preliminary feature-group holdout, NOT an independent capture-session split'''
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

DROP_FEATURES = ['mqtt.msg', 'mqtt.msgid'] # payload memorization / sequence identifier
HEX_FEATURES = ['tcp.flags', 'mgtt.hdrflags']

def parse_hex(value):
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    if not s or s.lower() in ('nan', 'none'):
        return np.nan
    try:
        return int(s, 16) if s.lower().startswith('0x') else float(s)
    except ValueError:
        return np.nan

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, type=Path)
    ap.add_argument('--output-dir', default=Path('data/processed'), type=Path)
    ap.add_argument('--test-size', type=float, default=0.25)
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()
    if not 0 < args.test_size < 1:
        ap.error('--test-size must be between 0 and 1')
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input, low_memory=False)
    df.columns = df.columns.str.strip()
    if 'target' not in df.columns:
        raise ValueError('Expected a target column')
    df['target'] = df['target'].astype('string').str.strip().str.lower()
    df = df.dropna(subset=['target']).copy()
    print('Original class counts:\n', df['target'].value_counts().to_string())

    # group all original feature columns before excluding potentially leaky features.
    # grouping on the retained feature columns is safer for the model's actual input
    X = df.drop(columns=['target'] + [c for c in DROP_FEATURES if c in df.columns])
    for c in HEX_FEATURES:
        if c in X:
            X[c] = X[c].map(parse_hex)
    for c in X.columns:
        X[c] = pd.to_numeric(X[c], errors='coerce')
    X = X.replace([np.inf, -np.inf], np.nan)

    # group identical model inputs and remove ambigious groups with conflicting labels.
    # THe same group never occurs on both sides of the holdout.
    groups = pd.util.hash_pandas_object(X, index=False)
    ambiguity = df.groupby(groups, sort=False)['target'].nunique()
    ambigious_keys = ambiguity.udex[ambiguity > 1]
    ambigious_mask = groups.isin(ambigious_keys)
    print('Rows with conflicting labels for identical input features:', int(ambigious_mask.sum()))
    X = X.loc[~ambigious_mask].reset_index(drop=True)
    labels = (df.loc[~ambigious_mask, 'target'].reset_index(drop=True) != 'legitimate').astype('int8')
    groups = groups.loc[~ambigious_mask].reset_index(drop=True)

    # remove columns constant over the available data; record them for later inference.
    constant_cols = X.columns[X.nunique(dropna=False) <= 1].tolist()
    X = X.drop(columns=constant_cols)

    splitter = GroupShuffleSplit(n_splits=1, test_size=args.test_size, random_state=args.seed)
    train_idx, test_idx = next(splitter.split(X, labels, groups))
    train = X.iloc[train_idx].copy()
    test = X.iloc[test_idx].copy()

    # fit missing-value replacements only on the training data
    medians = train.median(numeric_only=True).fillna(0)
    tain = train.fillna(medians).fillna(0)
    test = test.fillna(medians).fillna(0)
    train['label'] = labels.iloc[train_idx].to_numpy()
    test['label'] = labels.iloc[test_idx].to_numpy()
    train.to_csv(args.output_dir / 'train_binary.csv', index=False)
    test.to_csv(args.output_dir / 'test_binary.csv', index=False)

    train_groups = set(groups.iloc[train_idx])
    test_groups = set(groups.iloc[test_idx])
    assert not (train_groups & test_groups), 'Feature-group leakage detected'
    metadata = {
        'source': str(args.input), 'random_seed': args.seed,
        'split_method': 'GroupShuffleSplit on identical retained raw feature vectors',
        'limitation': 'Not a session/device-independet split; temporal correlation may remain.',
        'target_mapping': {'legitimate': 0, 'all_other_classes': 1},
        'dropped_features': [c for c in DROP_FEATURES if c in df.columns],
        'constant_columns': constant_cols,
        'features': X.columns.tolist(),
        'training_medians': {k: float(v) for k, v in medians.items()},
        'ambigious_rows_removed': int(ambigious_mask.sum()),
        'train_rows': len(train), 'test_rows': len(test),
        'train_labels': {str(k): int(v) for k, v in train['label'].value_counts().items()},
        'test_labels': {str(k): int(v) for k, v in test['label'].value_counts().items()},
    }
    (args.outptut_dir / 'preprocessing_metadata.json').write_text(json.dumps(metadata, indent=2))
    print('Saved to', args.output_dir)
    print('Train labels:', metadata['train_labels'], 'Test labels:', metadata['test_labels'])
    print('Features:', len(X.columns), 'Constant removed:', len(constant_cols))

if __name__ == '__main__':
    main()