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
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
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
USE_LOG_TRANSFORM = True  # Log-transform AAV for better handling of skewed distribution
USE_XGBOOST = True  # Use XGBoost instead of sklearn GradientBoosting (requires: pip install xgboost)
TRAIN_QUANTILE_MODELS = True  # Train additional models for prediction intervals (10th and 90th percentile)

# Try to import XGBoost
XGBOOST_AVAILABLE = False
if USE_XGBOOST:
    try:
        import xgboost as xgb
        # Test that it actually works (not just installed but with missing dependencies)
        _ = xgb.XGBRegressor(n_estimators=1, verbosity=0)
        XGBOOST_AVAILABLE = True
    except Exception as e:
        print(f"Warning: XGBoost not available ({type(e).__name__})")
        print("Falling back to sklearn GradientBoosting")

# Feature sets for batters and pitchers
# NOTE: year_signed removed to prevent feature leakage (model learning market inflation vs player value)
BATTER_FEATURES = [
    'age_at_signing',
    'WAR_3yr',
    'wRC_plus_3yr',
    'AVG_3yr',
    'OBP_3yr',
    'SLG_3yr',
    'HR_3yr',
    'seasons_with_data',
]

# Derived features with higher predictive power
BATTER_DERIVED_FEATURES = [
    'peak_efficiency',   # WAR_3yr / age_at_signing - captures young elite value
    'ISO_3yr',           # SLG_3yr - AVG_3yr - isolates pure power
    'power_consistency', # avg_exit_velo * barrel_rate / 100 - repeatable power
]

PITCHER_DERIVED_FEATURES = [
    'peak_efficiency',   # WAR_3yr / age_at_signing - captures young elite value
    'control_metric',    # K_9_3yr - BB_9_3yr - command quality
]

BATTER_STATCAST_FEATURES = [
    'avg_exit_velo',
    'barrel_rate',
    'max_exit_velo',
    'hard_hit_pct',
    'chase_rate',  # Plate discipline percentile (0-100)
    'whiff_rate',  # Plate discipline percentile (0-100)
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
]

