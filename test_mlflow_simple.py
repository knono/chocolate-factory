#!/usr/bin/env python3
"""
Test simple MLflow artifact logging
"""

import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.datasets import make_regression
import tempfile
import os

# Set MLflow tracking URI
mlflow.set_tracking_uri("http://localhost:5000")

# Create simple test data
X, y = make_regression(n_samples=10, n_features=3, random_state=42)

# Train simple model
model = RandomForestRegressor(n_estimators=10, random_state=42)
model.fit(X, y)

# Start MLflow run and log model
experiment_name = "test_artifacts"
experiment = mlflow.get_experiment_by_name(experiment_name)
if experiment is None:
    experiment_id = mlflow.create_experiment(experiment_name)
else:
    experiment_id = experiment.experiment_id

print(f"Using experiment: {experiment_name} (ID: {experiment_id})")

with mlflow.start_run(experiment_id=experiment_id, run_name="simple_test"):
    # Log metrics
    mlflow.log_metric("test_score", 0.95)
    mlflow.log_param("n_estimators", 10)
    
    # Log model artifact
    mlflow.sklearn.log_model(
        sk_model=model,
        artifact_path="model"
    )
    
    # Log a simple text file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test artifact file")
        mlflow.log_artifact(f.name, "test_files")
    
    print("✅ MLflow artifacts logged successfully!")
    print(f"🔗 Run URL: http://localhost:5000/#/experiments/{experiment_id}")