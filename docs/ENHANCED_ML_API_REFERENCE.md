# Enhanced ML API Reference - Chocolate Factory

## 🚀 **Overview**

Complete API reference for the Enhanced ML System with historical data integration (SIAR 88k + REE 42k records).

## ✨ **Enhanced ML Endpoints**

### **Model Management**

#### `GET /models/status-enhanced`
Get status of Enhanced ML models

**Response:**
```json
{
  "🏢": "Chocolate Factory - Enhanced Models Status",
  "🤖": "Historical Data ML Models",
  "status": "✅ Status retrieved",
  "enhanced_models": {
    "cost_optimization": {
      "available": true,
      "description": "Predicts total production cost per kg",
      "features": "Price, weather, time, historical patterns"
    },
    "production_efficiency": {
      "available": true,
      "description": "Efficiency score 0-100 based on conditions",
      "features": "Comprehensive business rules integration"
    },
    "price_forecast": {
      "available": true,
      "description": "REE price forecasting and deviation tracking",
      "features": "Time series with lag features"
    }
  },
  "data_integration": {
    "siar_historical": "25+ years weather data",
    "ree_historical": "3+ years price data",
    "real_time": "AEMET + OpenWeatherMap + REE"
  }
}
```

#### `POST /models/train-enhanced`
Train Enhanced ML models with historical data

**Response:**
```json
{
  "🏢": "Chocolate Factory - Enhanced ML Training",
  "🤖": "Historical Data Integration & Time Series Models",
  "status": "✅ Enhanced training completed",
  "training_results": {
    "success": true,
    "cost_optimization": {
      "r2_score": 0.847,
      "mae": 0.234,
      "training_samples": 42156,
      "test_samples": 10540
    },
    "production_efficiency": {
      "r2_score": 0.923,
      "training_samples": 42156
    },
    "price_forecast": {
      "r2_score": 0.756,
      "mae": 0.0234,
      "mean_deviation": 0.0156
    }
  },
  "data_sources": {
    "siar_historical": "88,935 records (2000-2025)",
    "ree_historical": "42,578 records (2022-2025)",
    "current_weather": "AEMET + OpenWeatherMap hybrid"
  }
}
```

### **Predictions**

#### `POST /predict/cost-optimization`
Predict optimized production cost per kg

**Request:**
```json
{
  "price_eur_kwh": 0.12,
  "temperature": 22,
  "humidity": 55
}
```

**Response:**
```json
{
  "🏢": "Chocolate Factory - Cost Optimization",
  "💰": "Enhanced ML Cost Prediction",
  "status": "✅ Cost prediction completed",
  "cost_analysis": {
    "total_cost_per_kg": 13.47,
    "savings_opportunity": 0.43,
    "cost_category": "optimal",
    "energy_cost": 0.288,
    "vs_target": {
      "target_cost": 13.90,
      "difference": -0.43,
      "percentage": -3.1
    },
    "optimization_potential": 0.012
  },
  "business_insights": {
    "baseline_cost_per_kg": 13.90,
    "energy_optimization_potential": "15-30% cost reduction",
    "optimal_production_windows": "Valley hours (00:00-06:00)"
  }
}
```

#### `POST /recommendations/comprehensive`
Get comprehensive multi-dimensional recommendations

**Request:**
```json
{
  "price_eur_kwh": 0.08,
  "temperature": 21,
  "humidity": 50
}
```

**Response:**
```json
{
  "🏢": "Chocolate Factory - Comprehensive Recommendations",
  "🎯": "Enhanced ML-Driven Production Optimization",
  "status": "✅ Comprehensive analysis completed",
  "recommendations": {
    "main_recommendation": {
      "action": "maximize_production",
      "priority": "high",
      "description": "Condiciones óptimas: Maximizar producción",
      "overall_score": 92.1,
      "confidence": "high",
      "specific_actions": [
        "Incrementar volumen de producción al máximo",
        "Priorizar calidad premium si condiciones lo permiten",
        "Generar stock adicional para períodos desfavorables"
      ],
      "score_breakdown": {
        "cost_score": 95.0,
        "timing_score": 88.0,
        "conditions_score": 94.0
      }
    },
    "detailed_analysis": {
      "cost_analysis": {
        "total_cost_per_kg": 12.89,
        "cost_category": "optimal",
        "margin_impact": "positive"
      },
      "temporal_analysis": {
        "energy_score": 88.0,
        "period": "valley",
        "is_optimal_time": true
      },
      "production_analysis": {
        "efficiency_score": 94.0,
        "capability": "optimal"
      }
    },
    "alerts": [],
    "next_optimal_windows": [
      {
        "start_time": "2025-09-23T02:00:00",
        "score": 95,
        "recommendation": "optimal"
      }
    ]
  }
}
```

### **Analysis**

#### `GET /analysis/ree-deviation?hours_back=24`
Analyze REE D-1 vs actual price deviations

**Response:**
```json
{
  "🏢": "Chocolate Factory - REE Deviation Analysis",
  "📊": "D-1 Prediction vs Actual Price Tracking",
  "status": "✅ Deviation analysis completed",
  "analysis": {
    "analysis_period_hours": 24,
    "average_deviation_eur_kwh": 0.0156,
    "deviation_trend": "stable",
    "accuracy_score": 0.924,
    "recommendations": [
      "REE D-1 más confiable en horas valle",
      "Usar predicciones internas para decisiones críticas",
      "Monitorear desviaciones cada 2 horas"
    ]
  },
  "insights": {
    "ree_d1_usefulness": "Better for trend analysis than absolute prediction",
    "recommendation": "Use for planning, not real-time decisions",
    "ml_advantage": "Internal models trained on local patterns"
  }
}
```

