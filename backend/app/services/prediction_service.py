"""
ML Prediction Service - Loads models and makes predictions.
"""
import logging
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import MODELS_DIR, MASTER_DATA_DIR
from app.models.schemas import PredictionRequest, ComparablePlayer
from app.utils import (
    is_pitcher as check_is_pitcher,
    get_position_group,
    get_current_year,
    PITCHER_POSITIONS,
    POSITION_GROUPS,
    DEFAULT_BATTER_STATS,
    DEFAULT_PITCHER_STATS,
    MAX_CONFIDENCE_SCORE,
)

logger = logging.getLogger(__name__)


class PredictionService:
    """Service for loading ML models and making contract predictions."""

    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.features = {}
        self.metrics = {}
        self.configs = {}
        self.quantile_models = {}  # For prediction intervals
        self.contracts_df = None
        self._loaded = False

    def load_models(self) -> bool:
        """Load all trained models from disk."""
        try:
            model_types = ['batter_aav', 'batter_length', 'pitcher_aav', 'pitcher_length']

            for model_type in model_types:
                model_path = MODELS_DIR / f"{model_type}_model.joblib"
                scaler_path = MODELS_DIR / f"{model_type}_scaler.joblib"
                features_path = MODELS_DIR / f"{model_type}_features.joblib"
                metrics_path = MODELS_DIR / f"{model_type}_metrics.joblib"
                config_path = MODELS_DIR / f"{model_type}_config.joblib"

                if model_path.exists():
                    self.models[model_type] = joblib.load(model_path)
                    self.scalers[model_type] = joblib.load(scaler_path)
                    self.features[model_type] = joblib.load(features_path)
                    self.metrics[model_type] = joblib.load(metrics_path)

                    # Load config if available (for log transform flag)
                    if config_path.exists():
                        self.configs[model_type] = joblib.load(config_path)
                    else:
                        self.configs[model_type] = {'is_log_transformed': False}

                    # Load quantile models for AAV predictions
                    if 'aav' in model_type:
                        q_low_path = MODELS_DIR / f"{model_type}_quantile_low.joblib"
                        q_high_path = MODELS_DIR / f"{model_type}_quantile_high.joblib"
                        if q_low_path.exists() and q_high_path.exists():
                            self.quantile_models[model_type] = {
                                'low': joblib.load(q_low_path),
                                'high': joblib.load(q_high_path),
                            }

            # Load contracts for comparables
            # Try multiple paths for the master dataset
            possible_paths = [
                MASTER_DATA_DIR / "master_contract_dataset.csv",  # backend folder
                MASTER_DATA_DIR.parent / "Data" / "Master Data" / "master_contract_dataset.csv",  # project root
            ]
            for contracts_path in possible_paths:
                if contracts_path.exists():
                    self.contracts_df = pd.read_csv(contracts_path)
                    break

            self._loaded = len(self.models) >= 4
            return self._loaded

        except Exception as e:
            logger.exception("Error loading models: %s", e)
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def is_pitcher(self, position: str) -> bool:
        """Check if position is a pitcher."""
        return check_is_pitcher(position)

    def predict(self, request: PredictionRequest) -> Dict:
        """
        Make contract prediction for a player.

        Returns dict with:
        - predicted_aav (in millions)
        - predicted_length
        - confidence_score
        - comparables
        - feature_importance
        """
        if not self._loaded:
            raise RuntimeError("Models not loaded")

        position_is_pitcher = self.is_pitcher(request.position)
        current_year = get_current_year()

        if position_is_pitcher:
            return self._predict_pitcher(request, current_year)
        else:
            return self._predict_batter(request, current_year)

    def _predict_batter(self, request: PredictionRequest, year: int) -> Dict:
        """Make prediction for a batter."""
        # Get position group and create one-hot encoding
        pos_group = get_position_group(request.position)

        # Build feature vector matching training order
        features = self.features['batter_aav']
        feature_values = {}

        # Core features (use defaults from utils for missing values)
        feature_values['age_at_signing'] = request.age
        feature_values['WAR_3yr'] = request.war_3yr
        feature_values['wRC_plus_3yr'] = request.wrc_plus_3yr or DEFAULT_BATTER_STATS['wrc_plus']
        feature_values['AVG_3yr'] = request.avg_3yr or DEFAULT_BATTER_STATS['avg']
        feature_values['OBP_3yr'] = request.obp_3yr or DEFAULT_BATTER_STATS['obp']
        feature_values['SLG_3yr'] = request.slg_3yr or DEFAULT_BATTER_STATS['slg']
        feature_values['HR_3yr'] = request.hr_3yr or DEFAULT_BATTER_STATS['hr']
        feature_values['seasons_with_data'] = 3

        # Statcast features (use defaults for missing values)
        avg_exit_velo = request.avg_exit_velo or DEFAULT_BATTER_STATS['exit_velo']
        barrel_rate = request.barrel_rate or DEFAULT_BATTER_STATS['barrel_rate']
        feature_values['avg_exit_velo'] = avg_exit_velo
        feature_values['barrel_rate'] = barrel_rate
        feature_values['max_exit_velo'] = request.max_exit_velo or DEFAULT_BATTER_STATS['max_exit_velo']
        feature_values['hard_hit_pct'] = request.hard_hit_pct or DEFAULT_BATTER_STATS['hard_hit_pct']
        feature_values['chase_rate'] = request.chase_rate or DEFAULT_BATTER_STATS['chase_rate']
        feature_values['whiff_rate'] = request.whiff_rate or DEFAULT_BATTER_STATS['whiff_rate']

        # Derived features (computed from other features)
        feature_values['peak_efficiency'] = request.war_3yr / request.age if request.age > 0 else 0
        feature_values['ISO_3yr'] = feature_values['SLG_3yr'] - feature_values['AVG_3yr']
        feature_values['power_consistency'] = avg_exit_velo * barrel_rate / 100

        # Has Statcast flag (1 if user provided any Statcast data)
        has_statcast = request.avg_exit_velo is not None or request.barrel_rate is not None
        feature_values['has_statcast'] = 1 if has_statcast else 0

        # Position one-hot encoding
        for pos in ['1B', '2B', '3B', 'C', 'DH', 'OF', 'SS']:
            feature_values[f'pos_{pos}'] = 1 if pos_group == pos else 0

        # Create feature array in correct order
        X = np.array([[feature_values.get(f, 0) for f in features]])

        # Scale and predict AAV
        X_scaled = self.scalers['batter_aav'].transform(X)
        predicted_aav_raw = self.models['batter_aav'].predict(X_scaled)[0]

        # Handle log transform if model was trained with it
        config = self.configs.get('batter_aav', {})
        if config.get('is_log_transformed', False):
            predicted_aav = np.exp(predicted_aav_raw) - 0.1  # Reverse log transform
        else:
            predicted_aav = predicted_aav_raw

        # Calculate prediction intervals (using quantile models if available)
        aav_metrics = self.metrics['batter_aav']
        mae = aav_metrics['mae']

        if 'batter_aav' in self.quantile_models:
            q_models = self.quantile_models['batter_aav']
            aav_low_raw = q_models['low'].predict(X_scaled)[0]
            aav_high_raw = q_models['high'].predict(X_scaled)[0]

            if config.get('is_log_transformed', False):
                predicted_aav_low = max(0.5, np.exp(aav_low_raw) - 0.1)
                predicted_aav_high = np.exp(aav_high_raw) - 0.1
            else:
                predicted_aav_low = max(0.5, aav_low_raw)
                predicted_aav_high = aav_high_raw
        else:
            # Fallback to MAE-based range
            predicted_aav_low = max(0.5, predicted_aav - mae)
            predicted_aav_high = predicted_aav + mae

        # Predict length (same features)
        length_features = self.features['batter_length']
        X_length = np.array([[feature_values.get(f, 0) for f in length_features]])
        X_length_scaled = self.scalers['batter_length'].transform(X_length)
        predicted_length = self.models['batter_length'].predict(X_length_scaled)[0]

        accuracy = aav_metrics['within_5m']

        # Get feature importance
        importance = dict(zip(features, self.models['batter_aav'].feature_importances_))
        top_features = dict(sorted(importance.items(), key=lambda x: -x[1])[:5])

        # Get comparables
        comparables = self._find_comparables(request, is_pitcher=False)

        return {
            'predicted_aav': predicted_aav,
            'predicted_aav_low': predicted_aav_low,
            'predicted_aav_high': predicted_aav_high,
            'predicted_length': max(1, round(predicted_length)),
            'confidence_score': min(MAX_CONFIDENCE_SCORE, accuracy),
            'feature_importance': top_features,
            'comparables': comparables,
            'model_accuracy': accuracy,
        }

    def _predict_pitcher(self, request: PredictionRequest, year: int) -> Dict:
        """Make prediction for a pitcher."""
        features = self.features['pitcher_aav']
        feature_values = {}

        # Core features (use defaults from utils for missing values)
        feature_values['age_at_signing'] = request.age
        feature_values['WAR_3yr'] = request.war_3yr
        feature_values['ERA_3yr'] = request.era_3yr or DEFAULT_PITCHER_STATS['era']
        feature_values['FIP_3yr'] = request.fip_3yr or DEFAULT_PITCHER_STATS['fip']
        k_9 = request.k_9_3yr or DEFAULT_PITCHER_STATS['k_9']
        bb_9 = request.bb_9_3yr or DEFAULT_PITCHER_STATS['bb_9']
        feature_values['K_9_3yr'] = k_9
        feature_values['BB_9_3yr'] = bb_9
        feature_values['IP_3yr'] = request.ip_3yr or DEFAULT_PITCHER_STATS['ip']
        feature_values['seasons_with_data'] = 3
        feature_values['is_starter'] = 1 if request.position.upper() == 'SP' else 0

        # Derived features
        feature_values['peak_efficiency'] = request.war_3yr / request.age if request.age > 0 else 0
        feature_values['control_metric'] = k_9 - bb_9

        # Pitcher Statcast features (use defaults for missing percentiles)
        feature_values['fb_velocity'] = request.fb_velocity or DEFAULT_PITCHER_STATS['fb_velocity']
        feature_values['fb_spin'] = request.fb_spin or DEFAULT_PITCHER_STATS['fb_spin']
        feature_values['xera'] = request.xera or DEFAULT_PITCHER_STATS['xera']
        feature_values['k_percent'] = request.k_percent or DEFAULT_PITCHER_STATS['k_percent']
        feature_values['bb_percent'] = request.bb_percent or DEFAULT_PITCHER_STATS['bb_percent']
        feature_values['whiff_percent_pitcher'] = request.whiff_percent_pitcher or DEFAULT_PITCHER_STATS['whiff_percent_pitcher']
        feature_values['chase_percent_pitcher'] = request.chase_percent_pitcher or DEFAULT_PITCHER_STATS['chase_percent_pitcher']

        # Has Statcast flag
        has_statcast = request.fb_velocity is not None or request.xera is not None
        feature_values['has_statcast'] = 1 if has_statcast else 0

        # Create feature array
        X = np.array([[feature_values.get(f, 0) for f in features]])

        # Scale and predict AAV
        X_scaled = self.scalers['pitcher_aav'].transform(X)
        predicted_aav_raw = self.models['pitcher_aav'].predict(X_scaled)[0]

        # Handle log transform if model was trained with it
        config = self.configs.get('pitcher_aav', {})
        if config.get('is_log_transformed', False):
            predicted_aav = np.exp(predicted_aav_raw) - 0.1  # Reverse log transform
        else:
            predicted_aav = predicted_aav_raw

        # Calculate prediction intervals
        aav_metrics = self.metrics['pitcher_aav']
        mae = aav_metrics['mae']

        if 'pitcher_aav' in self.quantile_models:
            q_models = self.quantile_models['pitcher_aav']
            aav_low_raw = q_models['low'].predict(X_scaled)[0]
            aav_high_raw = q_models['high'].predict(X_scaled)[0]

            if config.get('is_log_transformed', False):
                predicted_aav_low = max(0.5, np.exp(aav_low_raw) - 0.1)
                predicted_aav_high = np.exp(aav_high_raw) - 0.1
            else:
                predicted_aav_low = max(0.5, aav_low_raw)
                predicted_aav_high = aav_high_raw
        else:
            # Fallback to MAE-based range
            predicted_aav_low = max(0.5, predicted_aav - mae)
            predicted_aav_high = predicted_aav + mae

        # Predict length
        length_features = self.features['pitcher_length']
        X_length = np.array([[feature_values.get(f, 0) for f in length_features]])
        X_length_scaled = self.scalers['pitcher_length'].transform(X_length)
        predicted_length = self.models['pitcher_length'].predict(X_length_scaled)[0]

        accuracy = aav_metrics['within_5m']

        # Get feature importance
        importance = dict(zip(features, self.models['pitcher_aav'].feature_importances_))
        top_features = dict(sorted(importance.items(), key=lambda x: -x[1])[:5])

        # Get comparables
        comparables = self._find_comparables(request, is_pitcher=True)

        return {
            'predicted_aav': predicted_aav,
            'predicted_aav_low': predicted_aav_low,
            'predicted_aav_high': predicted_aav_high,
            'predicted_length': max(1, round(predicted_length)),
            'confidence_score': min(MAX_CONFIDENCE_SCORE, accuracy),
            'feature_importance': top_features,
            'comparables': comparables,
            'model_accuracy': accuracy,
        }

    def _find_comparables(self, request: PredictionRequest, is_pitcher: bool, n: int = 5) -> List[ComparablePlayer]:
        """Find comparable players based on similarity."""
        if self.contracts_df is None or len(self.contracts_df) == 0:
            return []

        # Filter to same player type (no copy needed - we filter into a new df)
        if is_pitcher:
            df = self.contracts_df[self.contracts_df['position'].isin(PITCHER_POSITIONS)]
        else:
            df = self.contracts_df[~self.contracts_df['position'].isin(PITCHER_POSITIONS)]

        if len(df) == 0:
            return []

        # Work on a filtered view - calculate similarity scores
        # Weight: 40% position, 35% WAR, 15% age, 10% recency
        current_year = get_current_year()
        pos_group = get_position_group(request.position)

        # Calculate similarity components
        pos_groups = df['position'].map(POSITION_GROUPS).fillna('OF')
        pos_match = (pos_groups == pos_group).astype(float) * 40

        # WAR similarity (35%)
        war_similarity = 0.0
        if 'WAR_3yr' in df.columns:
            war_diff = abs(df['WAR_3yr'] - request.war_3yr)
            max_war_diff = war_diff.max() if war_diff.max() > 0 else 1
            war_similarity = (1 - war_diff / max_war_diff) * 35

        # Age similarity (15%)
        age_diff = abs(df['age_at_signing'] - request.age)
        max_age_diff = age_diff.max() if age_diff.max() > 0 else 1
        age_similarity = (1 - age_diff / max_age_diff) * 15

        # Recency (10%)
        year_diff = current_year - df['year_signed']
        max_year_diff = year_diff.max() if year_diff.max() > 0 else 1
        recency_similarity = (1 - year_diff / max_year_diff) * 10

        # Combine into total similarity
        similarity = pos_match + war_similarity + age_similarity + recency_similarity

        # Get top n indices
        top_indices = similarity.nlargest(n).index
        top_df = df.loc[top_indices]
        top_similarity = similarity.loc[top_indices]

        comparables = []
        for idx, row in top_df.iterrows():
            age = int(row['age_at_signing'])
            length = int(row['length'])
            # Pre-FA extension: young player (<=25) with long contract (>=6 years)
            is_ext = age <= 25 and length >= 6

            comparables.append(ComparablePlayer(
                name=row['player_name'],
                position=row['position'],
                year_signed=int(row['year_signed']),
                age_at_signing=age,
                aav=row['AAV'],
                length=length,
                war_3yr=row.get('WAR_3yr', 0) or 0,
                similarity_score=round(top_similarity.loc[idx], 1),
                is_extension=is_ext,
            ))

        return comparables


# Singleton instance
prediction_service = PredictionService()
