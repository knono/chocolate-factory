"""
MLflow Client Service - Cuartel General ML
==========================================

Cliente para integración con MLflow tracking server para el 
TFM Chocolate Factory. Maneja modelos, experimentos y tracking.
"""

import os
import logging
from typing import Optional, Dict, Any, List
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from contextlib import asynccontextmanager
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class MLflowService:
    """Servicio para gestión de MLflow - Unidad MLOps"""
    
    def __init__(self):
        self.tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        self.client = None
        self._setup_mlflow()
    
    def _setup_mlflow(self):
        """Configurar conexión MLflow"""
        try:
            # Set environment variable first to prevent local file system access
            os.environ["MLFLOW_TRACKING_URI"] = self.tracking_uri
            
            # Configure MLflow with remote tracking URI
            mlflow.set_tracking_uri(self.tracking_uri)
            self.client = MlflowClient(tracking_uri=self.tracking_uri)
            
            logger.info(f"✅ MLflow configured with remote URI: {self.tracking_uri}")
        except Exception as e:
            logger.error(f"❌ Failed to setup MLflow: {e}")
            raise
    
    async def check_connectivity(self) -> Dict[str, Any]:
        """Verificar conectividad con MLflow"""
        try:
            # Test basic connectivity
            experiments = self.client.search_experiments()
            
            # Get MLflow version
            import mlflow
            mlflow_version = mlflow.__version__
            
            return {
                "status": "connected",
                "tracking_uri": self.tracking_uri,
                "mlflow_version": mlflow_version,
                "experiments_count": len(experiments),
                "default_experiment": mlflow.get_experiment_by_name("Default"),
                "connectivity_test": "✅ Success"
            }
        except Exception as e:
            logger.error(f"MLflow connectivity failed: {e}")
            return {
                "status": "failed",
                "tracking_uri": self.tracking_uri,
                "error": str(e),
                "connectivity_test": "❌ Failed"
            }
    
    async def get_or_create_experiment(self, experiment_name: str) -> str:
        """Obtener o crear experimento MLflow"""
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(experiment_name)
                logger.info(f"✅ Created new experiment: {experiment_name} (ID: {experiment_id})")
                return experiment_id
            else:
                logger.info(f"✅ Using existing experiment: {experiment_name} (ID: {experiment.experiment_id})")
                return experiment.experiment_id
        except Exception as e:
            logger.error(f"Failed to get/create experiment {experiment_name}: {e}")
            raise
    
    async def log_chocolate_metrics(self, 
                                  experiment_name: str,
                                  run_name: str,
                                  metrics: Dict[str, float],
                                  params: Dict[str, Any] = None,
                                  artifacts: Dict[str, str] = None) -> str:
        """Log métricas específicas para chocolate factory"""
        try:
            # Ensure tracking URI is set before any MLflow operations
            mlflow.set_tracking_uri(self.tracking_uri)
            os.environ["MLFLOW_TRACKING_URI"] = self.tracking_uri
            
            experiment_id = await self.get_or_create_experiment(experiment_name)
            
            with mlflow.start_run(experiment_id=experiment_id, run_name=run_name):
                # Log parameters
                if params:
                    for key, value in params.items():
                        mlflow.log_param(key, value)
                
                # Log metrics
                for key, value in metrics.items():
                    mlflow.log_metric(key, value)
                
                # Log artifacts as parameters instead of files to avoid file system issues
                if artifacts:
                    for artifact_name, content in artifacts.items():
                        mlflow.log_param(f"artifact_{artifact_name}", content)
                
                run_id = mlflow.active_run().info.run_id
                logger.info(f"✅ Logged run {run_name} in experiment {experiment_name}")
                return run_id
                
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")
            raise
    
    async def get_latest_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Obtener último modelo registrado"""
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()
            
            # Get latest version
            latest_versions = client.get_latest_versions(model_name, stages=["Production", "Staging"])
            if not latest_versions:
                latest_versions = client.get_latest_versions(model_name)
            
            if latest_versions:
                latest_version = latest_versions[0]
                return {
                    "name": latest_version.name,
                    "version": latest_version.version,
                    "stage": latest_version.current_stage,
                    "run_id": latest_version.run_id,
                    "creation_timestamp": latest_version.creation_timestamp
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to get latest model {model_name}: {e}")
            return None
    
    async def predict_with_model(self, 
                               model_name: str, 
                               input_data: pd.DataFrame) -> np.ndarray:
        """Realizar predicción con modelo MLflow"""
        try:
            # Load model from MLflow
            model_uri = f"models:/{model_name}/latest"
            model = mlflow.sklearn.load_model(model_uri)
            
            # Make prediction
            predictions = model.predict(input_data)
            logger.info(f"✅ Made predictions with model {model_name}")
            return predictions
            
        except Exception as e:
            logger.error(f"Failed to predict with model {model_name}: {e}")
            raise


@asynccontextmanager
async def get_mlflow_service():
    """Context manager para MLflow service"""
    service = MLflowService()
    try:
        yield service
    finally:
        # Cleanup if needed
        pass


# Instancia global para uso en FastAPI
mlflow_service = MLflowService()