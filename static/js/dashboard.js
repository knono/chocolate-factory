// Función para formato español (coma decimal)
function formatSpanishNumber(number, decimals = 2) {
    if (typeof number !== 'number' || isNaN(number)) return '--';
    return number.toFixed(decimals).replace('.', ',');
}

// Función para formato de coordenadas españolas
function formatSpanishCoordinate(number, decimals = 6) {
    if (typeof number !== 'number' || isNaN(number)) return '--';
    return number.toFixed(decimals).replace('.', ',');
}

// Función para renderizar el heatmap semanal
function renderHeatmap(weeklyForecast) {
    const calendarGrid = document.getElementById('calendar-grid');
    const optimalDaysElement = document.getElementById('optimal-days');
    const avgPriceElement = document.getElementById('avg-price');
    const priceRangeElement = document.getElementById('price-range');
    
    if (!weeklyForecast || !weeklyForecast.calendar_days) {
        calendarGrid.innerHTML = '<div style="text-align: center; grid-column: 1/-1; padding: 2rem;">❌ No hay datos del pronóstico semanal</div>';
        return;
    }
    
    // Limpiar grid
    calendarGrid.innerHTML = '';
    
    // Renderizar días
    weeklyForecast.calendar_days.forEach(day => {
        const dayElement = document.createElement('div');
        dayElement.className = `calendar-day ${day.is_today ? 'today' : ''}`;
        
        // CSS variables para colores dinámicos
        dayElement.style.setProperty('--day-bg', day.heat_color + '20');
        dayElement.style.setProperty('--day-border', day.heat_color);
        
        dayElement.innerHTML = `
            <div class="day-name">${day.day_short}</div>
            <div class="day-number">${day.day_number}</div>
            <div class="day-price">${formatSpanishNumber(day.avg_price_eur_kwh, 3)} €</div>
            <div class="day-recommendation">${day.recommendation_icon}</div>
        `;
        
        // Tooltip compatible con Safari/Brave usando data-attribute
        dayElement.setAttribute('data-tooltip', `${day.day_name} ${day.day_number}\\nPrecio: ${formatSpanishNumber(day.avg_price_eur_kwh, 3)} €/kWh\\nTemperatura: ${day.avg_temperature}°C\\nHumedad: ${day.avg_humidity}%\\nRecomendación: ${day.production_recommendation}`);

        // Fallback: title nativo para navegadores que lo soporten
        dayElement.title = `${day.day_name} ${day.day_number}
Precio: ${formatSpanishNumber(day.avg_price_eur_kwh, 3)} €/kWh
Temperatura: ${day.avg_temperature}°C
Humedad: ${day.avg_humidity}%
Recomendación: ${day.production_recommendation}`;

        calendarGrid.appendChild(dayElement);
    });
    
    // Actualizar resumen
    const summary = weeklyForecast.summary;
    if (summary) {
        optimalDaysElement.textContent = summary.optimal_days || 0;
        avgPriceElement.textContent = formatSpanishNumber(summary.price_summary?.avg_price || 0, 3) + ' €/kWh';
        const minPrice = formatSpanishNumber(summary.price_summary?.min_price || 0, 2);
        const maxPrice = formatSpanishNumber(summary.price_summary?.max_price || 0, 2);
        priceRangeElement.textContent = `${minPrice} - ${maxPrice} €/kWh`;
    }
}

function renderHistoricalAnalytics(data) {
    const analytics = data.historical_analytics;
    if (!analytics) return;
    
    // Métricas principales
    const totalConsumptionEl = document.getElementById('total-consumption');
    const avgDailyCostEl = document.getElementById('avg-daily-cost');
    const peakConsumptionEl = document.getElementById('peak-consumption');
    const totalCostEl = document.getElementById('total-cost');
    
    if (totalConsumptionEl) totalConsumptionEl.textContent = formatSpanishNumber(analytics.factory_metrics.total_kwh, 0) + ' kWh';
    if (avgDailyCostEl) avgDailyCostEl.textContent = formatSpanishNumber(analytics.factory_metrics.avg_daily_cost, 2) + ' €';
    if (peakConsumptionEl) peakConsumptionEl.textContent = formatSpanishNumber(analytics.factory_metrics.peak_consumption, 0) + ' kW';
    if (totalCostEl) totalCostEl.textContent = formatSpanishNumber(analytics.factory_metrics.total_cost, 2) + ' €';
    
    // Análisis de precios
    const minPriceEl = document.getElementById('min-price');
    const maxPriceEl = document.getElementById('max-price');
    const avgPriceEl = document.getElementById('avg-price');
    const volatilityEl = document.getElementById('price-volatility');
    
    if (minPriceEl) minPriceEl.textContent = formatSpanishNumber(analytics.price_analysis.min_price_eur_kwh, 4) + ' €/kWh';
    if (maxPriceEl) maxPriceEl.textContent = formatSpanishNumber(analytics.price_analysis.max_price_eur_kwh, 4) + ' €/kWh';
    if (avgPriceEl) avgPriceEl.textContent = formatSpanishNumber(analytics.price_analysis.avg_price_eur_kwh, 4) + ' €/kWh';
    if (volatilityEl) volatilityEl.textContent = formatSpanishNumber(analytics.price_analysis.volatility_coefficient, 2);
    
    // Potencial de optimización
    const savingsPotentialEl = document.getElementById('savings-potential');
    const optimalHoursEl = document.getElementById('optimal-hours');
    const annualProjectionEl = document.getElementById('annual-projection');
    
    if (savingsPotentialEl) savingsPotentialEl.textContent = formatSpanishNumber(analytics.optimization_potential.total_savings_eur, 0) + ' €';
    if (optimalHoursEl) optimalHoursEl.textContent = analytics.optimization_potential.optimal_production_hours;
    if (annualProjectionEl) annualProjectionEl.textContent = formatSpanishNumber(analytics.optimization_potential.annual_savings_projection, 0) + ' €';
    
    // Recomendaciones
    const recommendationsContainer = document.getElementById('optimization-recommendations');
    if (recommendationsContainer && analytics.recommendations) {
        recommendationsContainer.innerHTML = analytics.recommendations
            .map(rec => `<div class="recommendation-item">• ${rec}</div>`)
            .join('');
    }
}

