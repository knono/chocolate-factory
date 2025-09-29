# src/ml/__init__.py
"""Machine Learning module for Chocolate Factory."""

from src.ml.serving.model_registry import model_registry
from src.ml.config import ML_CONFIG

__version__ = '1.0.0'

__all__ = [
    'model_registry',
    'ML_CONFIG'
]