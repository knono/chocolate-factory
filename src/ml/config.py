# src/ml/config.py
"""Machine Learning configuration for chocolate factory."""

ML_CONFIG = {
    'models': {
        'quality_predictor': {
            'version': '1.0.0',
            'features': [
                'temperature', 
                'humidity', 
                'roasting_time',
                'bean_origin_encoded',
                'cocoa_percentage'
            ],
            'model_type': 'RandomForestClassifier',
            'hyperparameters': {
                'n_estimators': 100,
                'max_depth': 10,
                'min_samples_split': 5,
                'min_samples_leaf': 2,
                'random_state': 42
            },
            'target_column': 'quality_grade'
        },
        'production_forecaster': {
            'version': '1.0.0',
            'features': [
                'historical_production',
                'season',
                'demand_forecast',
                'capacity'
            ],
            'model_type': 'GradientBoostingRegressor',
            'hyperparameters': {
                'n_estimators': 50,
                'learning_rate': 0.1,
                'max_depth': 5,
                'random_state': 42
            },
            'target_column': 'production_volume'
        }
    },
    'preprocessing': {
        'scaler_type': 'StandardScaler',
        'missing_value_strategy': 'mean',
        'outlier_detection_method': 'IQR',
        'categorical_encoding': 'label',
        'test_size': 0.2
    },
    'training': {
        'validation_strategy': 'cross_validation',
        'cv_folds': 5,
        'metrics': ['accuracy', 'precision', 'recall', 'f1'],
        'early_stopping': True,
        'max_iterations': 1000
    },
    'paths': {
        'models': 'models/',
        'data': 'src/ml/data/',
        'logs': 'logs/ml/',
        'features': 'src/ml/data/features/'
    },
    'quality_thresholds': {
        'Grade_A': {'min': 85, 'max': 100},
        'Grade_B': {'min': 70, 'max': 84},
        'Grade_C': {'min': 50, 'max': 69},
        'Grade_D': {'min': 0, 'max': 49}
    },
    'monitoring': {
        'log_predictions': True,
        'drift_detection': True,
        'performance_threshold': 0.8,
        'retraining_trigger': 'monthly'
    }
}