function renderSmartInsights(data) {
    const analytics = data.historical_analytics;
    const currentEnergy = data.current_info?.energy;
    
    if (!analytics || !currentEnergy) return;
    
    const currentPrice = currentEnergy.price_eur_kwh;
    const avgPrice = analytics.price_analysis.avg_price_eur_kwh;
    const minPrice = analytics.price_analysis.min_price_eur_kwh;
    const maxPrice = analytics.price_analysis.max_price_eur_kwh;
    
    // Calcular percentil del precio actual
    const priceRange = maxPrice - minPrice;
    const pricePosition = (currentPrice - minPrice) / priceRange;
    
    // Actualizar estado energético actual
    const statusIconEl = document.querySelector('.status-icon');
    const statusTextEl = document.getElementById('energy-status-text');
    const priceAnalysisEl = document.getElementById('current-price-analysis');
    const actionRecommendationEl = document.getElementById('energy-action-recommendation');
    
    if (pricePosition <= 0.25) {
        // Precio muy bajo (25% inferior)
        if (statusIconEl) statusIconEl.textContent = '🟢';
        if (statusTextEl) statusTextEl.textContent = 'ÓPTIMO - Precio Muy Bajo';
        if (actionRecommendationEl) actionRecommendationEl.textContent = '🚀 Momento ideal para maximizar producción';
    } else if (pricePosition <= 0.5) {
        // Precio bajo-medio (25-50%)
        if (statusIconEl) statusIconEl.textContent = '🟡';
        if (statusTextEl) statusTextEl.textContent = 'FAVORABLE - Precio Bajo';
        if (actionRecommendationEl) actionRecommendationEl.textContent = '✅ Condiciones buenas para producir';
    } else if (pricePosition <= 0.75) {
        // Precio medio-alto (50-75%)
        if (statusIconEl) statusIconEl.textContent = '🟠';
        if (statusTextEl) statusTextEl.textContent = 'NEUTRO - Precio Medio';
        if (actionRecommendationEl) actionRecommendationEl.textContent = '⚖️ Evaluar necesidad vs costo';
    } else {
        // Precio alto (75%+)
        if (statusIconEl) statusIconEl.textContent = '🔴';
        if (statusTextEl) statusTextEl.textContent = 'CARO - Precio Alto';
        if (actionRecommendationEl) actionRecommendationEl.textContent = '⚠️ Considerar diferir producción';
    }
    
    if (priceAnalysisEl) priceAnalysisEl.textContent = formatSpanishNumber(currentPrice, 4) + ' €/kWh';
    
    // Calcular ahorro vs precio promedio
    const hourlyConsumption = 104; // kW promedio de la fábrica
    const savingsPerHour = (avgPrice - currentPrice) * hourlyConsumption;
    const savingsPotentialEl = document.getElementById('current-savings-potential');
    if (savingsPotentialEl) {
        if (savingsPerHour > 0) {
            savingsPotentialEl.textContent = '+' + formatSpanishNumber(savingsPerHour, 2) + ' €/hora';
            savingsPotentialEl.style.color = '#4CAF50';
        } else {
            savingsPotentialEl.textContent = formatSpanishNumber(savingsPerHour, 2) + ' €/hora';
            savingsPotentialEl.style.color = '#F44336';
        }
    }
    
    // Ranking diario simulado (basado en percentil)
    const rankingEl = document.getElementById('price-ranking');
    const ranking = Math.ceil(pricePosition * 24);
    if (rankingEl) rankingEl.textContent = ranking + '/24';
    
    // Acción de ahorro
    const savingsActionEl = document.getElementById('savings-action');
    if (savingsActionEl) {
        if (savingsPerHour > 5) {
            savingsActionEl.textContent = '💰 Excelente momento para ahorrar';
        } else if (savingsPerHour > 0) {
            savingsActionEl.textContent = '💡 Ahorro moderado disponible';
        } else if (savingsPerHour > -5) {
            savingsActionEl.textContent = '⚖️ Costo ligeramente superior';
        } else {
            savingsActionEl.textContent = '⚠️ Momento costoso para producir';
        }
    }
    
    // Análisis por procesos de fábrica
    const processes = {
        'Conchado': 48,    // kW - Proceso más intensivo
        'Rolado': 42,      // kW - Refinado del chocolate
        'Templado': 36,    // kW - Control de temperatura
        'Mezcla': 30       // kW - Proceso básico
    };
    
    // Calcular costo por proceso en el precio actual
    const processCosts = Object.entries(processes).map(([name, kw]) => ({
        name,
        kw,
        costPerHour: currentPrice * kw,
        savingsVsAvg: (avgPrice - currentPrice) * kw
    }));
    
    // Recomendar proceso basado en precio actual
    const recommendedProcessEl = document.getElementById('recommended-process');
    const processCostEl = document.getElementById('process-cost');
    const processActionEl = document.getElementById('process-action');
    
    if (pricePosition <= 0.25) {
        // Precio muy bajo - recomendar proceso más intensivo
        const bestProcess = processCosts[0]; // Conchado (48kW)
        if (recommendedProcessEl) recommendedProcessEl.textContent = '🍫 Conchado';
        if (processCostEl) processCostEl.textContent = formatSpanishNumber(bestProcess.costPerHour, 2) + ' €/h';
        if (processActionEl) processActionEl.textContent = `🚀 Momento óptimo para procesos intensivos (+${formatSpanishNumber(bestProcess.savingsVsAvg, 2)}€/h vs promedio)`;
    } else if (pricePosition <= 0.4) {
        // Precio bajo-medio - recomendar proceso intermedio
        const goodProcess = processCosts[1]; // Rolado (42kW)
        if (recommendedProcessEl) recommendedProcessEl.textContent = '🔄 Rolado';
        if (processCostEl) processCostEl.textContent = formatSpanishNumber(goodProcess.costPerHour, 2) + ' €/h';
        if (processActionEl) processActionEl.textContent = `✅ Condiciones favorables para refinado (+${formatSpanishNumber(goodProcess.savingsVsAvg, 2)}€/h)`;
    } else if (pricePosition <= 0.6) {
        // Precio medio - recomendar proceso estándar
        const stdProcess = processCosts[2]; // Templado (36kW)
        if (recommendedProcessEl) recommendedProcessEl.textContent = '🌡️ Templado';
        if (processCostEl) processCostEl.textContent = formatSpanishNumber(stdProcess.costPerHour, 2) + ' €/h';
        if (processActionEl) processActionEl.textContent = `⚖️ Proceso estándar recomendado (${formatSpanishNumber(Math.abs(stdProcess.savingsVsAvg), 2)}€/h vs promedio)`;
    } else {
        // Precio alto - recomendar proceso de menor consumo
        const lowProcess = processCosts[3]; // Mezcla (30kW)
        if (recommendedProcessEl) recommendedProcessEl.textContent = '🥄 Mezcla';
        if (processCostEl) processCostEl.textContent = formatSpanishNumber(lowProcess.costPerHour, 2) + ' €/h';
        if (processActionEl) processActionEl.textContent = `⚠️ Solo procesos básicos recomendados (sobrecosto: +${formatSpanishNumber(Math.abs(lowProcess.savingsVsAvg), 2)}€/h)`;
    }
    
    // Recomendación principal inteligente
    const recIconEl = document.getElementById('recommendation-icon');
    const recTitleEl = document.getElementById('recommendation-title');
    const recDetailEl = document.getElementById('recommendation-detail');
    
    if (pricePosition <= 0.25) {
        if (recIconEl) recIconEl.textContent = '🚀';
        if (recTitleEl) recTitleEl.textContent = 'PRODUCIR AHORA - Oportunidad Excepcional';
        if (recDetailEl) recDetailEl.textContent = `🍫 CONCHADO RECOMENDADO: Precio actual (${formatSpanishNumber(currentPrice, 4)} €/kWh) en el 25% más bajo del histórico. Momento óptimo para procesos intensivos (48kW). Ahorro vs promedio: ${formatSpanishNumber((avgPrice - currentPrice) * 48, 2)} €/hora en Conchado.`;
    } else if (pricePosition <= 0.4) {
        if (recIconEl) recIconEl.textContent = '✅';
        if (recTitleEl) recTitleEl.textContent = 'PRODUCIR - Rolado Recomendado';
        if (recDetailEl) recDetailEl.textContent = `🔄 ROLADO FAVORABLE: Condiciones buenas para refinado (42kW). Costo actual: ${formatSpanishNumber(currentPrice * 42, 2)} €/hora. Ahorro vs promedio: +${formatSpanishNumber((avgPrice - currentPrice) * 42, 2)} €/hora.`;
    } else if (pricePosition <= 0.6) {
        if (recIconEl) recIconEl.textContent = '⚖️';
        if (recTitleEl) recTitleEl.textContent = 'EVALUAR - Templado Estándar';
        if (recDetailEl) recDetailEl.textContent = `🌡️ TEMPLADO RECOMENDADO: Precio medio, ideal para procesos estándar (36kW). Costo: ${formatSpanishNumber(currentPrice * 36, 2)} €/hora. Evaluar urgencia vs esperar mejores condiciones para procesos intensivos.`;
    } else if (pricePosition <= 0.8) {
        if (recIconEl) recIconEl.textContent = '⚠️';
        if (recTitleEl) recTitleEl.textContent = 'DIFERIR - Solo Procesos Básicos';
        if (recDetailEl) recDetailEl.textContent = `🥄 SOLO MEZCLA: Precio elevado, limitarse a procesos básicos (30kW). Costo Mezcla: ${formatSpanishNumber(currentPrice * 30, 2)} €/hora. Diferir Conchado y Rolado hasta mejores condiciones.`;
    } else {
        if (recIconEl) recIconEl.textContent = '🛑';
        if (recTitleEl) recTitleEl.textContent = 'SUSPENDER - Precio Crítico';
        if (recDetailEl) recDetailEl.textContent = `⚠️ ALERTA CRÍTICA: Precio en máximos históricos (${formatSpanishNumber(currentPrice, 4)} €/kWh). Incluso Mezcla cuesta ${formatSpanishNumber(currentPrice * 30, 2)} €/h. Suspender toda producción no crítica hasta mejores condiciones.`;
    }
}

