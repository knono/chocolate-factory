// REE Deviation Component - Sprint 09
// Displays REE D-1 vs Real price analysis

class REEDeviationComponent {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.data = null;
    }

    async render() {
        if (!this.container) {
            console.error('REEDeviation container not found');
            return;
        }

        try {
            // Fetch REE deviation analysis
            this.data = await apiClient.get('/insights/ree-deviation');

            if (this.data.status === 'error') {
                this.renderError(this.data.message);
                return;
            }

            this.renderContent();

        } catch (error) {
            console.error('Failed to load REE deviation:', error);
            this.renderError('Error al cargar análisis REE');
        }
    }

    renderContent() {
        const { validation_metrics, performance_context, reliability_by_period, model_info, practical_value } = this.data;

        const html = `
            <div class="ree-deviation-container">
                <!-- Summary Metrics (Prophet Validated) -->
                <div class="deviation-summary-grid">
                    <div class="deviation-metric">
                        <div class="metric-icon">📊</div>
                        <div class="metric-content">
                            <div class="metric-value">±${validation_metrics.mae_eur_kwh.toFixed(3)}</div>
                            <div class="metric-label">MAE (Error Medio)</div>
                        </div>
                    </div>
                    <div class="deviation-metric">
                        <div class="metric-icon">🎯</div>
                        <div class="metric-content">
                            <div class="metric-value">${(validation_metrics.r2_score * 100).toFixed(1)}%</div>
                            <div class="metric-label">R² Score</div>
                        </div>
                    </div>
                    <div class="deviation-metric">
                        <div class="metric-icon">📈</div>
                        <div class="metric-content">
                            <div class="metric-value">${validation_metrics.coverage_95pct.toFixed(1)}%</div>
                            <div class="metric-label">Coverage 95%</div>
                        </div>
                    </div>
                </div>

                <!-- Model Info -->
                <div class="model-info-section" style="background: rgba(59, 130, 246, 0.1); padding: 1rem; border-radius: 8px; margin: 1rem 0; border-left: 4px solid #3b82f6;">
                    <div style="font-size: 0.85rem; color: #333;">
                        <strong>🤖 ${model_info.model_type}</strong> - ${model_info.validation_method}<br>
                        <span style="color: #666; font-size: 0.8rem;">${model_info.note}</span>
                    </div>
                </div>

                <!-- Performance Context -->
                <div class="context-section" style="background: rgba(16, 185, 129, 0.1); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                    <h5 style="margin: 0 0 0.5rem 0; color: #10b981; font-size: 0.9rem;">💡 Contexto de Rendimiento</h5>
                    <div style="font-size: 0.8rem; color: #333; line-height: 1.5;">
                        • ${performance_context.market_volatility}<br>
                        • ${performance_context.r2_interpretation}<br>
                        • ${performance_context.mae_practical}
                    </div>
                </div>

                <!-- Reliability by Period -->
                <div class="reliability-section">
                    <h4 class="section-title">📊 Fiabilidad por Periodo Tarifario</h4>
                    <div class="reliability-grid">
                        <div class="reliability-card success">
                            <div class="reliability-period">Valle (P3) - 00-07h</div>
                            <div class="reliability-deviation">
                                ${reliability_by_period.valle_p3.expected_deviation}
                            </div>
                            <div class="reliability-status">${reliability_by_period.valle_p3.reliability}</div>
                            <div style="font-size: 0.75rem; color: #666; margin-top: 0.5rem;">
                                Confianza: ${reliability_by_period.valle_p3.scheduling_confidence}
                            </div>
                        </div>
                        <div class="reliability-card warning">
                            <div class="reliability-period">Punta (P1) - 10-13h, 18-21h</div>
                            <div class="reliability-deviation">
                                ${reliability_by_period.punta_p1.expected_deviation}
                            </div>
                            <div class="reliability-status">${reliability_by_period.punta_p1.reliability}</div>
                            <div style="font-size: 0.75rem; color: #666; margin-top: 0.5rem;">
                                Confianza: ${reliability_by_period.punta_p1.scheduling_confidence}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Practical Value -->
                <div class="practical-value-section" style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(124, 58, 237, 0.1)); padding: 1rem; border-radius: 8px; margin: 1rem 0; border: 2px solid rgba(139, 92, 246, 0.3);">
                    <h4 class="section-title" style="color: #8b5cf6; margin-bottom: 0.75rem;">💰 Valor Práctico en Fábrica</h4>
                    <div style="font-size: 0.85rem; color: #333; line-height: 1.6;">
                        <div style="margin-bottom: 0.5rem;">
                            <strong>🏭 ${practical_value.conchado_batch}</strong>
                        </div>
                        <div style="margin-bottom: 0.5rem;">
                            📅 Ahorro semanal: ${practical_value.weekly_savings}
                        </div>
                        <div style="margin-bottom: 0.5rem;">
                            📈 Impacto anual: <strong>${practical_value.annual_impact}</strong>
                        </div>
                        <div style="color: #666; font-size: 0.8rem; margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid rgba(0,0,0,0.1);">
                            ℹ️ ${practical_value.error_cost}
                        </div>
                    </div>
                </div>

                <!-- Insights -->
                <div class="deviation-insights">
                    <div class="insight-icon">💡</div>
                    <div class="insight-text">
                        ${this.generateInsights(validation_metrics, performance_context)}
                    </div>
                </div>
            </div>
        `;

        this.container.innerHTML = html;
    }

    generateInsights(metrics, context) {
        const insights = [];

        // R² interpretation
        if (metrics.r2_score >= 0.60) {
            insights.push('✅ Modelo explica >60% de varianza de precios (excelente para mercado volátil)');
        } else if (metrics.r2_score >= 0.40) {
            insights.push('✅ Modelo explica >40% de varianza (aceptable dado alta volatilidad mercado)');
        } else {
            insights.push('⚠️ R² <40% - modelo con limitaciones predictivas');
        }

        // Coverage interpretation
        if (metrics.coverage_95pct >= 90) {
            insights.push(`✅ ${metrics.coverage_95pct.toFixed(0)}% predicciones dentro intervalo confianza - alta fiabilidad`);
        }

        // MAE practical value
        if (metrics.mae_eur_kwh <= 0.03) {
            insights.push('✅ Error promedio <3 céntimos - suficiente para decisiones scheduling');
        } else if (metrics.mae_eur_kwh <= 0.05) {
            insights.push('⚠️ Error promedio 3-5 céntimos - aceptable pero mejorable');
        }

        // General recommendation
        if (insights.length > 0) {
            insights.push('Desviaciones estables y predecibles');
        } else {
            insights.push('Variabilidad mayor en periodos punta');
        }

        insights.push('Horarios valle (00-06h) más confiables para planificación');

        return insights.join(' • ');
    }

    renderError(message) {
        this.container.innerHTML = `
            <div class="error-state">
                <span class="error-icon">⚠️</span>
                <span class="error-message">${message}</span>
            </div>
        `;
    }
}