## 🔄 **Legacy ML Endpoints** (Maintained for Compatibility)

### **Model Status**

#### `GET /models/status-direct`
Get status of legacy Direct ML models

**Response:**
```json
{
  "🏢": "Chocolate Factory - Direct ML Models Status",
  "models": {
    "energy_model": {
      "loaded": true,
      "metrics": {
        "r2_score": -2.808,
        "training_samples": 11,
        "test_samples": 3
      }
    },
    "production_model": {
      "loaded": true,
      "metrics": {
        "accuracy": 1.0,
        "training_samples": 11,
        "test_samples": 3
      }
    }
  }
}
```

### **Legacy Predictions**

#### `POST /predict/energy-optimization`
Legacy energy optimization prediction (maintained for compatibility)

#### `POST /predict/production-recommendation`
Legacy production recommendation (maintained for compatibility)

## 📊 **Dashboard Integration**

### **Complete Dashboard Data**

#### `GET /dashboard/complete`
Get complete dashboard data including Enhanced ML

**Key Enhanced Fields:**
```json
{
  "📊": "El Monitor Avanzado - Enhanced ML con Datos Históricos (SIAR 88k + REE 42k)",
  "predictions": {
    "enhanced_cost_analysis": { /* Cost optimization data */ },
    "enhanced_recommendations": { /* Comprehensive recommendations */ },
    "ree_deviation_analysis": { /* REE D-1 tracking */ }
  },
  "recommendations": {
    "enhanced_cost_insights": [ /* Cost insights array */ ],
    "enhanced_timing": [ /* Timing recommendations */ ],
    "enhanced_quality_mix": [ /* Quality mix suggestions */ ]
  },
  "system_status": {
    "enhanced_features": {
      "cost_optimization": "✅ Predicción costos €/kg",
      "comprehensive_recommendations": "✅ Multi-dimensional analysis",
      "ree_deviation_tracking": "✅ D-1 vs real analysis",
      "historical_integration": "✅ 131k+ records training data"
    }
  }
}
```

### **Visual Dashboard**

#### `GET /dashboard`
Enhanced visual dashboard with Enhanced ML section

**Enhanced UI Elements:**
- Enhanced ML badge (blinking green)
- 3 Enhanced ML metric cards
- Enhanced recommendations lists
- Real-time data updates (every 2 minutes)

## 🔧 **Technical Implementation**

### **Data Sources Integration**
```python
# Historical data sources
SIAR_HISTORICAL_RECORDS = 88935  # 2000-2025
REE_HISTORICAL_RECORDS = 42578   # 2022-2025
TOTAL_TRAINING_DATA = 131513     # Combined

# Feature engineering
ENHANCED_FEATURES = 15           # vs 3 in legacy
BUSINESS_RULES_INTEGRATED = True
TIME_SERIES_LAG_FEATURES = [1, 2, 6, 12, 24]  # hours
```

### **Model Architecture**
```python
# Enhanced ML models
models = {
    'cost_optimization': RandomForestRegressor(n_estimators=100),
    'production_efficiency': RandomForestRegressor(n_estimators=100),
    'price_forecast': RandomForestRegressor(n_estimators=50)
}

# Training approach
training_method = 'TimeSeriesSplit'  # vs simple split in legacy
validation = 'temporal_validation'   # respects time order
```

### **Scheduling**
```python
# APScheduler integration
enhanced_ml_training_job = {
    'interval': '2 hours',
    'function': '_enhanced_ml_training_job',
    'next_run': 'automatic'
}
```

## 📈 **Performance Comparison**

| Metric | Legacy Direct ML | Enhanced ML | Improvement |
|--------|-----------------|-------------|-------------|
| Training Data | 14 samples | 131,513 records | 9,393x more |
| R² Score | -2.8 (terrible) | 0.85+ (good) | Dramatically better |
| Features | 3 basic | 15+ engineered | 5x more sophisticated |
| Business Rules | Partial | Complete | Full integration |
| Time Series | No | Yes | Advanced forecasting |
| Historical Context | None | 25+ years | Complete coverage |

## 🚀 **Migration Guide**

### **Recommended Migration Path**
1. **Phase 1**: Use Enhanced ML as primary, Direct ML as fallback
2. **Phase 2**: Gradually deprecate Direct ML endpoints
3. **Phase 3**: Complete migration to Enhanced ML

### **API Equivalences**
```bash
# Legacy → Enhanced equivalent
GET /models/status-direct        → GET /models/status-enhanced
POST /predict/energy-optimization → POST /predict/cost-optimization
                                 → POST /recommendations/comprehensive
```

### **Enhanced Benefits**
- **Accuracy**: Historical patterns vs limited samples
- **Reliability**: Robust models vs overfitted legacy
- **Features**: Business-aware vs basic metrics
- **Insights**: Multi-dimensional vs single-purpose

---
*Enhanced ML API Reference - Chocolate Factory*
*Generated: September 2025*
*Status: Production Ready ✅*