async function loadData() {
    try {
        document.getElementById('status').textContent = '🔄 Cargando...';
        document.getElementById('status').className = 'status-badge status-warning';
        
        const response = await fetch('/dashboard/complete');
        const data = await response.json();
        
        // Estado conexión
        document.getElementById('status').textContent = '✅ Conectado';
        document.getElementById('status').className = 'status-badge status-connected';
        document.getElementById('last-update').textContent = new Date(data.timestamp).toLocaleTimeString();
        
        // Energía (formato español)
        const energy = data.current_info.energy || {};
        document.getElementById('energy-price').textContent = formatSpanishNumber(energy.price_eur_kwh || 0, 4);
        document.getElementById('energy-mwh').textContent = formatSpanishNumber(energy.price_eur_mwh || 0, 2) + ' €/MWh';
        document.getElementById('energy-datetime').textContent = new Date(energy.datetime).toLocaleString();
        
        const trendElement = document.getElementById('energy-trend');
        trendElement.textContent = '📈 ' + (energy.trend || 'stable');
        trendElement.className = `metric-trend trend-${energy.trend || 'stable'}`;
        
        // Clima (formato español)
        const weather = data.current_info.weather || {};
        document.getElementById('temperature').textContent = formatSpanishNumber(weather.temperature || 0, 1);
        document.getElementById('humidity').textContent = formatSpanishNumber(weather.humidity || 0, 0) + '%';
        document.getElementById('pressure').textContent = formatSpanishNumber(weather.pressure || 0, 0) + ' hPa';
        document.getElementById('comfort-index').textContent = weather.comfort_index || '--';
        
        // Producción (formato español)
        document.getElementById('production-status').textContent = data.current_info.production_status || '--';
        document.getElementById('factory-efficiency').textContent = formatSpanishNumber(data.current_info.factory_efficiency || 0, 1) + '%';
        
        
        // Estado sistema
        const systemStatus = data.system_status || {};
        const sources = systemStatus.data_sources || {};
        
        const reeStatusEl = document.getElementById('ree-status');
        const weatherStatusEl = document.getElementById('weather-status');
        const mlModelsStatusEl = document.getElementById('ml-models-status');
        
        if (reeStatusEl) reeStatusEl.textContent = sources.ree || '--';
        if (weatherStatusEl) weatherStatusEl.textContent = sources.weather || '--';
        if (mlModelsStatusEl) mlModelsStatusEl.textContent = sources.ml_models || '--';
        
        // Renderizar heatmap semanal
        if (data.weekly_forecast) {
            renderHeatmap(data.weekly_forecast);
        }

        // ✨ Enhanced ML data rendering removed (card deprecated in v0.42.0)
        // renderEnhancedMLData(data);

        // 🔄 Renderizar REE Unificado (reemplaza analytics históricos + smart insights)
        renderUnifiedREEAnalysis(data);

        // 📊 Renderizar SIAR Historical Analysis (Sprint 07)
        renderSIARAnalysis(data);

        // 🎯 Cargar Plan Optimizado 24h (Sprint 08)
        loadOptimizationPlan();

    } catch (error) {
        document.getElementById('status').textContent = '❌ Error de conexión';
        document.getElementById('status').className = 'status-badge';
        console.error('Dashboard error:', error);
    }
}

