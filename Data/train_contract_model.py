"""
MLB Contract Advisor - ML Model Training Script
================================================
Trains Gradient Boosting models to predict MLB contract values (AAV and length).

Target Metrics (from PRD):
- Mean Absolute Error (MAE): < $3M
- Accuracy within $3M: >= 70%
- Accuracy within $5M: >= 85%
- R² Score: >= 0.75

Usage:
    python train_contract_model.py
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
import joblib
import matplotlib.pyplot as plt
import warnings
import os
from datetime import datetime

warnings.filterwarnings('ignore')

# Configuration
RANDOM_STATE = 42
TEST_SIZE = 0.2
MODEL_OUTPUT_DIR = 'Models'
PLOTS_OUTPUT_DIR = 'Master Data'

# Feature sets for batters and pitchers
BATTER_FEATURES = [
    'age_at_signing',
    'WAR_3yr',
    'wRC_plus_3yr',
    'AVG_3yr',
    'OBP_3yr',
    'SLG_3yr',
    'HR_3yr',
    'seasons_with_data',
    'year_signed',
]

BATTER_STATCAST_FEATURES = [
    'avg_exit_velo',
    'barrel_rate',
    'max_exit_velo',
    'hard_hit_pct',
]

PITCHER_FEATURES = [
    'age_at_signing',
    'WAR_3yr',
    'ERA_3yr',
    'FIP_3yr',
    'K_9_3yr',
    'BB_9_3yr',
    'IP_3yr',
    'seasons_with_data',
    'year_signed',
]

# Position encoding
POSITION_GROUPS = {
    'SP': 'SP',
    'RP': 'RP',
    'CL': 'RP',
    'P': 'SP',  # Default pitchers to SP
    'C': 'C',
    '1B': '1B',
    '2B': '2B',
    '3B': '3B',
    'SS': 'SS',
    'LF': 'OF',
    'CF': 'OF',
    'RF': 'OF',
    'OF': 'OF',
    'DH': 'DH',
}


def load_and_prepare_data(filepath):
    """Load the master dataset and prepare for training."""
    print("=" * 60)
    print("LOADING DATA")
    print("=" * 60)

    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} contracts")

    # Convert AAV to millions for easier interpretation
    df['AAV_millions'] = df['AAV'] / 1_000_000

    # Identify pitchers vs batters based on position
    pitcher_positions = ['SP', 'RP', 'CL', 'P']
    df['is_pitcher'] = df['position'].isin(pitcher_positions)

    # Map positions to groups
    df['position_group'] = df['position'].map(POSITION_GROUPS).fillna('OF')

    print(f"\nBatters: {(~df['is_pitcher']).sum()}")
    print(f"Pitchers: {df['is_pitcher'].sum()}")

    return df


def prepare_batter_features(df):
    """Prepare feature matrix for batters."""
    batters = df[~df['is_pitcher']].copy()

    # Core features
    features = BATTER_FEATURES.copy()

    # Add Statcast features if available (> 50% coverage)
    for feat in BATTER_STATCAST_FEATURES:
        coverage = batters[feat].notna().mean()
        if coverage > 0.5:
            features.append(feat)
            print(f"  Including Statcast feature: {feat} ({coverage:.1%} coverage)")

    # Position encoding (one-hot for batters)
    position_dummies = pd.get_dummies(batters['position_group'], prefix='pos')
    batters = pd.concat([batters, position_dummies], axis=1)
    position_cols = [col for col in position_dummies.columns]
    features.extend(position_cols)

    # Drop rows with missing core features
    core_features = [f for f in BATTER_FEATURES if f in features]
    batters_clean = batters.dropna(subset=core_features)

    # Fill missing Statcast with median
    for feat in BATTER_STATCAST_FEATURES:
        if feat in features:
            batters_clean[feat] = batters_clean[feat].fillna(batters_clean[feat].median())

    print(f"  Clean batters: {len(batters_clean)} (dropped {len(batters) - len(batters_clean)} with missing data)")

    X = batters_clean[features].copy()
    y_aav = batters_clean['AAV_millions'].copy()
    y_length = batters_clean['length'].copy()

    return X, y_aav, y_length, features, batters_clean


def prepare_pitcher_features(df):
    """Prepare feature matrix for pitchers."""
    pitchers = df[df['is_pitcher']].copy()

    features = PITCHER_FEATURES.copy()

    # Position encoding (SP vs RP)
    pitchers['is_starter'] = (pitchers['position_group'] == 'SP').astype(int)
    features.append('is_starter')

    # Drop rows with missing core features
    pitchers_clean = pitchers.dropna(subset=PITCHER_FEATURES)

    print(f"  Clean pitchers: {len(pitchers_clean)} (dropped {len(pitchers) - len(pitchers_clean)} with missing data)")

    X = pitchers_clean[features].copy()
    y_aav = pitchers_clean['AAV_millions'].copy()
    y_length = pitchers_clean['length'].copy()

    return X, y_aav, y_length, features, pitchers_clean


def train_model(X, y, model_name, is_classification=False):
    """Train a Gradient Boosting model with cross-validation."""
    print(f"\n  Training {model_name}...")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Gradient Boosting parameters (tuned for small dataset)
    model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        random_state=RANDOM_STATE,
    )

    # Cross-validation
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='neg_mean_absolute_error')
    print(f"    CV MAE: ${-cv_scores.mean():.2f}M (+/- ${cv_scores.std():.2f}M)")

    # Train final model
    model.fit(X_train_scaled, y_train)

    # Predictions
    y_pred = model.predict(X_test_scaled)

    # Metrics
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    # Accuracy within thresholds (for AAV)
    within_3m = np.mean(np.abs(y_test - y_pred) <= 3) * 100
    within_5m = np.mean(np.abs(y_test - y_pred) <= 5) * 100

    print(f"    Test MAE: ${mae:.2f}M")
    print(f"    Test R²: {r2:.3f}")
    print(f"    Within $3M: {within_3m:.1f}%")
    print(f"    Within $5M: {within_5m:.1f}%")

    return {
        'model': model,
        'scaler': scaler,
        'features': list(X.columns),
        'metrics': {
            'mae': mae,
            'r2': r2,
            'rmse': rmse,
            'within_3m': within_3m,
            'within_5m': within_5m,
            'cv_mae_mean': -cv_scores.mean(),
            'cv_mae_std': cv_scores.std(),
        },
        'test_data': {
            'X_test': X_test,
            'y_test': y_test,
            'y_pred': y_pred,
        }
    }


def plot_feature_importance(model_result, model_name, output_dir):
    """Create feature importance visualization."""
    model = model_result['model']
    features = model_result['features']

    importance = model.feature_importances_
    indices = np.argsort(importance)[::-1]

    plt.figure(figsize=(10, 6))
    plt.title(f'Feature Importance - {model_name}')
    plt.barh(range(len(importance)), importance[indices], align='center')
    plt.yticks(range(len(importance)), [features[i] for i in indices])
    plt.xlabel('Importance')
    plt.tight_layout()

    filepath = os.path.join(output_dir, f'feature_importance_{model_name.lower().replace(" ", "_")}.png')
    plt.savefig(filepath, dpi=150)
    plt.close()
    print(f"  Saved: {filepath}")


def plot_predictions_vs_actual(model_result, model_name, output_dir):
    """Create predictions vs actual scatter plot."""
    y_test = model_result['test_data']['y_test']
    y_pred = model_result['test_data']['y_pred']

    plt.figure(figsize=(8, 8))
    plt.scatter(y_test, y_pred, alpha=0.6, edgecolors='black', linewidth=0.5)

    # Perfect prediction line
    max_val = max(y_test.max(), y_pred.max())
    plt.plot([0, max_val], [0, max_val], 'r--', label='Perfect Prediction')

    # +/- $3M bands
    plt.fill_between([0, max_val], [0 - 3, max_val - 3], [0 + 3, max_val + 3],
                     alpha=0.2, color='green', label='Within $3M')

    plt.xlabel('Actual AAV ($M)')
    plt.ylabel('Predicted AAV ($M)')
    plt.title(f'{model_name}: Predicted vs Actual')
    plt.legend()
    plt.tight_layout()

    filepath = os.path.join(output_dir, f'predictions_{model_name.lower().replace(" ", "_")}.png')
    plt.savefig(filepath, dpi=150)
    plt.close()
    print(f"  Saved: {filepath}")


def save_model(model_result, model_name, output_dir):
    """Save model and scaler to disk."""
    os.makedirs(output_dir, exist_ok=True)

    base_name = model_name.lower().replace(" ", "_")

    # Save model
    model_path = os.path.join(output_dir, f'{base_name}_model.joblib')
    joblib.dump(model_result['model'], model_path)

    # Save scaler
    scaler_path = os.path.join(output_dir, f'{base_name}_scaler.joblib')
    joblib.dump(model_result['scaler'], scaler_path)

    # Save feature list
    features_path = os.path.join(output_dir, f'{base_name}_features.joblib')
    joblib.dump(model_result['features'], features_path)

    # Save metrics
    metrics_path = os.path.join(output_dir, f'{base_name}_metrics.joblib')
    joblib.dump(model_result['metrics'], metrics_path)

    print(f"  Saved model to: {model_path}")


def print_summary(results):
    """Print summary of all model results."""
    print("\n" + "=" * 60)
    print("MODEL TRAINING SUMMARY")
    print("=" * 60)

    print("\nTarget Metrics (from PRD):")
    print("  - MAE: < $3M")
    print("  - Within $3M: >= 70%")
    print("  - Within $5M: >= 85%")
    print("  - R²: >= 0.75")

    print("\n" + "-" * 60)
    print("RESULTS:")
    print("-" * 60)

    for name, result in results.items():
        metrics = result['metrics']
        print(f"\n{name}:")

        # MAE check
        mae_status = "PASS" if metrics['mae'] < 3 else "NEEDS IMPROVEMENT"
        print(f"  MAE: ${metrics['mae']:.2f}M [{mae_status}]")

        # Within $3M check
        w3m_status = "PASS" if metrics['within_3m'] >= 70 else "NEEDS IMPROVEMENT"
        print(f"  Within $3M: {metrics['within_3m']:.1f}% [{w3m_status}]")

        # Within $5M check
        w5m_status = "PASS" if metrics['within_5m'] >= 85 else "NEEDS IMPROVEMENT"
        print(f"  Within $5M: {metrics['within_5m']:.1f}% [{w5m_status}]")

        # R² check
        r2_status = "PASS" if metrics['r2'] >= 0.75 else "NEEDS IMPROVEMENT"
        print(f"  R²: {metrics['r2']:.3f} [{r2_status}]")


def main():
    """Main training pipeline."""
    print("\n" + "=" * 60)
    print("MLB CONTRACT ADVISOR - MODEL TRAINING")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, 'Master Data', 'master_contract_dataset.csv')
    model_dir = os.path.join(script_dir, MODEL_OUTPUT_DIR)
    plots_dir = os.path.join(script_dir, PLOTS_OUTPUT_DIR)

    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)

    # Load data
    df = load_and_prepare_data(data_path)

    results = {}

    # Train batter models
    print("\n" + "=" * 60)
    print("TRAINING BATTER MODELS")
    print("=" * 60)

    X_bat, y_aav_bat, y_len_bat, bat_features, batters_df = prepare_batter_features(df)
    print(f"\nFeatures ({len(bat_features)}): {bat_features}")

    # Batter AAV model
    batter_aav_result = train_model(X_bat, y_aav_bat, "Batter AAV")
    results['Batter AAV'] = batter_aav_result
    save_model(batter_aav_result, 'batter_aav', model_dir)
    plot_feature_importance(batter_aav_result, 'Batter AAV', plots_dir)
    plot_predictions_vs_actual(batter_aav_result, 'Batter AAV', plots_dir)

    # Batter Length model
    batter_len_result = train_model(X_bat, y_len_bat, "Batter Length")
    results['Batter Length'] = batter_len_result
    save_model(batter_len_result, 'batter_length', model_dir)
    plot_feature_importance(batter_len_result, 'Batter Length', plots_dir)

    # Train pitcher models
    print("\n" + "=" * 60)
    print("TRAINING PITCHER MODELS")
    print("=" * 60)

    X_pit, y_aav_pit, y_len_pit, pit_features, pitchers_df = prepare_pitcher_features(df)
    print(f"\nFeatures ({len(pit_features)}): {pit_features}")

    if len(X_pit) >= 10:  # Need minimum samples
        # Pitcher AAV model
        pitcher_aav_result = train_model(X_pit, y_aav_pit, "Pitcher AAV")
        results['Pitcher AAV'] = pitcher_aav_result
        save_model(pitcher_aav_result, 'pitcher_aav', model_dir)
        plot_feature_importance(pitcher_aav_result, 'Pitcher AAV', plots_dir)
        plot_predictions_vs_actual(pitcher_aav_result, 'Pitcher AAV', plots_dir)

        # Pitcher Length model
        pitcher_len_result = train_model(X_pit, y_len_pit, "Pitcher Length")
        results['Pitcher Length'] = pitcher_len_result
        save_model(pitcher_len_result, 'pitcher_length', model_dir)
        plot_feature_importance(pitcher_len_result, 'Pitcher Length', plots_dir)
    else:
        print(f"\n  Insufficient pitcher data ({len(X_pit)} samples). Skipping pitcher models.")

    # Print summary
    print_summary(results)

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"\nModels saved to: {model_dir}")
    print(f"Plots saved to: {plots_dir}")
    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return results


if __name__ == '__main__':
    results = main()
