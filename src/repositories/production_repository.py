# src/repositories/production_repository.py
"""Repository for production data management."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import random
import logging

logger = logging.getLogger(__name__)


class ProductionRepository:
    """
    Repository for managing production data.
    Currently uses in-memory storage, can be easily switched to database.
    """
    
    def __init__(self):
        """Initialize repository with in-memory storage."""
        self._production_data = []
        self._quality_metrics = {
            "average": 85.0,
            "trend": "stable",
            "batches_processed": 0,
            "success_rate": 90.0
        }
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize with sample production data."""
        for i in range(10):
            self._production_data.append({
                "batch": f"BATCH{1000 + i}",
                "temperature": round(20 + random.uniform(-2, 2), 1),
                "humidity": round(60 + random.uniform(-5, 5), 1),
                "roasting_time": round(20 + random.uniform(-5, 5), 1),
                "cocoa_percentage": round(70 + random.uniform(-10, 20), 1),
                "quality": random.choice(["Grade_A", "Grade_B", "Grade_C"]),
                "quality_score": round(75 + random.uniform(-15, 20), 1),
                "timestamp": datetime.now() - timedelta(hours=i)
            })
        self._quality_metrics["batches_processed"] = len(self._production_data)
    
    def get_recent_batches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent production batches.
        
        Args:
            limit: Maximum number of batches to return
            
        Returns:
            List of production batch dictionaries
        """
        # Sort by timestamp descending and return limited results
        sorted_data = sorted(
            self._production_data, 
            key=lambda x: x['timestamp'], 
            reverse=True
        )
        return sorted_data[:limit]
    
    def get_batch_by_id(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific batch by ID.
        
        Args:
            batch_id: Batch identifier
            
        Returns:
            Batch dictionary or None if not found
        """
        for batch in self._production_data:
            if batch['batch'] == batch_id:
                return batch
        return None
    
    def add_batch(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new production batch.
        
        Args:
            batch_data: Dictionary with batch information
            
        Returns:
            Created batch dictionary
        """
        # Add timestamp if not present
        if 'timestamp' not in batch_data:
            batch_data['timestamp'] = datetime.now()
        
        # Generate batch ID if not present
        if 'batch' not in batch_data:
            last_batch_num = 1000 + len(self._production_data)
            batch_data['batch'] = f"BATCH{last_batch_num + 1}"
        
        self._production_data.append(batch_data)
        self._update_metrics()
        
        logger.info(f"Added new batch: {batch_data['batch']}")
        return batch_data
    
    def update_batch(self, batch_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing batch.
        
        Args:
            batch_id: Batch identifier
            update_data: Dictionary with fields to update
            
        Returns:
            Updated batch or None if not found
        """
        for i, batch in enumerate(self._production_data):
            if batch['batch'] == batch_id:
                self._production_data[i].update(update_data)
                self._update_metrics()
                logger.info(f"Updated batch: {batch_id}")
                return self._production_data[i]
        return None
    
    def delete_batch(self, batch_id: str) -> bool:
        """
        Delete a batch.
        
        Args:
            batch_id: Batch identifier
            
        Returns:
            True if deleted, False if not found
        """
        for i, batch in enumerate(self._production_data):
            if batch['batch'] == batch_id:
                del self._production_data[i]
                self._update_metrics()
                logger.info(f"Deleted batch: {batch_id}")
                return True
        return False
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """
        Get current quality metrics.
        
        Returns:
            Dictionary with quality metrics
        """
        # Simulate some variation in metrics
        self._quality_metrics['average'] = round(85 + random.uniform(-5, 5), 1)
        self._quality_metrics['trend'] = random.choice(["up", "down", "stable"])
        self._quality_metrics['success_rate'] = round(90 + random.uniform(-5, 5), 1)
        
        return self._quality_metrics.copy()
    
    def get_production_stats(self, 
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get production statistics for a date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary with production statistics
        """
        # Filter by date range if provided
        filtered_data = self._production_data
        
        if start_date:
            filtered_data = [
                b for b in filtered_data 
                if b['timestamp'] >= start_date
            ]
        
        if end_date:
            filtered_data = [
                b for b in filtered_data 
                if b['timestamp'] <= end_date
            ]
        
        if not filtered_data:
            return {
                'total_batches': 0,
                'average_quality': 0,
                'best_batch': None,
                'worst_batch': None
            }
        
        # Calculate statistics
        quality_scores = [
            b.get('quality_score', 75) 
            for b in filtered_data
        ]
        
        best_batch = max(
            filtered_data, 
            key=lambda x: x.get('quality_score', 0)
        )
        worst_batch = min(
            filtered_data, 
            key=lambda x: x.get('quality_score', 100)
        )
        
        return {
            'total_batches': len(filtered_data),
            'average_quality': round(sum(quality_scores) / len(quality_scores), 1),
            'best_batch': best_batch['batch'],
            'worst_batch': worst_batch['batch'],
            'period_start': start_date or min(b['timestamp'] for b in filtered_data),
            'period_end': end_date or max(b['timestamp'] for b in filtered_data)
        }
    
    def _update_metrics(self):
        """Update quality metrics based on current data."""
        if self._production_data:
            quality_scores = [
                b.get('quality_score', 75) 
                for b in self._production_data
            ]
            self._quality_metrics['average'] = round(
                sum(quality_scores) / len(quality_scores), 1
            )
            self._quality_metrics['batches_processed'] = len(self._production_data)
            
            # Determine trend based on recent batches
            recent = self._production_data[-5:]
            if len(recent) >= 2:
                recent_avg = sum(b.get('quality_score', 75) for b in recent[-3:]) / 3
                older_avg = sum(b.get('quality_score', 75) for b in recent[:2]) / 2
                
                if recent_avg > older_avg + 2:
                    self._quality_metrics['trend'] = 'up'
                elif recent_avg < older_avg - 2:
                    self._quality_metrics['trend'] = 'down'
                else:
                    self._quality_metrics['trend'] = 'stable'