// ⚡ Función Unificada REE con BusinessLogicService
function renderUnifiedREEAnalysis(data) {
    try {
        const analytics = data.historical_analytics;
        const currentEnergy = data.current_info?.energy;
        const recommendations = data.recommendations || {};
        const humanRecUnified = recommendations.human_recommendation;

        if (!analytics || !currentEnergy) {
            console.log('⚠️ Missing data for unified REE analysis');
            return;
        }

        // === RECOMENDACIÓN HUMANIZADA PRINCIPAL ===
        if (humanRecUnified && !humanRecUnified.error) {
            const unifiedSection = document.getElementById('unified-human-recommendation-section');
            const unifiedContent = document.getElementById('unified-human-recommendation-content');

            if (unifiedSection && unifiedContent) {
                const message = humanRecUnified.main_message || {};
                const economicImpact = humanRecUnified.economic_impact || {};
                const metadata = humanRecUnified.metadata || {};

                let content = `
                    <div style="margin-bottom: 1rem;">
                        <h3 style="margin: 0; font-size: 1.3rem; color: white;">${message.title || 'RECOMENDACIÓN INTELIGENTE'}</h3>
                        <div style="margin-top: 0.5rem; opacity: 0.95; font-size: 1rem;">
                            <strong>📊 Análisis:</strong> ${message.situation || 'Evaluando condiciones actuales...'}
                        </div>
                    </div>

                    <div class="grid grid-2" style="gap: 1rem; margin-bottom: 1rem;">
                        <div>
                            <strong style="display: block; margin-bottom: 0.5rem;">🎯 Acciones:</strong>
                            <ul style="margin: 0; padding-left: 1rem; font-size: 0.95rem;">
                `;

                if (message.priority_actions && Array.isArray(message.priority_actions)) {
                    message.priority_actions.slice(0, 3).forEach(action => {
                        content += `<li>${action}</li>`;
                    });
                }

                content += `
                            </ul>
                        </div>
                        <div>
                            <strong style="display: block; margin-bottom: 0.5rem;">💰 Impacto:</strong>
                            <div style="font-size: 0.95rem; line-height: 1.4;">
                                <div><strong>Costo/kg:</strong> ${economicImpact.current_cost_per_kg || '13,90'}€</div>
                                <div><strong>Categoría:</strong> ${economicImpact.cost_category || 'normal'}</div>
                                <div><strong>Confianza:</strong> ${message.confidence_level || metadata.confidence || 'media'}</div>
                            </div>
                        </div>
                    </div>
                `;

                unifiedContent.innerHTML = content;
                unifiedSection.style.display = 'block';
            }
        }

        // === MÉTRICAS DE LA TARJETA UNIFICADA ===

        // Current energy status
        const currentPrice = currentEnergy.price_eur_kwh;
        const statusTextEl = document.getElementById('energy-status-text');
        const statusDetailEl = document.getElementById('energy-status-detail');
        const actionRecommendationEl = document.getElementById('energy-action-recommendation');

        if (statusTextEl && statusDetailEl && actionRecommendationEl) {
            // === USE SAME LOGIC AS ENHANCED ML ANALYTICS ===
            if (humanRecUnified && humanRecUnified.recommendation_level) {
                const level = humanRecUnified.recommendation_level;
                const levelNames = {
                    'maximize': 'Óptimo',
                    'standard': 'Normal',
                    'reduced': 'Subóptimo',
                    'minimal': 'Crítico',
                    'critical': 'Emergencia'
                };
                statusTextEl.textContent = levelNames[level] || 'Evaluando';

                // Use humanized recommendation level instead of raw Enhanced ML action
                const levelToAction = {
                    'maximize': 'Maximize Production',
                    'standard': 'Standard Production',
                    'reduced': 'Reduce Production',
                    'minimal': 'Minimal Production',
                    'critical': 'Emergency Procedures'
                };
                const actionDisplay = levelToAction[level] || 'Standard Production';
                actionRecommendationEl.textContent = actionDisplay;
            } else {
                // Fallback to price-based logic only if no human recommendation
                if (currentPrice < 0.12) {
                    statusTextEl.textContent = 'Óptimo';
                    actionRecommendationEl.textContent = 'Standard Production';
                } else if (currentPrice < 0.20) {
                    statusTextEl.textContent = 'Normal';
                    actionRecommendationEl.textContent = 'Standard Production';
                } else if (currentPrice < 0.30) {
                    statusTextEl.textContent = 'Alto';
                    actionRecommendationEl.textContent = 'Reduce Production';
                } else {
                    statusTextEl.textContent = 'Crítico';
                    actionRecommendationEl.textContent = 'Halt Production';
                }
            }

            statusDetailEl.textContent = formatSpanishNumber(currentPrice, 4) + ' €/kWh';
        }

        // Historical metrics
        if (analytics.price_analysis) {
            const priceAnalysis = analytics.price_analysis;
            document.getElementById('avg-price').textContent = formatSpanishNumber(priceAnalysis.average_price || 0, 4) + ' €/kWh';
            document.getElementById('total-cost').textContent = formatSpanishNumber(analytics.factory_metrics?.total_cost || 0, 0) + ' €';

            const minPrice = priceAnalysis.min_price_eur_kwh || 0;
            const maxPrice = priceAnalysis.max_price_eur_kwh || 0;
            document.getElementById('min-max-price').textContent = formatSpanishNumber(minPrice, 4) + '/' + formatSpanishNumber(maxPrice, 4) + ' €/kWh';
        }

        // Optimization metrics
        if (analytics.optimization_potential) {
            const optimization = analytics.optimization_potential;
            document.getElementById('annual-projection').textContent = formatSpanishNumber(optimization.annual_savings_projection || 0, 0) + ' €';
            document.getElementById('optimal-hours').textContent = optimization.optimal_production_hours || '--';
        }

        // Current savings potential
        const avgPrice = analytics.price_analysis?.average_price || 0.15;
        const savingsPerHour = (avgPrice - currentPrice) * 2.4; // 2.4 kW approx consumption
        const savingsPotentialEl = document.getElementById('current-savings-potential');
        if (savingsPotentialEl) {
            if (savingsPerHour > 0) {
                savingsPotentialEl.textContent = '+' + formatSpanishNumber(savingsPerHour, 2) + ' €/h';
                savingsPotentialEl.style.color = '#4CAF50';
            } else {
                savingsPotentialEl.textContent = formatSpanishNumber(savingsPerHour, 2) + ' €/h';
                savingsPotentialEl.style.color = '#F44336';
            }
        }

        // Price ranking (simplified)
        const pricePosition = currentPrice / (avgPrice * 1.5); // Relative position
        const ranking = Math.ceil(Math.min(pricePosition * 24, 24));
        document.getElementById('price-ranking').textContent = ranking + '/24';

        // Strategic recommendations (sync with Enhanced ML Analytics)
        const strategicEl = document.getElementById('strategic-recommendation');
        if (strategicEl) {
            const enhanced = data.predictions || {};
            const enhancedRec = enhanced.enhanced_recommendations || {};

            if (enhancedRec.main_action) {
                const mainAction = enhancedRec.main_action;
                const actionIcons = {
                    'maximize_production': '🚀 Maximizar producción',
                    'increase_production': '📈 Incrementar producción',
                    'standard_production': '⚖️ Producción estándar',
                    'reduce_production': '📉 Reducir operaciones',
                    'minimize_production': '⚠️ Producción mínima',
                    'halt_production': '🚨 Parar nueva producción'
                };
                strategicEl.textContent = actionIcons[mainAction] || `🔧 ${mainAction.replace('_', ' ')}`;
            } else if (humanRecUnified && humanRecUnified.recommendation_level) {
                const level = humanRecUnified.recommendation_level;
                const levelNames = {
                    'maximize': '🚀 Maximizar producción',
                    'standard': '⚖️ Producción estándar',
                    'reduced': '📉 Reducir operaciones',
                    'minimal': '⚠️ Producción mínima',
                    'critical': '🚨 Parar nueva producción'
                };
                strategicEl.textContent = levelNames[level] || 'Evaluando...';
            } else {
                strategicEl.textContent = 'Usar criterio operacional';
            }
        }

        // === LLENAR DATOS FALTANTES ===

        // Process recommendations
        const processEl = document.getElementById('recommended-process');
        const processCostEl = document.getElementById('process-cost');
        const processActionEl = document.getElementById('process-action');

        if (processEl && processCostEl && processActionEl) {
            const enhanced = data.predictions || {};
            const enhancedRec = enhanced.enhanced_recommendations || {};

            if (enhancedRec.main_action) {
                const processMap = {
                    'maximize_production': 'Conchado extendido + Templado premium',
                    'increase_production': 'Conchado intensivo + Mezclado',
                    'standard_production': 'Conchado estándar + Moldeado',
                    'reduce_production': 'Solo conchado básico',
                    'minimize_production': 'Completar lotes actuales',
                    'halt_production': 'Ningún proceso nuevo'
                };

                const costMap = {
                    'maximize_production': (currentPrice * 4.8).toFixed(2),
                    'increase_production': (currentPrice * 3.6).toFixed(2),
                    'standard_production': (currentPrice * 2.4).toFixed(2),
                    'reduce_production': (currentPrice * 1.2).toFixed(2),
                    'minimize_production': (currentPrice * 0.6).toFixed(2),
                    'halt_production': '0.00'
                };

                processEl.textContent = processMap[enhancedRec.main_action] || 'Proceso estándar';
                processCostEl.textContent = (costMap[enhancedRec.main_action] || currentPrice * 2.4) + ' €/h';

                if (enhancedRec.main_action.includes('halt')) {
                    processActionEl.textContent = 'Detener nuevos procesos ahora';
                } else if (enhancedRec.main_action.includes('maximize')) {
                    processActionEl.textContent = 'Aprovechar ventana energética';
                } else if (enhancedRec.main_action.includes('reduce')) {
                    processActionEl.textContent = 'Reducir intensidad energética';
                } else {
                    processActionEl.textContent = 'Mantener operación normal';
                }
            } else {
                processEl.textContent = 'Conchado estándar + Moldeado';
                processCostEl.textContent = (currentPrice * 2.4).toFixed(2) + ' €/h';
                processActionEl.textContent = 'Evaluando mejores procesos...';
            }
        }

        // Optimal time window
        const optimalTimeEl = document.getElementById('optimal-time-window');
        if (optimalTimeEl) {
            const currentHour = new Date().getHours();
            if (currentPrice < avgPrice) {
                optimalTimeEl.textContent = `Ahora (hasta ${(currentHour + 2) % 24}:00h)`;
            } else {
                optimalTimeEl.textContent = '00:00-06:00 (hora valle)';
            }
        }

        // Price range
        const priceRangeEl = document.getElementById('price-range');
        if (priceRangeEl && analytics.price_analysis) {
            const minPrice = analytics.price_analysis.min_price || 0;
            const maxPrice = analytics.price_analysis.max_price || 0;
            priceRangeEl.textContent = `${formatSpanishNumber(minPrice, 4)} - ${formatSpanishNumber(maxPrice, 4)} €/kWh`;
        }

        // Unified recommendations
        const unifiedRecsEl = document.getElementById('unified-optimization-recommendations');
        if (unifiedRecsEl) {
            let recsText = '';
            if (humanRecUnified && humanRecUnified.situation_context) {
                recsText = humanRecUnified.situation_context.slice(0, 2).map(ctx => `• ${ctx}`).join('<br>');
            } else {
                // Fallback recommendations based on Enhanced ML data
                const enhanced = data.predictions || {};
                const enhancedRec = enhanced.enhanced_recommendations || {};
                if (enhancedRec.main_action) {
                    const actionRecs = {
                        'maximize_production': '• Momento óptimo para maximizar volumen<br>• Aprovechar precio energético favorable',
                        'increase_production': '• Incrementar producción moderadamente<br>• Condiciones favorables detectadas',
                        'standard_production': '• Mantener ritmo normal de producción<br>• Condiciones estables para operación',
                        'reduce_production': '• Reducir operaciones no críticas<br>• Precio energético elevado detectado',
                        'minimize_production': '• Solo completar lotes comprometidos<br>• Condiciones subóptimas',
                        'halt_production': '• Parar nueva producción inmediatamente<br>• Condiciones críticas detectadas'
                    };
                    recsText = actionRecs[enhancedRec.main_action] || '• Sistema híbrido activado<br>• Consultar recomendación principal arriba';
                } else {
                    recsText = '• Sistema híbrido activado<br>• Consultar recomendación principal arriba';
                }
            }
            unifiedRecsEl.innerHTML = recsText;
        }

        console.log('✅ Unified REE analysis rendered successfully');

    } catch (error) {
        console.error('❌ Error rendering unified REE analysis:', error);
    }
}

