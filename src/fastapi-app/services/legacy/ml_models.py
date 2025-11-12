"""
ML Models Service - Chocolate Factory (Direct Implementation)
============================================================

Direct ML implementation using sklearn + pickle storage.
No external ML services (MLflow removed).
"""

import os
import pickle
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from domain.ml.feature_engineering import ChocolateFeatureEngine
from domain.machinery.specs import MACHINERY_SPECS, determine_active_process

logger = logging.getLogger(__name__)


@dataclass
class ModelTrainingResult:
    """Result of model training operation"""
    model_type: str
    model_path: str
    metrics: Dict[str, float]
    training_time_seconds: float
    feature_names: List[str]
    status: str
    error_message: Optional[str] = None


class ChocolateMLModels:
    """
    Direct ML Models for Chocolate Factory
    - Energy optimization prediction
    - Production recommendation classification
    - Direct sklearn + pickle storage
    """

    def __init__(self, models_dir: str = "/app/models"):
        self.models_dir = models_dir
        self.feature_engine = ChocolateFeatureEngine()

        # Ensure models directory exists
        os.makedirs(self.models_dir, exist_ok=True)

    async def train_energy_optimization_model(self,
                                            training_data: pd.DataFrame,
                                            experiment_name: str = "energy_optimization") -> ModelTrainingResult:
        """
        Train energy optimization model (Direct Implementation)
        """
        try:
            start_time = datetime.now()
            logger.info(f"🤖 Training energy optimization model with {len(training_data)} records")

            # Feature engineering
            features_df = await self.feature_engine.create_features(training_data)

            # Target variable (based on REAL machinery specs)
            if 'energy_optimization_score' not in features_df.columns:
                logger.info("Creating energy_optimization_score based on REAL machinery specs")

                # Use machine-specific features if available
                if 'machine_thermal_efficiency' in features_df.columns:
                    # IMPROVED TARGET: Based on real specs
                    # - Price normalized (0.05 = optimal, 0.35 = worst)
                    # - Machine thermal efficiency (0-100, from real optimal temps)
                    # - Machine humidity efficiency (0-100, from real optimal humidity)
                    # - Tariff multiplier (P3 valle bonus, P1 punta penalty)

                    features_df['price_normalized'] = (
                        (0.35 - features_df['price_eur_kwh']) / 0.30 * 100
                    ).clip(0, 100)

                    features_df['energy_optimization_score'] = (
                        features_df['price_normalized'] * 0.4 +           # 40% price
                        features_df['machine_thermal_efficiency'] * 0.35 + # 35% thermal
                        features_df['machine_humidity_efficiency'] * 0.15 + # 15% humidity
                        (features_df['tariff_multiplier'] - 1) * 50 + 50  # 10% tariff bonus/penalty
                    ).clip(0, 100)

                    logger.info("✅ Using REAL machinery specs for target calculation")
                else:
                    # FALLBACK: Old synthetic target (if machine features not available)
                    logger.warning("Machine features not available, using basic target")
                    features_df['energy_optimization_score'] = (
                        100 - (features_df['price_eur_kwh'] * 100) +
                        (features_df.get('chocolate_production_index', 50) * 0.3)
                    ).clip(0, 100)

            target = features_df['energy_optimization_score']
            feature_columns = [col for col in features_df.columns if col != 'energy_optimization_score']
            features = features_df[feature_columns]

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features, target, test_size=0.2, random_state=42
            )

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train model
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )

            model.fit(X_train_scaled, y_train)

            # Evaluate
            y_pred = model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            # Cross validation
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='r2')

            training_time = (datetime.now() - start_time).total_seconds()

            # Save model artifacts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            model_filename = f"energy_optimization_model_{timestamp}.pkl"
            scaler_filename = f"energy_optimization_scaler_{timestamp}.pkl"
            features_filename = f"energy_optimization_features_{timestamp}.pkl"

            model_path = os.path.join(self.models_dir, model_filename)
            scaler_path = os.path.join(self.models_dir, scaler_filename)
            features_path = os.path.join(self.models_dir, features_filename)

            # Save with pickle
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)

            with open(scaler_path, 'wb') as f:
                pickle.dump(scaler, f)

            with open(features_path, 'wb') as f:
                pickle.dump(feature_columns, f)

            # Update latest model symlinks
            latest_model_path = os.path.join(self.models_dir, "energy_optimization_model_latest.pkl")
            latest_scaler_path = os.path.join(self.models_dir, "energy_optimization_scaler_latest.pkl")
            latest_features_path = os.path.join(self.models_dir, "energy_optimization_features_latest.pkl")

            # Create or update symlinks
            for latest_path, current_path in [
                (latest_model_path, model_path),
                (latest_scaler_path, scaler_path),
                (latest_features_path, features_path)
            ]:
                if os.path.exists(latest_path):
                    os.remove(latest_path)
                os.symlink(os.path.basename(current_path), latest_path)

            metrics = {
                "mse": float(mse),
                "mae": float(mae),
                "r2_score": float(r2),
                "cv_mean": float(cv_scores.mean()),
                "cv_std": float(cv_scores.std()),
                "training_time_seconds": training_time,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "feature_count": len(feature_columns)
            }

            logger.info(f"✅ Energy model trained: R²={r2:.3f}, MAE={mae:.3f}")

            return ModelTrainingResult(
                model_type="energy_optimization",
                model_path=model_path,
                metrics=metrics,
                training_time_seconds=training_time,
                feature_names=feature_columns,
                status="success"
            )

        except Exception as e:
            logger.error(f"❌ Energy model training failed: {e}")
            return ModelTrainingResult(
                model_type="energy_optimization",
                model_path="",
                metrics={},
                training_time_seconds=0,
                feature_names=[],
                status="error",
                error_message=str(e)
            )

    async def train_production_recommendation_model(self,
                                                  training_data: pd.DataFrame,
                                                  experiment_name: str = "production_recommendation") -> ModelTrainingResult:
        """
        Train production recommendation model (Direct Implementation)
        """
        try:
            start_time = datetime.now()
            logger.info(f"🤖 Training production model with {len(training_data)} records")

            # Feature engineering
            features_df = await self.feature_engine.create_features(training_data)

            # Create production recommendations based on REAL machinery specs
            if 'production_recommendation' not in features_df.columns:
                logger.info("Creating production_recommendation based on REAL machinery specs")

                def get_production_recommendation_realistic(row):
                    """
                    Production recommendation based on:
                    - Real estimated cost (from machinery specs)
                    - Machine thermal efficiency (real optimal temps)
                    - Tariff period (P3 valle preferred)
                    """
                    # Use machine features if available
                    if 'estimated_cost_eur' in row and 'machine_thermal_efficiency' in row:
                        cost = row['estimated_cost_eur']
                        thermal_eff = row['machine_thermal_efficiency']
                        tariff_mult = row.get('tariff_multiplier', 1.0)

                        # Combined score (0-100)
                        cost_score = (20 - cost) / 20 * 100  # Lower cost = higher score
                        cost_score = max(0, min(100, cost_score))

                        combined_score = (
                            cost_score * 0.5 +        # 50% cost
                            thermal_eff * 0.3 +       # 30% thermal
                            (tariff_mult - 1) * -50 + 50  # 20% tariff (P3 bonus, P1 penalty)
                        )

                        # Classify based on combined score
                        if combined_score >= 75:
                            return "Optimal"
                        elif combined_score >= 50:
                            return "Moderate"
                        elif combined_score >= 25:
                            return "Reduced"
                        else:
                            return "Halt"
                    else:
                        # FALLBACK: Old basic thresholds
                        price = row.get('price_eur_kwh', 0.20)
                        choco_index = row.get('chocolate_production_index', 50)

                        if price < 0.15 and choco_index > 75:
                            return "Optimal"
                        elif price < 0.25 and choco_index > 50:
                            return "Moderate"
                        elif price < 0.35 and choco_index > 25:
                            return "Reduced"
                        else:
                            return "Halt"

                features_df['production_recommendation'] = features_df.apply(
                    get_production_recommendation_realistic, axis=1
                )

                # Log distribution
                dist = features_df['production_recommendation'].value_counts()
                logger.info(f"Production recommendation distribution: {dist.to_dict()}")

            target = features_df['production_recommendation']
            feature_columns = [col for col in features_df.columns if col != 'production_recommendation']
            features = features_df[feature_columns]

            # Encode target labels
            label_encoder = LabelEncoder()
            target_encoded = label_encoder.fit_transform(target)

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features, target_encoded, test_size=0.2, random_state=42, stratify=target_encoded
            )

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train model
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )

            model.fit(X_train_scaled, y_train)

            # Evaluate
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, average='weighted')
            recall = recall_score(y_test, y_pred, average='weighted')
            f1 = f1_score(y_test, y_pred, average='weighted')

            # Cross validation
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='accuracy')

            training_time = (datetime.now() - start_time).total_seconds()

            # Save model artifacts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            model_filename = f"production_recommendation_model_{timestamp}.pkl"
            scaler_filename = f"production_recommendation_scaler_{timestamp}.pkl"
            encoder_filename = f"production_recommendation_encoder_{timestamp}.pkl"
            features_filename = f"production_recommendation_features_{timestamp}.pkl"

            model_path = os.path.join(self.models_dir, model_filename)
            scaler_path = os.path.join(self.models_dir, scaler_filename)
            encoder_path = os.path.join(self.models_dir, encoder_filename)
            features_path = os.path.join(self.models_dir, features_filename)

            # Save with pickle
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)

            with open(scaler_path, 'wb') as f:
                pickle.dump(scaler, f)

            with open(encoder_path, 'wb') as f:
                pickle.dump(label_encoder, f)

            with open(features_path, 'wb') as f:
                pickle.dump(feature_columns, f)

            # Update latest model symlinks
            latest_model_path = os.path.join(self.models_dir, "production_recommendation_model_latest.pkl")
            latest_scaler_path = os.path.join(self.models_dir, "production_recommendation_scaler_latest.pkl")
            latest_encoder_path = os.path.join(self.models_dir, "production_recommendation_encoder_latest.pkl")
            latest_features_path = os.path.join(self.models_dir, "production_recommendation_features_latest.pkl")

            # Create or update symlinks
            for latest_path, current_path in [
                (latest_model_path, model_path),
                (latest_scaler_path, scaler_path),
                (latest_encoder_path, encoder_path),
                (latest_features_path, features_path)
            ]:
                if os.path.exists(latest_path):
                    os.remove(latest_path)
                os.symlink(os.path.basename(current_path), latest_path)

            metrics = {
                "accuracy": float(accuracy),
                "precision": float(precision),
                "recall": float(recall),
                "f1_score": float(f1),
                "cv_mean": float(cv_scores.mean()),
                "cv_std": float(cv_scores.std()),
                "training_time_seconds": training_time,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "feature_count": len(feature_columns),
                "classes": len(label_encoder.classes_)
            }

            logger.info(f"✅ Production model trained: Accuracy={accuracy:.3f}, F1={f1:.3f}")

            return ModelTrainingResult(
                model_type="production_recommendation",
                model_path=model_path,
                metrics=metrics,
                training_time_seconds=training_time,
                feature_names=feature_columns,
                status="success"
            )

        except Exception as e:
            logger.error(f"❌ Production model training failed: {e}")
            return ModelTrainingResult(
                model_type="production_recommendation",
                model_path="",
                metrics={},
                training_time_seconds=0,
                feature_names=[],
                status="error",
                error_message=str(e)
            )

    def load_latest_energy_model(self) -> Tuple[Any, Any, List[str]]:
        """Load latest energy optimization model"""
        try:
            model_path = os.path.join(self.models_dir, "energy_optimization_model_latest.pkl")
            scaler_path = os.path.join(self.models_dir, "energy_optimization_scaler_latest.pkl")
            features_path = os.path.join(self.models_dir, "energy_optimization_features_latest.pkl")

            with open(model_path, 'rb') as f:
                model = pickle.load(f)

            with open(scaler_path, 'rb') as f:
                scaler = pickle.load(f)

            with open(features_path, 'rb') as f:
                feature_names = pickle.load(f)

            return model, scaler, feature_names

        except Exception as e:
            logger.error(f"Failed to load energy model: {e}")
            raise

    def load_latest_production_model(self) -> Tuple[Any, Any, Any, List[str]]:
        """Load latest production recommendation model"""
        try:
            model_path = os.path.join(self.models_dir, "production_recommendation_model_latest.pkl")
            scaler_path = os.path.join(self.models_dir, "production_recommendation_scaler_latest.pkl")
            encoder_path = os.path.join(self.models_dir, "production_recommendation_encoder_latest.pkl")
            features_path = os.path.join(self.models_dir, "production_recommendation_features_latest.pkl")

            with open(model_path, 'rb') as f:
                model = pickle.load(f)

            with open(scaler_path, 'rb') as f:
                scaler = pickle.load(f)

            with open(encoder_path, 'rb') as f:
                label_encoder = pickle.load(f)

            with open(features_path, 'rb') as f:
                feature_names = pickle.load(f)

            return model, scaler, label_encoder, feature_names

        except Exception as e:
            logger.error(f"Failed to load production model: {e}")
            raise

    async def get_model_status(self) -> Dict[str, Any]:
        """Get status of trained models"""
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "models_directory": self.models_dir,
                "energy_optimization": {
                    "available": False,
                    "model_file": None,
                    "last_modified": None
                },
                "production_recommendation": {
                    "available": False,
                    "model_file": None,
                    "last_modified": None
                }
            }

            # Check energy model
            energy_model_path = os.path.join(self.models_dir, "energy_optimization_model_latest.pkl")
            if os.path.exists(energy_model_path):
                status["energy_optimization"]["available"] = True
                status["energy_optimization"]["model_file"] = energy_model_path
                status["energy_optimization"]["last_modified"] = datetime.fromtimestamp(
                    os.path.getmtime(energy_model_path)
                ).isoformat()

            # Check production model
            production_model_path = os.path.join(self.models_dir, "production_recommendation_model_latest.pkl")
            if os.path.exists(production_model_path):
                status["production_recommendation"]["available"] = True
                status["production_recommendation"]["model_file"] = production_model_path
                status["production_recommendation"]["last_modified"] = datetime.fromtimestamp(
                    os.path.getmtime(production_model_path)
                ).isoformat()

            return status

        except Exception as e:
            logger.error(f"Failed to get model status: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "models_directory": self.models_dir
            }


# Global instance
chocolate_ml_models = ChocolateMLModels()