PITCHER_STATCAST_FEATURES = [
    'fb_velocity',  # Fastball velocity percentile (0-100)
    'fb_spin',  # Fastball spin percentile (0-100)
    'xera',  # Expected ERA percentile (0-100)
    'k_percent',  # K% percentile (0-100)
    'bb_percent',  # BB% percentile (0-100)
    'whiff_percent_pitcher',  # Whiff% induced percentile (0-100)
    'chase_percent_pitcher',  # Chase% induced percentile (0-100)
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

    # Log-transform AAV for better handling of skewed distribution
    df['AAV_log'] = np.log(df['AAV_millions'] + 0.1)  # +0.1 to handle very small values

    # Identify pitchers vs batters based on position
    pitcher_positions = ['SP', 'RP', 'CL', 'P']
    df['is_pitcher'] = df['position'].isin(pitcher_positions)

    # Map positions to groups
    df['position_group'] = df['position'].map(POSITION_GROUPS).fillna('OF')

    # Compute derived features for batters
    df['peak_efficiency'] = df['WAR_3yr'] / df['age_at_signing']
    df['ISO_3yr'] = df['SLG_3yr'] - df['AVG_3yr']
    df['power_consistency'] = df['avg_exit_velo'] * df['barrel_rate'] / 100

    # Compute derived features for pitchers
    df['control_metric'] = df['K_9_3yr'] - df['BB_9_3yr']

    print(f"\nBatters: {(~df['is_pitcher']).sum()}")
    print(f"Pitchers: {df['is_pitcher'].sum()}")
    print("Derived features computed: peak_efficiency, ISO_3yr, power_consistency, control_metric")

    return df


def prepare_batter_features(df):
    """Prepare feature matrix for batters."""
    batters = df[~df['is_pitcher']].copy()

    # Core features
    features = BATTER_FEATURES.copy()

    # Add derived features
    for feat in BATTER_DERIVED_FEATURES:
        if feat in batters.columns:
            coverage = batters[feat].notna().mean()
            if coverage > 0.5:
                features.append(feat)
                print(f"  Including derived feature: {feat} ({coverage:.1%} coverage)")

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

    # Add binary flag for Statcast data availability (pre-2015 contracts have no Statcast)
    batters_clean['has_statcast'] = batters_clean['avg_exit_velo'].notna().astype(int)
    features.append('has_statcast')
    print(f"  Including has_statcast flag ({batters_clean['has_statcast'].mean():.1%} have Statcast)")

    # Fill missing derived features with position-specific median
    for feat in BATTER_DERIVED_FEATURES:
        if feat in features:
            batters_clean[feat] = batters_clean.groupby('position_group')[feat].transform(
                lambda x: x.fillna(x.median())
            )
            # Fallback to global median if position group has no data
            batters_clean[feat] = batters_clean[feat].fillna(batters_clean[feat].median())

    # Fill missing Statcast with position-specific median
    for feat in BATTER_STATCAST_FEATURES:
        if feat in features:
            batters_clean[feat] = batters_clean.groupby('position_group')[feat].transform(
                lambda x: x.fillna(x.median())
            )
            # Fallback to global median if position group has no data
            batters_clean[feat] = batters_clean[feat].fillna(batters_clean[feat].median())

    print(f"  Clean batters: {len(batters_clean)} (dropped {len(batters) - len(batters_clean)} with missing data)")

    X = batters_clean[features].copy()
    y_aav = batters_clean['AAV_millions'].copy()
    y_aav_log = batters_clean['AAV_log'].copy()
    y_length = batters_clean['length'].copy()

    return X, y_aav, y_aav_log, y_length, features, batters_clean


def prepare_pitcher_features(df):
    """Prepare feature matrix for pitchers."""
    pitchers = df[df['is_pitcher']].copy()

    features = PITCHER_FEATURES.copy()

    # Add derived features
    for feat in PITCHER_DERIVED_FEATURES:
        if feat in pitchers.columns:
            coverage = pitchers[feat].notna().mean()
            if coverage > 0.5:
                features.append(feat)
                print(f"  Including derived feature: {feat} ({coverage:.1%} coverage)")

    # Add Statcast features if available (> 50% coverage)
    for feat in PITCHER_STATCAST_FEATURES:
        if feat in pitchers.columns:
            coverage = pitchers[feat].notna().mean()
            if coverage > 0.5:
                features.append(feat)
                print(f"  Including Statcast feature: {feat} ({coverage:.1%} coverage)")

    # Position encoding (SP vs RP)
    pitchers['is_starter'] = (pitchers['position_group'] == 'SP').astype(int)
    features.append('is_starter')

    # Drop rows with missing core features
    pitchers_clean = pitchers.dropna(subset=PITCHER_FEATURES)

    # Add binary flag for Statcast data availability (pre-2015 contracts have no Statcast)
    pitchers_clean['has_statcast'] = pitchers_clean['fb_velocity'].notna().astype(int)
    features.append('has_statcast')
    print(f"  Including has_statcast flag ({pitchers_clean['has_statcast'].mean():.1%} have Statcast)")

    # Fill missing derived features with position-specific median (SP vs RP)
    for feat in PITCHER_DERIVED_FEATURES:
        if feat in features and feat in pitchers_clean.columns:
            pitchers_clean[feat] = pitchers_clean.groupby('is_starter')[feat].transform(
                lambda x: x.fillna(x.median())
            )
            # Fallback to global median
            pitchers_clean[feat] = pitchers_clean[feat].fillna(pitchers_clean[feat].median())

    # Fill missing Statcast with position-specific median (SP vs RP)
    for feat in PITCHER_STATCAST_FEATURES:
        if feat in features and feat in pitchers_clean.columns:
            pitchers_clean[feat] = pitchers_clean.groupby('is_starter')[feat].transform(
                lambda x: x.fillna(x.median())
            )
            # Fallback to global median
            pitchers_clean[feat] = pitchers_clean[feat].fillna(pitchers_clean[feat].median())

    print(f"  Clean pitchers: {len(pitchers_clean)} (dropped {len(pitchers) - len(pitchers_clean)} with missing data)")

    X = pitchers_clean[features].copy()
    y_aav = pitchers_clean['AAV_millions'].copy()
    y_aav_log = pitchers_clean['AAV_log'].copy()
    y_length = pitchers_clean['length'].copy()

    return X, y_aav, y_aav_log, y_length, features, pitchers_clean


def train_model(X, y, model_name, df_with_years=None, is_log_transformed=False, y_original=None, is_classification=False):
    """Train a Gradient Boosting model with cross-validation.

    If df_with_years is provided, uses temporal split (train on 2019-2024, test on 2025-2026).
    If is_log_transformed=True and y_original is provided, metrics are computed on original scale.
    """
    print(f"\n  Training {model_name}...")

    # Use temporal split if year data is available
    if df_with_years is not None and 'year_signed' in df_with_years.columns:
        # NOTE: 2026 data appears to be projected/arbitration contracts with avg AAV ~$6M
        # vs actual FA contracts (2019-2024) averaging ~$17-25M.
        # Use stratified random split instead for now, with year as stratification.
        # This ensures each split has similar year distribution.

        # For small datasets, use random split with stratification by year buckets
        year_buckets = pd.cut(df_with_years['year_signed'], bins=[2018, 2023, 2025, 2027], labels=['early', 'mid', 'recent'])

        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE,
                stratify=year_buckets
            )
            print(f"    Stratified split by year: train {len(X_train)}, test {len(X_test)}")
        except ValueError:
            # If stratification fails (too few samples in a stratum), fall back to random
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
            )
            print(f"    Random split (stratification failed): train {len(X_train)}, test {len(X_test)}")
    else:
        # Fallback to random split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
        )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Choose model type: XGBoost or sklearn GradientBoosting
    use_xgboost = USE_XGBOOST and XGBOOST_AVAILABLE

    if use_xgboost:
        # XGBoost with GridSearchCV
        param_grid = {
            'n_estimators': [50, 100, 200],
            'max_depth': [3, 4, 5, 6],
            'learning_rate': [0.05, 0.1, 0.15],
            'min_child_weight': [1, 3, 5],  # XGBoost equivalent of min_samples_leaf
        }

        base_model = xgb.XGBRegressor(
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=RANDOM_STATE,
            verbosity=0,
        )
        print(f"    Using XGBoost with GridSearchCV ({len(param_grid['n_estimators']) * len(param_grid['max_depth']) * len(param_grid['learning_rate']) * len(param_grid['min_child_weight'])} combinations)...")
    else:
        # sklearn GradientBoosting with GridSearchCV
        param_grid = {
            'n_estimators': [50, 100, 200],
            'max_depth': [3, 4, 5, 6],
            'learning_rate': [0.05, 0.1, 0.15],
            'min_samples_leaf': [1, 3, 5],
        }

        base_model = GradientBoostingRegressor(
            subsample=0.8,
            random_state=RANDOM_STATE,
        )
        print(f"    Using sklearn GradientBoosting with GridSearchCV ({len(param_grid['n_estimators']) * len(param_grid['max_depth']) * len(param_grid['learning_rate']) * len(param_grid['min_samples_leaf'])} combinations)...")

    grid_search = GridSearchCV(
        base_model,
        param_grid,
        cv=5,
        scoring='neg_mean_absolute_error',
        n_jobs=-1,
        verbose=0
    )
    grid_search.fit(X_train_scaled, y_train)

    model = grid_search.best_estimator_
    best_params = grid_search.best_params_
    cv_score = -grid_search.best_score_

    print(f"    Best params: {best_params}")
    print(f"    CV MAE: ${cv_score:.2f}M")

    # Predictions
    y_pred = model.predict(X_test_scaled)

    # If log-transformed, convert back to original scale for metrics
    if is_log_transformed and y_original is not None:
        # Get original scale values for test set
        # Must use the same split as we used for X and y
        if df_with_years is not None and 'year_signed' in df_with_years.columns:
            year_buckets = pd.cut(df_with_years['year_signed'], bins=[2018, 2023, 2025, 2027], labels=['early', 'mid', 'recent'])
            try:
                _, y_test_original = train_test_split(
                    y_original, test_size=TEST_SIZE, random_state=RANDOM_STATE,
                    stratify=year_buckets
                )
            except ValueError:
                _, y_test_original = train_test_split(
                    y_original, test_size=TEST_SIZE, random_state=RANDOM_STATE
                )
        else:
            # Random split - need to track original y
            _, y_test_original = train_test_split(
                y_original, test_size=TEST_SIZE, random_state=RANDOM_STATE
            )

        # Convert predictions back to original scale
        y_pred_original = np.exp(y_pred) - 0.1  # Reverse log transform

        # Compute metrics on original scale
        mae = mean_absolute_error(y_test_original, y_pred_original)
        r2 = r2_score(y_test_original, y_pred_original)
        rmse = np.sqrt(mean_squared_error(y_test_original, y_pred_original))
        within_3m = np.mean(np.abs(y_test_original - y_pred_original) <= 3) * 100
        within_5m = np.mean(np.abs(y_test_original - y_pred_original) <= 5) * 100

        print(f"    Test MAE: ${mae:.2f}M (original scale)")
        print(f"    Test R²: {r2:.3f} (original scale)")
    else:
        # Standard metrics
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
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
        'is_log_transformed': is_log_transformed,
        'metrics': {
            'mae': mae,
            'r2': r2,
            'rmse': rmse,
            'within_3m': within_3m,
            'within_5m': within_5m,
            'cv_mae': cv_score,
            'best_params': best_params,
        },
        'test_data': {
            'X_test': X_test,
            'y_test': y_test,
            'y_pred': y_pred,
        }
    }