// 📊 SIAR Historical Analysis Renderer (Sprint 07)
function renderSIARAnalysis(data) {
    try {
        const siar = data.siar_analysis || {};

        if (siar.status !== 'success') {
            console.log('⚠️ SIAR analysis not available or failed');
            document.getElementById('siar-insights').innerHTML = '<div>⚠️ Análisis SIAR no disponible</div>';
            return;
        }

        const summary = siar.summary || {};
        const correlations = siar.correlations || {};
        const seasonal = siar.seasonal_patterns || {};
        const thresholds = siar.thresholds || {};

        // Summary Stats
        const totalRecords = summary.total_records || 0;
        document.getElementById('siar-total-records').textContent = totalRecords.toLocaleString('es-ES');

        const dateRange = summary.date_range || {};
        const startDate = dateRange.start_date ? new Date(dateRange.start_date).getFullYear() : '2000';
        const endDate = dateRange.end_date ? new Date(dateRange.end_date).getFullYear() : '2025';
        document.getElementById('siar-date-range').textContent = `${startDate} - ${endDate}`;

        // Correlations
        const tempCorr = correlations.temperature_production || {};
        const humidityCorr = correlations.humidity_production || {};

        const tempR2 = tempCorr.r_squared || 0;
        const humidityR2 = humidityCorr.r_squared || 0;

        document.getElementById('siar-temp-correlation').textContent = formatSpanishNumber(tempR2, 3);
        document.getElementById('siar-humidity-correlation').textContent = formatSpanishNumber(humidityR2, 3);

        // Seasonal Patterns
        const bestMonth = seasonal.best_month || {};
        const worstMonth = seasonal.worst_month || {};

        // Month names already come in proper format from API
        document.getElementById('siar-best-month').textContent = bestMonth.name || '--';
        document.getElementById('siar-best-month-score').textContent =
            `${formatSpanishNumber(bestMonth.efficiency_score || 0, 1)}% condiciones óptimas`;

        document.getElementById('siar-worst-month').textContent = worstMonth.name || '--';
        document.getElementById('siar-worst-month-score').textContent =
            `${formatSpanishNumber(worstMonth.efficiency_score || 0, 1)}% condiciones óptimas`;

        // Critical Thresholds
        const tempThresholds = thresholds.temperature || {};
        const humidityThresholds = thresholds.humidity || {};

        document.getElementById('siar-temp-p90').textContent = formatSpanishNumber(tempThresholds.p90 || 0, 1);
        document.getElementById('siar-temp-p95').textContent = formatSpanishNumber(tempThresholds.p95 || 0, 1);
        document.getElementById('siar-temp-p99').textContent = formatSpanishNumber(tempThresholds.p99 || 0, 1);

        document.getElementById('siar-humidity-p90').textContent = formatSpanishNumber(humidityThresholds.p90 || 0, 1);
        document.getElementById('siar-humidity-p95').textContent = formatSpanishNumber(humidityThresholds.p95 || 0, 1);
        document.getElementById('siar-humidity-p99').textContent = formatSpanishNumber(humidityThresholds.p99 || 0, 1);

        // Generate Insights
        const insights = [];

        if (tempR2 > 0.03) {
            insights.push(`🌡️ La temperatura muestra correlación significativa (R²=${formatSpanishNumber(tempR2, 3)}) con la eficiencia de producción`);
        } else {
            insights.push(`🌡️ La temperatura tiene baja correlación (R²=${formatSpanishNumber(tempR2, 3)}) - otros factores dominan`);
        }

        if (humidityR2 > 0.03) {
            insights.push(`💧 La humedad muestra correlación significativa (R²=${formatSpanishNumber(humidityR2, 3)}) con la producción`);
        }

        if (bestMonth.name) {
            insights.push(`📅 ${bestMonth.name} históricamente ofrece las mejores condiciones (${formatSpanishNumber(bestMonth.efficiency_score || 0, 1)}%)`);
        }

        if (worstMonth.name) {
            insights.push(`⚠️ ${worstMonth.name} requiere mayor atención operativa (solo ${formatSpanishNumber(worstMonth.efficiency_score || 0, 1)}% óptimo)`);
        }

        insights.push(`📊 Basado en ${totalRecords.toLocaleString('es-ES')} registros históricos (${startDate}-${endDate})`);

        document.getElementById('siar-insights').innerHTML = insights.map(i => `<div style="margin-bottom: 0.5rem;">${i}</div>`).join('');

        console.log('✅ SIAR analysis rendered successfully');

    } catch (error) {
        console.error('❌ Error rendering SIAR analysis:', error);
        document.getElementById('siar-insights').innerHTML = '<div>❌ Error al cargar análisis SIAR</div>';
    }
}

