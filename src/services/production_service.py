# src/services/production_service.py
"""Service layer for production business logic."""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import pandas as pd

from repositories.production_repository import ProductionRepository
# ml.serving.model_registry not available yet - will use placeholder
model_registry = None  # TODO: Import when ml/ is properly structured
from core.config import settings

logger = logging.getLogger(__name__)


class ProductionService:
    """Service for managing production business logic."""
    
    def __init__(self, repository: Optional[ProductionRepository] = None):
        """
        Initialize production service.
        
        Args:
            repository: Production repository instance
        """
        self.repository = repository or ProductionRepository()
    
    async def get_recent_production_data(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent production batches with quality predictions.
        
        Args:
            limit: Maximum number of batches to return
            
        Returns:
            List of production batch dictionaries
        """
        batches = self.repository.get_recent_batches(limit)
        
        # Enrich with ML predictions if model is available
        try:
            model = model_registry.get('quality_predictor')
            if model:
                for batch in batches:
                    if not batch.get('quality_score'):
                        score = await self._calculate_quality_score(batch, model)
                        batch['quality_score'] = score
        except Exception as e:
            logger.warning(f"Could not enrich with ML predictions: {e}")
        
        return batches
    
    async def get_quality_metrics(self) -> Dict[str, Any]:
        """
        Get current quality metrics with business logic applied.
        
        Returns:
            Dictionary with quality metrics
        """
        metrics = self.repository.get_quality_metrics()
        
        # Apply business rules
        if metrics['average'] < settings.QUALITY_THRESHOLD:
            metrics['alert'] = 'Quality below threshold!'
            metrics['recommendation'] = 'Review production parameters'
        
        # Add performance indicator
        if metrics['success_rate'] >= 95:
            metrics['performance'] = 'Excellent'
        elif metrics['success_rate'] >= 85:
            metrics['performance'] = 'Good'
        elif metrics['success_rate'] >= 70:
            metrics['performance'] = 'Acceptable'
        else:
            metrics['performance'] = 'Needs Improvement'
        
        return metrics
    
    async def create_production_batch(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new production batch with quality prediction.
        
        Args:
            batch_data: Dictionary with batch information
            
        Returns:
            Created batch with quality prediction
        """
        # Validate business rules
        if batch_data.get('temperature', 0) < 15 or batch_data.get('temperature', 0) > 35:
            raise ValueError("Temperature must be between 15 and 35°C")
        
        if batch_data.get('humidity', 0) < 30 or batch_data.get('humidity', 0) > 80:
            raise ValueError("Humidity must be between 30 and 80%")
        
        # Try to predict quality using ML model
        try:
            model = model_registry.get('quality_predictor')
            if model:
                # Prepare data for prediction
                input_data = pd.DataFrame([{
                    'temperature': batch_data.get('temperature', 25),
                    'humidity': batch_data.get('humidity', 60),
                    'roasting_time': batch_data.get('roasting_time', 20),
                    'cocoa_percentage': batch_data.get('cocoa_percentage', 70),
                    'bean_origin': batch_data.get('bean_origin', 'Unknown')
                }])
                
                # Get prediction
                predictions, confidence = model.predict_with_confidence(input_data)
                batch_data['quality'] = str(predictions[0])
                batch_data['quality_score'] = round(confidence[0] * 100, 1)
                batch_data['ml_predicted'] = True
                
                logger.info(f"ML prediction for new batch: {batch_data['quality']}")
        except Exception as e:
            logger.warning(f"Could not get ML prediction: {e}")
            # Fallback to rule-based quality assignment
            batch_data['quality'] = self._calculate_quality_grade(batch_data)
            batch_data['ml_predicted'] = False
        
        # Add to repository
        created_batch = self.repository.add_batch(batch_data)
        
        # Check if quality is below threshold
        if created_batch.get('quality_score', 100) < settings.QUALITY_THRESHOLD:
            logger.warning(f"Low quality batch created: {created_batch['batch']}")
            # Here you could trigger alerts or notifications
        
        return created_batch
    
    async def get_production_stats(self,
                                  start_date: Optional[datetime] = None,
                                  end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get production statistics with insights.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary with production statistics and insights
        """
        stats = self.repository.get_production_stats(start_date, end_date)
        
        # Add business insights
        if stats['total_batches'] > 0:
            if stats['average_quality'] >= 85:
                stats['quality_assessment'] = 'Excellent production quality'
            elif stats['average_quality'] >= 70:
                stats['quality_assessment'] = 'Good production quality'
            else:
                stats['quality_assessment'] = 'Quality needs improvement'
            
            # Add recommendations
            stats['recommendations'] = self._generate_recommendations(stats)
        
        return stats
    
    async def analyze_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Perform detailed analysis of a specific batch.
        
        Args:
            batch_id: Batch identifier
            
        Returns:
            Dictionary with batch analysis
        """
        batch = self.repository.get_batch_by_id(batch_id)
        
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        analysis = {
            'batch': batch,
            'quality_factors': self._analyze_quality_factors(batch),
            'recommendations': []
        }
        
        # Get ML insights if available
        try:
            model = model_registry.get('quality_predictor')
            if model:
                input_data = pd.DataFrame([batch])
                insights = model.get_quality_insights(input_data)
                analysis['ml_insights'] = insights
                if insights.get('recommendations'):
                    analysis['recommendations'].extend(insights['recommendations'])
        except Exception as e:
            logger.warning(f"Could not get ML insights: {e}")
        
        # Add rule-based recommendations
        if batch.get('temperature', 25) < 20:
            analysis['recommendations'].append("Consider increasing temperature to 20-25°C")
        if batch.get('humidity', 60) > 70:
            analysis['recommendations'].append("Reduce humidity below 70% for better quality")
        
        return analysis
    
    def _calculate_quality_grade(self, batch_data: Dict[str, Any]) -> str:
        """
        Calculate quality grade using rule-based logic.
        
        Args:
            batch_data: Batch information
            
        Returns:
            Quality grade string
        """
        score = 50  # Base score
        
        # Temperature scoring
        temp = batch_data.get('temperature', 25)
        if 22 <= temp <= 26:
            score += 20
        elif 20 <= temp <= 28:
            score += 10
        
        # Humidity scoring
        humidity = batch_data.get('humidity', 60)
        if 55 <= humidity <= 65:
            score += 20
        elif 50 <= humidity <= 70:
            score += 10
        
        # Cocoa percentage bonus
        cocoa = batch_data.get('cocoa_percentage', 70)
        if cocoa >= 75:
            score += 10
        
        # Determine grade
        if score >= 85:
            return 'Grade_A'
        elif score >= 70:
            return 'Grade_B'
        elif score >= 50:
            return 'Grade_C'
        else:
            return 'Grade_D'
    
    async def _calculate_quality_score(self, batch: Dict[str, Any], model) -> float:
        """
        Calculate quality score using ML model.
        
        Args:
            batch: Batch data
            model: ML model instance
            
        Returns:
            Quality score
        """
        try:
            input_data = pd.DataFrame([batch])
            _, confidence = model.predict_with_confidence(input_data)
            return round(confidence[0] * 100, 1)
        except Exception:
            return 75.0  # Default score
    
    def _analyze_quality_factors(self, batch: Dict[str, Any]) -> Dict[str, str]:
        """
        Analyze quality factors for a batch.
        
        Args:
            batch: Batch data
            
        Returns:
            Dictionary with factor analysis
        """
        factors = {}
        
        # Temperature analysis
        temp = batch.get('temperature', 25)
        if 22 <= temp <= 26:
            factors['temperature'] = 'Optimal'
        elif temp < 20:
            factors['temperature'] = 'Too low'
        elif temp > 30:
            factors['temperature'] = 'Too high'
        else:
            factors['temperature'] = 'Acceptable'
        
        # Humidity analysis
        humidity = batch.get('humidity', 60)
        if 55 <= humidity <= 65:
            factors['humidity'] = 'Optimal'
        elif humidity < 50:
            factors['humidity'] = 'Too low'
        elif humidity > 70:
            factors['humidity'] = 'Too high'
        else:
            factors['humidity'] = 'Acceptable'
        
        # Cocoa percentage analysis
        cocoa = batch.get('cocoa_percentage', 70)
        if cocoa >= 75:
            factors['cocoa'] = 'Premium'
        elif cocoa >= 60:
            factors['cocoa'] = 'Standard'
        else:
            factors['cocoa'] = 'Low'
        
        return factors
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on statistics.
        
        Args:
            stats: Production statistics
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if stats['average_quality'] < 70:
            recommendations.append("Review and optimize production parameters")
            recommendations.append("Consider additional quality control measures")
        
        if stats['average_quality'] < 85:
            recommendations.append("Monitor temperature and humidity more closely")
        
        if stats['total_batches'] < 5:
            recommendations.append("Increase production volume for better statistics")
        
        return recommendations