def train_quantile_models(X, y, model_name, df_with_years=None, is_log_transformed=False):
    """Train quantile regression models for prediction intervals.

    Returns models for 10th and 90th percentiles.
    """
    print(f"\n  Training quantile models for {model_name}...")

    # Use temporal split if year data is available
    if df_with_years is not None and 'year_signed' in df_with_years.columns:
        train_mask = df_with_years['year_signed'] <= 2024
        X_train = X[train_mask]
        y_train = y[train_mask]
    else:
        X_train, _, y_train, _ = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
        )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    # Train quantile models using GradientBoosting with quantile loss
    # Note: XGBoost also supports quantile regression but sklearn is simpler here
    quantile_models = {}

    for alpha, name in [(0.10, 'low'), (0.90, 'high')]:
        model = GradientBoostingRegressor(
            loss='quantile',
            alpha=alpha,
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            random_state=RANDOM_STATE,
        )
        model.fit(X_train_scaled, y_train)
        quantile_models[name] = model
        print(f"    Trained {name} ({int(alpha*100)}th percentile) model")

    return {
        'models': quantile_models,
        'scaler': scaler,
        'features': list(X.columns),
        'is_log_transformed': is_log_transformed,
    }


def save_quantile_models(quantile_result, model_name, output_dir):
    """Save quantile models for prediction intervals."""
    os.makedirs(output_dir, exist_ok=True)
    base_name = model_name.lower().replace(" ", "_")

    # Save low (10th percentile) model
    low_path = os.path.join(output_dir, f'{base_name}_quantile_low.joblib')
    joblib.dump(quantile_result['models']['low'], low_path)

    # Save high (90th percentile) model
    high_path = os.path.join(output_dir, f'{base_name}_quantile_high.joblib')
    joblib.dump(quantile_result['models']['high'], high_path)

    print(f"  Saved quantile models: {base_name}_quantile_low.joblib, {base_name}_quantile_high.joblib")


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

    # Save model config (including log transform flag)
    config_path = os.path.join(output_dir, f'{base_name}_config.joblib')
    config = {
        'is_log_transformed': model_result.get('is_log_transformed', False),
    }
    joblib.dump(config, config_path)

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

    X_bat, y_aav_bat, y_aav_log_bat, y_len_bat, bat_features, batters_df = prepare_batter_features(df)
    print(f"\nFeatures ({len(bat_features)}): {bat_features}")

    # Batter AAV model (with log transform if enabled)
    if USE_LOG_TRANSFORM:
        print("\n  Using log-transformed AAV target")
        batter_aav_result = train_model(
            X_bat, y_aav_log_bat, "Batter AAV",
            df_with_years=batters_df,
            is_log_transformed=True,
            y_original=y_aav_bat
        )
    else:
        batter_aav_result = train_model(X_bat, y_aav_bat, "Batter AAV", df_with_years=batters_df)
    results['Batter AAV'] = batter_aav_result
    save_model(batter_aav_result, 'batter_aav', model_dir)
    plot_feature_importance(batter_aav_result, 'Batter AAV', plots_dir)
    plot_predictions_vs_actual(batter_aav_result, 'Batter AAV', plots_dir)

    # Train quantile models for prediction intervals (AAV only)
    if TRAIN_QUANTILE_MODELS:
        y_target = y_aav_log_bat if USE_LOG_TRANSFORM else y_aav_bat
        batter_quantile = train_quantile_models(
            X_bat, y_target, "Batter AAV",
            df_with_years=batters_df,
            is_log_transformed=USE_LOG_TRANSFORM
        )
        save_quantile_models(batter_quantile, 'batter_aav', model_dir)

    # Batter Length model (no log transform for length)
    batter_len_result = train_model(X_bat, y_len_bat, "Batter Length", df_with_years=batters_df)
    results['Batter Length'] = batter_len_result
    save_model(batter_len_result, 'batter_length', model_dir)
    plot_feature_importance(batter_len_result, 'Batter Length', plots_dir)

    # Train pitcher models
    print("\n" + "=" * 60)
    print("TRAINING PITCHER MODELS")
    print("=" * 60)

    X_pit, y_aav_pit, y_aav_log_pit, y_len_pit, pit_features, pitchers_df = prepare_pitcher_features(df)
    print(f"\nFeatures ({len(pit_features)}): {pit_features}")

    if len(X_pit) >= 10:  # Need minimum samples
        # Pitcher AAV model (with log transform if enabled)
        if USE_LOG_TRANSFORM:
            print("\n  Using log-transformed AAV target")
            pitcher_aav_result = train_model(
                X_pit, y_aav_log_pit, "Pitcher AAV",
                df_with_years=pitchers_df,
                is_log_transformed=True,
                y_original=y_aav_pit
            )
        else:
            pitcher_aav_result = train_model(X_pit, y_aav_pit, "Pitcher AAV", df_with_years=pitchers_df)
        results['Pitcher AAV'] = pitcher_aav_result
        save_model(pitcher_aav_result, 'pitcher_aav', model_dir)
        plot_feature_importance(pitcher_aav_result, 'Pitcher AAV', plots_dir)
        plot_predictions_vs_actual(pitcher_aav_result, 'Pitcher AAV', plots_dir)

        # Train quantile models for prediction intervals (AAV only)
        if TRAIN_QUANTILE_MODELS:
            y_target = y_aav_log_pit if USE_LOG_TRANSFORM else y_aav_pit
            pitcher_quantile = train_quantile_models(
                X_pit, y_target, "Pitcher AAV",
                df_with_years=pitchers_df,
                is_log_transformed=USE_LOG_TRANSFORM
            )
            save_quantile_models(pitcher_quantile, 'pitcher_aav', model_dir)

        # Pitcher Length model (no log transform for length)
        pitcher_len_result = train_model(X_pit, y_len_pit, "Pitcher Length", df_with_years=pitchers_df)
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