// Cargar datos al inicializar
loadData();

// ============================================
// SPRINT 08: HOURLY OPTIMIZATION
// ============================================

async function loadOptimizationPlan(targetDate = null, targetKg = null) {
    /**
     * Carga el plan optimizado de producción desde el endpoint /optimize/production/daily
     */
    try {
        console.log('🎯 Loading optimization plan...');

        // Build query params
        const params = new URLSearchParams();
        if (targetDate) params.append('target_date', targetDate);
        if (targetKg) params.append('target_kg', targetKg);

        const url = `/optimize/production/daily${params.toString() ? '?' + params.toString() : ''}`;

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.optimization) {
            renderOptimizationPlan(data.optimization);
            console.log('✅ Optimization plan loaded successfully');
        } else {
            throw new Error('No optimization data in response');
        }

    } catch (error) {
        console.error('❌ Error loading optimization plan:', error);
        renderOptimizationError(error.message);
    }
}

function renderOptimizationPlan(optimization) {
    /**
     * Renderiza el plan optimizado en el dashboard
     */
    try {
        // Summary metrics
        const savingsEurEl = document.getElementById('opt-savings-eur');
        const savingsPercentEl = document.getElementById('opt-savings-percent');
        const numBatchesEl = document.getElementById('opt-num-batches');
        const targetKgEl = document.getElementById('opt-target-kg');
        const totalCostEl = document.getElementById('opt-total-cost');
        const totalEnergyEl = document.getElementById('opt-total-energy');

        if (savingsEurEl) savingsEurEl.textContent = formatSpanishNumber(optimization.savings.absolute_eur, 2) + ' €';
        if (savingsPercentEl) savingsPercentEl.textContent = formatSpanishNumber(optimization.savings.percent, 1) + '%';
        if (numBatchesEl) numBatchesEl.textContent = optimization.num_batches;
        if (targetKgEl) targetKgEl.textContent = optimization.target_kg;
        if (totalCostEl) totalCostEl.textContent = formatSpanishNumber(optimization.plan.total_cost_eur, 2) + ' €';
        if (totalEnergyEl) totalEnergyEl.textContent = formatSpanishNumber(optimization.plan.total_energy_kwh, 0);

        // Baseline comparison
        const baselineCostEl = document.getElementById('baseline-cost');
        const baselineEnergyEl = document.getElementById('baseline-energy');
        const baselineAvgPriceEl = document.getElementById('baseline-avg-price');
        const optimizedCostEl = document.getElementById('optimized-cost');
        const optimizedEnergyEl = document.getElementById('optimized-energy');
        const optimizedAvgPriceEl = document.getElementById('optimized-avg-price');

        if (baselineCostEl) baselineCostEl.textContent = formatSpanishNumber(optimization.baseline.total_cost, 2) + ' €';
        if (baselineEnergyEl) baselineEnergyEl.textContent = formatSpanishNumber(optimization.baseline.total_energy_kwh, 0) + ' kWh';
        if (baselineAvgPriceEl) baselineAvgPriceEl.textContent = formatSpanishNumber(optimization.baseline.avg_price_eur_kwh, 4) + ' €/kWh';
        if (optimizedCostEl) optimizedCostEl.textContent = formatSpanishNumber(optimization.plan.total_cost_eur, 2) + ' €';
        if (optimizedEnergyEl) optimizedEnergyEl.textContent = formatSpanishNumber(optimization.plan.total_energy_kwh, 0) + ' kWh';
        if (optimizedAvgPriceEl) optimizedAvgPriceEl.textContent = formatSpanishNumber(optimization.plan.avg_price_eur_kwh, 4) + ' €/kWh';

        // Render batches timeline
        renderBatchesTimeline(optimization.plan.batches);

        // Render hourly timeline (NEW)
        if (optimization.hourly_timeline) {
            renderHourlyTimeline(optimization.hourly_timeline);
        }

        // Render recommendations
        renderOptimizationRecommendations(optimization.recommendations);

        console.log('✅ Optimization plan rendered successfully');

    } catch (error) {
        console.error('❌ Error rendering optimization plan:', error);
        renderOptimizationError('Error rendering plan: ' + error.message);
    }
}

