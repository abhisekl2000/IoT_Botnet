'''Train an evaluate a Random Forest classifier on the MQTTset binary split.

Usage: python src/train_model.py --train data/processed/train_binary.csv --test data/processed/test_binary.csv --output-dir results/random_forest
'''
import argparse
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use('Agg')  # Save plots without needing a desktop display.
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, classification_report,
                            confusion_matrix, ConfusionMatrixDisplay,
                            precision_score, recall_score, f1_score)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train', type=Path, required=True)
    parser.add_argument('--test', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=Path('results/random_forest'))
    parser.add_argument('--trees', type=int, default=100)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    if args.trees < 1:
        parser.error('--trees must be at least 1')
    args.output_dir.mkdir(parents=True, exist_ok=True)

    train = pd.read_csv(args.train)
    test = pd.read_csv(args.test)
    if 'label' not in train or 'label' not in test:
        raise ValueError("Expected 'label' column from original preprocess_mqttset.py")
    features = train.drop(columns=['label']).columns.tolist()
    if set(test.columns) != set(train.columns):
        raise ValueError('Training and testing columns differ')
    test = test[features + ['label']]
    X_train, X_test = train[features], test[features]
    y_train, y_test = train['label'], test['label']
    if not set(y_train.unique()).issubset({0, 1}) or not set(y_test.unique()).issubset({0, 1}):
        raise ValueError('Expected binary labels: 0=legitimate, 1=attack')
    if X_train.isna().any().any() or X_test.isna().any().any():
        raise ValueError('Missing features found; run preprocessing first')
    print(f'Training on {len(train):,} records with {len(features)} features...')
    model = RandomForestClassifier(
        n_estimators=args.trees,
        random_state=args.seed,
        n_jobs=-1,
        class_weight='balanced_subsample'
    )
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    cm = confusion_matrix(y_test, predictions, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    metrics = {
        'train_rows': int(len(train)),
        'test_rows': int(len(test)),
        'features': len(features),
        'trees': args.trees,
        'accuracy': float(accuracy_score(y_test, predictions)),
        'attack_precision': float(precision_score(y_test, predictions, zero_division=0)),
        'attack_recall': float(recall_score(y_test, predictions, zero_division=0)),
        'attack_f1': float(f1_score(y_test, predictions, zero_division=0)),
        'true_negative': int(tn),
        'false_positive': int(fp),
        'false_negative': int(fn),
        'true_positive': int(tp),
    }
    (args.output_dir / 'metrics.json').write_text(json.dumps(metrics, indent=2))
    report = classification_report(y_test, predictions, labels=[0, 1],
                                    target_names=['Legitimate', 'Attack'], zero_division=0)
    (args.output_dir / 'classification_report.txt').write_text(report)
    pd.DataFrame(cm, index=['Actual legitimate', 'Actual attack'],
                columns=['Predicted legitimate', 'Predicted attack']).to_csv(
                    args.output_dir / 'confusion_matrix.csv')
    ConfusionMatrixDisplay(cm, display_labels=['Legitimate', 'Attack']).plot(
        cmap='Blues', values_format='d')
    plt.title('Random Forest: MQTTset Binary Classification')
    plt.tight_layout()
    plt.savefig(args.output_dir / 'confusion_matrix.png', dpi=160)
    plt.close()
    importance = pd.DataFrame({'feature': features,
                            'importance': model.feature_importances_})
    importance.sort_values('importance', ascending=False).to_csv(
        args.output_dir / 'feature_importance.csv', index=False)
    joblib.dump({'model': model, 'features': features,
                'label_mapping': {'legitimate': 0, 'attack': 1}},
                args.output_dir / 'random_forest.joblib')
    print('\nClassification report:\n' + report)
    print('Confusion matrix [rows: actual, columns: predicted]:\n', cm)
    print('\nAccuracy: {accuracy:.4f} | Attack precision: {attack_precision:.4f} | '
        'Attack recall: {attack_recall:.4f} | Attack F1: {attack_f1:.4f}'.format(**metrics))
    print('Results saved to:', args.output_dir)

if __name__ == '__main__':
    main()
