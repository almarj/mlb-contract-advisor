"""
ML Prediction Service - Loads models and makes predictions.
"""
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import MODELS_DIR, MASTER_DATA_DIR
from app.models.schemas import PredictionRequest, ComparablePlayer


class PredictionService:
    """Service for loading ML models and making contract predictions."""

    PITCHER_POSITIONS = ['SP', 'RP', 'P', 'CL']

    POSITION_GROUPS = {
        'SP': 'SP', 'RP': 'RP', 'CL': 'RP', 'P': 'SP',
        'C': 'C', '1B': '1B', '2B': '2B', '3B': '3B', 'SS': 'SS',
        'LF': 'OF', 'CF': 'OF', 'RF': 'OF', 'OF': 'OF', 'DH': 'DH',
    }

    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.features = {}
        self.metrics = {}
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

                if model_path.exists():
                    self.models[model_type] = joblib.load(model_path)
                    self.scalers[model_type] = joblib.load(scaler_path)
                    self.features[model_type] = joblib.load(features_path)
                    self.metrics[model_type] = joblib.load(metrics_path)

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
            print(f"Error loading models: {e}")
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def is_pitcher(self, position: str) -> bool:
        """Check if position is a pitcher."""
        return position.upper() in self.PITCHER_POSITIONS

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

        is_pitcher = self.is_pitcher(request.position)
        current_year = 2026  # For year_signed feature

        if is_pitcher:
            return self._predict_pitcher(request, current_year)
        else:
            return self._predict_batter(request, current_year)

    def _predict_batter(self, request: PredictionRequest, year: int) -> Dict:
        """Make prediction for a batter."""
        # Get position group and create one-hot encoding
        pos_group = self.POSITION_GROUPS.get(request.position.upper(), 'OF')

        # Build feature vector matching training order
        features = self.features['batter_aav']
        feature_values = {}

        # Core features
        feature_values['age_at_signing'] = request.age
        feature_values['WAR_3yr'] = request.war_3yr
        feature_values['wRC_plus_3yr'] = request.wrc_plus_3yr or 100
        feature_values['AVG_3yr'] = request.avg_3yr or 0.250
        feature_values['OBP_3yr'] = request.obp_3yr or 0.320
        feature_values['SLG_3yr'] = request.slg_3yr or 0.400
        feature_values['HR_3yr'] = request.hr_3yr or 15
        feature_values['seasons_with_data'] = 3
        feature_values['year_signed'] = year

        # Statcast features
        feature_values['avg_exit_velo'] = request.avg_exit_velo or 88.5
        feature_values['barrel_rate'] = request.barrel_rate or 8.0
        feature_values['max_exit_velo'] = request.max_exit_velo or 110.0
        feature_values['hard_hit_pct'] = request.hard_hit_pct or 40.0
        feature_values['chase_rate'] = request.chase_rate or 50.0  # Percentile, 50 = average
        feature_values['whiff_rate'] = request.whiff_rate or 50.0  # Percentile, 50 = average

        # Position one-hot encoding
        for pos in ['1B', '2B', '3B', 'C', 'DH', 'OF', 'SS']:
            feature_values[f'pos_{pos}'] = 1 if pos_group == pos else 0

        # Create feature array in correct order
        X = np.array([[feature_values.get(f, 0) for f in features]])

        # Scale and predict AAV
        X_scaled = self.scalers['batter_aav'].transform(X)
        predicted_aav = self.models['batter_aav'].predict(X_scaled)[0]

        # Predict length (same features)
        length_features = self.features['batter_length']
        X_length = np.array([[feature_values.get(f, 0) for f in length_features]])
        X_length_scaled = self.scalers['batter_length'].transform(X_length)
        predicted_length = self.models['batter_length'].predict(X_length_scaled)[0]

        # Get metrics
        aav_metrics = self.metrics['batter_aav']
        mae = aav_metrics['mae']
        accuracy = aav_metrics['within_5m']

        # Get feature importance
        importance = dict(zip(features, self.models['batter_aav'].feature_importances_))
        top_features = dict(sorted(importance.items(), key=lambda x: -x[1])[:5])

        # Get comparables
        comparables = self._find_comparables(request, is_pitcher=False)

        return {
            'predicted_aav': predicted_aav,
            'predicted_aav_low': max(0.5, predicted_aav - mae),
            'predicted_aav_high': predicted_aav + mae,
            'predicted_length': max(1, round(predicted_length)),
            'confidence_score': min(95, accuracy),
            'feature_importance': top_features,
            'comparables': comparables,
            'model_accuracy': accuracy,
        }

    def _predict_pitcher(self, request: PredictionRequest, year: int) -> Dict:
        """Make prediction for a pitcher."""
        features = self.features['pitcher_aav']
        feature_values = {}

        # Core features
        feature_values['age_at_signing'] = request.age
        feature_values['WAR_3yr'] = request.war_3yr
        feature_values['ERA_3yr'] = request.era_3yr or 4.00
        feature_values['FIP_3yr'] = request.fip_3yr or 4.00
        feature_values['K_9_3yr'] = request.k_9_3yr or 8.0
        feature_values['BB_9_3yr'] = request.bb_9_3yr or 3.0
        feature_values['IP_3yr'] = request.ip_3yr or 150
        feature_values['seasons_with_data'] = 3
        feature_values['year_signed'] = year
        feature_values['is_starter'] = 1 if request.position.upper() == 'SP' else 0

        # Pitcher Statcast features (percentiles, 50 = average)
        feature_values['fb_velocity'] = request.fb_velocity or 50.0
        feature_values['fb_spin'] = request.fb_spin or 50.0
        feature_values['xera'] = request.xera or 50.0
        feature_values['k_percent'] = request.k_percent or 50.0
        feature_values['bb_percent'] = request.bb_percent or 50.0
        feature_values['whiff_percent_pitcher'] = request.whiff_percent_pitcher or 50.0
        feature_values['chase_percent_pitcher'] = request.chase_percent_pitcher or 50.0

        # Create feature array
        X = np.array([[feature_values.get(f, 0) for f in features]])

        # Scale and predict AAV
        X_scaled = self.scalers['pitcher_aav'].transform(X)
        predicted_aav = self.models['pitcher_aav'].predict(X_scaled)[0]

        # Predict length
        length_features = self.features['pitcher_length']
        X_length = np.array([[feature_values.get(f, 0) for f in length_features]])
        X_length_scaled = self.scalers['pitcher_length'].transform(X_length)
        predicted_length = self.models['pitcher_length'].predict(X_length_scaled)[0]

        # Get metrics
        aav_metrics = self.metrics['pitcher_aav']
        mae = aav_metrics['mae']
        accuracy = aav_metrics['within_5m']

        # Get feature importance
        importance = dict(zip(features, self.models['pitcher_aav'].feature_importances_))
        top_features = dict(sorted(importance.items(), key=lambda x: -x[1])[:5])

        # Get comparables
        comparables = self._find_comparables(request, is_pitcher=True)

        return {
            'predicted_aav': predicted_aav,
            'predicted_aav_low': max(0.5, predicted_aav - mae),
            'predicted_aav_high': predicted_aav + mae,
            'predicted_length': max(1, round(predicted_length)),
            'confidence_score': min(95, accuracy),
            'feature_importance': top_features,
            'comparables': comparables,
            'model_accuracy': accuracy,
        }

    def _find_comparables(self, request: PredictionRequest, is_pitcher: bool, n: int = 5) -> List[ComparablePlayer]:
        """Find comparable players based on similarity."""
        if self.contracts_df is None or len(self.contracts_df) == 0:
            return []

        df = self.contracts_df.copy()

        # Filter to same player type
        pitcher_positions = ['SP', 'RP', 'P', 'CL']
        if is_pitcher:
            df = df[df['position'].isin(pitcher_positions)]
        else:
            df = df[~df['position'].isin(pitcher_positions)]

        if len(df) == 0:
            return []

        # Calculate similarity scores
        # Weight: 40% position, 35% WAR, 15% age, 10% recency
        df['similarity'] = 0.0

        # Position similarity (40%)
        pos_group = self.POSITION_GROUPS.get(request.position.upper(), 'OF')
        df['pos_group'] = df['position'].map(self.POSITION_GROUPS).fillna('OF')
        df['similarity'] += (df['pos_group'] == pos_group).astype(float) * 40

        # WAR similarity (35%) - closer WAR = higher score
        if 'WAR_3yr' in df.columns:
            war_diff = abs(df['WAR_3yr'] - request.war_3yr)
            max_war_diff = war_diff.max() if war_diff.max() > 0 else 1
            df['similarity'] += (1 - war_diff / max_war_diff) * 35

        # Age similarity (15%)
        age_diff = abs(df['age_at_signing'] - request.age)
        max_age_diff = age_diff.max() if age_diff.max() > 0 else 1
        df['similarity'] += (1 - age_diff / max_age_diff) * 15

        # Recency (10%) - more recent = higher score
        year_diff = 2026 - df['year_signed']
        max_year_diff = year_diff.max() if year_diff.max() > 0 else 1
        df['similarity'] += (1 - year_diff / max_year_diff) * 10

        # Sort by similarity and take top n
        df = df.nlargest(n, 'similarity')

        comparables = []
        for _, row in df.iterrows():
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
                similarity_score=round(row['similarity'], 1),
                is_extension=is_ext,
            ))

        return comparables


# Singleton instance
prediction_service = PredictionService()