function renderBatchesTimeline(batches) {
    /**
     * Renderiza la timeline de batches optimizados
     */
    const timelineEl = document.getElementById('opt-batches-timeline');
    if (!timelineEl) return;

    if (!batches || batches.length === 0) {
        timelineEl.innerHTML = '<div style="text-align: center; padding: 2rem; opacity: 0.7;">❌ No hay batches programados</div>';
        return;
    }

    let html = '';

    batches.forEach((batch) => {
        // Quality badge
        const qualityBadge = batch.quality_type === 'premium'
            ? '<span style="background: #FFD700; color: #1e3c72; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem; font-weight: bold;">⭐ PREMIUM</span>'
            : '<span style="background: rgba(255,255,255,0.2); padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">📦 STANDARD</span>';

        // Weather conditions badge
        const temp = batch.weather_conditions.avg_temperature;
        const humidity = batch.weather_conditions.avg_humidity;
        const weatherBadge = temp <= 28 && humidity <= 60
            ? '✅'
            : temp <= 32 && humidity <= 70
            ? '⚠️'
            : '🔴';

        html += `
            <div style="background: rgba(255,255,255,0.08); padding: 1rem; margin-bottom: 0.75rem; border-radius: 8px; border-left: 4px solid ${batch.quality_type === 'premium' ? '#FFD700' : '#4CAF50'};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <span style="font-size: 1.2rem; font-weight: bold;">${batch.batch_id}</span>
                        ${qualityBadge}
                        <span style="opacity: 0.8; font-size: 0.9rem;">🕐 ${batch.start_time} - ${batch.end_time}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <span style="font-size: 0.9rem;">💰 ${formatSpanishNumber(batch.total_cost_eur, 2)} €</span>
                        <span style="font-size: 1.2rem;">${weatherBadge}</span>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.75rem;">
                    <div>⚡ ${formatSpanishNumber(batch.total_energy_kwh, 1)} kWh</div>
                    <div>🌡️ ${formatSpanishNumber(temp, 1)}°C</div>
                    <div>💧 ${formatSpanishNumber(humidity, 0)}%</div>
                </div>

                <div style="font-size: 0.85rem; opacity: 0.8;">
                    ${batch.recommendation}
                </div>

                <!-- Processes breakdown (collapsible) -->
                <details style="margin-top: 0.75rem;">
                    <summary style="cursor: pointer; font-size: 0.85rem; opacity: 0.8; padding: 0.5rem; background: rgba(255,255,255,0.05); border-radius: 4px;">
                        📋 Ver procesos (${batch.processes.length})
                    </summary>
                    <div style="margin-top: 0.5rem; padding-left: 1rem; font-size: 0.8rem; line-height: 1.6; opacity: 0.85;">
        `;

        batch.processes.forEach(proc => {
            html += `
                <div style="padding: 0.25rem 0;">
                    <strong>${proc.name}</strong>:
                    ${proc.duration_minutes} min •
                    ${formatSpanishNumber(proc.energy_kwh, 1)} kWh •
                    ${formatSpanishNumber(proc.cost_eur, 2)} €
                </div>
            `;
        });

        html += `
                    </div>
                </details>
            </div>
        `;
    });

    timelineEl.innerHTML = html;
}