// CSS Styles for REE Deviation Component
const reeDeviationCSS = `
.ree-deviation-container {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.deviation-summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
}

.deviation-metric {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: rgba(0, 0, 0, 0.02);
    padding: 1rem;
    border-radius: 8px;
}

.metric-icon {
    font-size: 2rem;
}

.metric-content {
    flex: 1;
}

.metric-value {
    font-size: 1.5rem;
    font-weight: bold;
    color: #333;
}

.metric-label {
    font-size: 0.85rem;
    color: #666;
    margin-top: 0.25rem;
}

.reliability-section, .worst-deviation-section {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.section-title {
    color: #333;
    font-size: 1rem;
    margin: 0;
}

.reliability-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1rem;
}

.reliability-card {
    background: rgba(0, 0, 0, 0.02);
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #10b981;
}

.reliability-card.success {
    border-left-color: #10b981;
}

.reliability-card.warning {
    border-left-color: #f59e0b;
}

.reliability-period {
    font-weight: bold;
    color: #333;
    margin-bottom: 0.5rem;
}

.reliability-deviation {
    font-size: 0.9rem;
    color: #666;
    margin-bottom: 0.5rem;
}

.reliability-status {
    font-size: 0.85rem;
    color: #666;
    font-weight: 600;
}

.worst-deviation-card {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 8px;
    padding: 1rem;
}

.deviation-time {
    font-size: 1.2rem;
    font-weight: bold;
    color: #fbbf24;
    margin-bottom: 1rem;
}

.deviation-comparison {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1rem;
}

.comparison-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.comparison-label {
    font-size: 0.8rem;
    color: #666;
}

.comparison-value {
    font-size: 1.1rem;
    font-weight: bold;
    color: #333;
}

.comparison-arrow {
    font-size: 1.5rem;
    color: #fbbf24;
}

.deviation-value {
    text-align: center;
    font-size: 0.95rem;
    color: #fbbf24;
    font-weight: 600;
}

.deviation-insights {
    display: flex;
    gap: 1rem;
    padding: 1rem;
    background: rgba(139, 92, 246, 0.1);
    border-radius: 8px;
    border-left: 4px solid #8b5cf6;
}

.insight-icon {
    font-size: 1.5rem;
}

.insight-text {
    flex: 1;
    font-size: 0.9rem;
    line-height: 1.6;
    color: #666;
}
`;