function renderHourlyTimeline(hourlyTimeline) {
    /**
     * Renderiza la timeline horaria 24h con precio, periodo y producción
     */
    const container = document.getElementById('hourly-timeline-container');
    if (!container) return;

    if (!hourlyTimeline || hourlyTimeline.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 2rem; opacity: 0.7;">❌ No hay datos de timeline horaria</div>';
        return;
    }

    // Crear tabla HTML
    let html = `
        <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem; color: white;">
            <thead>
                <tr style="background: rgba(255,255,255,0.15); position: sticky; top: 0;">
                    <th style="padding: 0.75rem; text-align: left; border-bottom: 2px solid rgba(255,255,255,0.3);">Hora</th>
                    <th style="padding: 0.75rem; text-align: right; border-bottom: 2px solid rgba(255,255,255,0.3);">Precio</th>
                    <th style="padding: 0.75rem; text-align: center; border-bottom: 2px solid rgba(255,255,255,0.3);">Periodo</th>
                    <th style="padding: 0.75rem; text-align: left; border-bottom: 2px solid rgba(255,255,255,0.3);">Proceso</th>
                    <th style="padding: 0.75rem; text-align: center; border-bottom: 2px solid rgba(255,255,255,0.3);">Batch</th>
                    <th style="padding: 0.75rem; text-align: center; border-bottom: 2px solid rgba(255,255,255,0.3);">Clima</th>
                </tr>
            </thead>
            <tbody>
    `;

    hourlyTimeline.forEach((hour) => {
        // Determinar color de fondo basado en periodo tarifario
        const bgColor = hour.tariff_period === 'P1'
            ? 'rgba(220, 38, 38, 0.15)'   // Rojo claro
            : hour.tariff_period === 'P2'
            ? 'rgba(245, 158, 11, 0.15)'  // Amarillo claro
            : 'rgba(16, 185, 129, 0.15)'; // Verde claro

        // Badge de periodo tarifario
        const periodBadge = `
            <span style="
                background: ${hour.tariff_color};
                color: white;
                padding: 0.25rem 0.5rem;
                border-radius: 4px;
                font-weight: bold;
                font-size: 0.75rem;
            ">${hour.tariff_period}</span>
        `;

        // Icono de clima
        const climateIcon = hour.climate_status === 'optimal'
            ? '✅'
            : hour.climate_status === 'acceptable'
            ? '⚠️'
            : '🔴';

        // Información de proceso y batch
        const processInfo = hour.active_process
            ? `<span style="font-weight: 500;">${hour.active_process}</span>`
            : '<span style="opacity: 0.5;">-</span>';

        const batchInfo = hour.active_batch
            ? `<span style="background: rgba(255,215,0,0.2); padding: 0.2rem 0.4rem; border-radius: 3px; font-weight: bold;">${hour.active_batch}</span>`
            : '<span style="opacity: 0.5;">-</span>';

        // Resaltar filas con producción
        const rowStyle = hour.is_production_hour
            ? `background: ${bgColor}; border-left: 3px solid ${hour.tariff_color};`
            : `background: ${bgColor};`;

        html += `
            <tr style="${rowStyle}">
                <td style="padding: 0.5rem; font-weight: ${hour.is_production_hour ? 'bold' : 'normal'};">${hour.time}</td>
                <td style="padding: 0.5rem; text-align: right; font-family: monospace;">${formatSpanishNumber(hour.price_eur_kwh, 4)} €</td>
                <td style="padding: 0.5rem; text-align: center;">${periodBadge}</td>
                <td style="padding: 0.5rem;">${processInfo}</td>
                <td style="padding: 0.5rem; text-align: center;">${batchInfo}</td>
                <td style="padding: 0.5rem; text-align: center;" title="Temp: ${hour.temperature}°C, Humedad: ${hour.humidity}%">
                    ${climateIcon} ${hour.temperature}°C
                </td>
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    container.innerHTML = html;
    console.log('✅ Hourly timeline rendered successfully');
}

function renderOptimizationRecommendations(recommendations) {
    /**
     * Renderiza las recomendaciones de optimización
     */
    const recommendationsEl = document.getElementById('opt-recommendations');
    if (!recommendationsEl) return;

    if (!recommendations || recommendations.length === 0) {
        recommendationsEl.innerHTML = '<div style="opacity: 0.7;">ℹ️ No hay recomendaciones disponibles</div>';
        return;
    }

    let html = '<div style="line-height: 1.8;">';
    recommendations.forEach(rec => {
        html += `<div>• ${rec}</div>`;
    });
    html += '</div>';

    recommendationsEl.innerHTML = html;
}

function renderOptimizationError(errorMessage) {
    /**
     * Renderiza error en la sección de optimización
     */
    const timelineEl = document.getElementById('opt-batches-timeline');
    if (timelineEl) {
        timelineEl.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: #FF5252;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚠️</div>
                <div style="font-weight: bold; margin-bottom: 0.5rem;">Error cargando plan optimizado</div>
                <div style="font-size: 0.85rem; opacity: 0.8;">${errorMessage}</div>
            </div>
        `;
    }
}

// Auto-refresh cada 2 minutos
setInterval(loadData, 2 * 60 * 1000);
