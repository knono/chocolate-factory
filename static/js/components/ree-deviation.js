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
        const { deviation_summary, reliability_by_period, worst_deviation } = this.data;

        const html = `
            <div class="ree-deviation-container">
                <!-- Summary Metrics -->
                <div class="deviation-summary-grid">
                    <div class="deviation-metric">
                        <div class="metric-icon">📊</div>
                        <div class="metric-content">
                            <div class="metric-value">±${deviation_summary.avg_deviation_eur_kwh.toFixed(4)}</div>
                            <div class="metric-label">Desviación Media</div>
                        </div>
                    </div>
                    <div class="deviation-metric">
                        <div class="metric-icon">🎯</div>
                        <div class="metric-content">
                            <div class="metric-value">${deviation_summary.accuracy_score_pct}%</div>
                            <div class="metric-label">Accuracy Score</div>
                        </div>
                    </div>
                    <div class="deviation-metric">
                        <div class="metric-icon">📈</div>
                        <div class="metric-content">
                            <div class="metric-value">${deviation_summary.trend}</div>
                            <div class="metric-label">Tendencia</div>
                        </div>
                    </div>
                </div>

                <!-- Reliability by Period -->
                <div class="reliability-section">
                    <h4 class="section-title">📊 Fiabilidad por Periodo Tarifario</h4>
                    <div class="reliability-grid">
                        <div class="reliability-card success">
                            <div class="reliability-period">Valle (P3) - 00-07h</div>
                            <div class="reliability-deviation">
                                Desviación: ±${reliability_by_period.valle_p3.avg_deviation.toFixed(4)} €/kWh
                            </div>
                            <div class="reliability-status">${reliability_by_period.valle_p3.reliability}</div>
                        </div>
                        <div class="reliability-card warning">
                            <div class="reliability-period">Punta (P1) - 10-13h, 18-21h</div>
                            <div class="reliability-deviation">
                                Desviación: ±${reliability_by_period.punta_p1.avg_deviation.toFixed(4)} €/kWh
                            </div>
                            <div class="reliability-status">${reliability_by_period.punta_p1.reliability}</div>
                        </div>
                    </div>
                </div>

                <!-- Worst Deviation -->
                <div class="worst-deviation-section">
                    <h4 class="section-title">⚠️ Mayor Desviación (Últimas 24h)</h4>
                    <div class="worst-deviation-card">
                        <div class="deviation-time">${worst_deviation.hour}</div>
                        <div class="deviation-comparison">
                            <div class="comparison-item">
                                <span class="comparison-label">Predicho:</span>
                                <span class="comparison-value">${worst_deviation.predicted.toFixed(4)} €/kWh</span>
                            </div>
                            <div class="comparison-arrow">→</div>
                            <div class="comparison-item">
                                <span class="comparison-label">Real:</span>
                                <span class="comparison-value">${worst_deviation.actual.toFixed(4)} €/kWh</span>
                            </div>
                        </div>
                        <div class="deviation-value">
                            Diferencia: ${worst_deviation.deviation.toFixed(4)} €/kWh
                        </div>
                    </div>
                </div>

                <!-- Insights -->
                <div class="deviation-insights">
                    <div class="insight-icon">💡</div>
                    <div class="insight-text">
                        ${this.generateInsights(deviation_summary, reliability_by_period)}
                    </div>
                </div>
            </div>
        `;

        this.container.innerHTML = html;
    }

    generateInsights(summary, reliability) {
        const insights = [];

        if (summary.accuracy_score_pct >= 85) {
            insights.push('Predicciones muy confiables (>85% accuracy)');
        } else if (summary.accuracy_score_pct >= 70) {
            insights.push('Predicciones confiables (70-85% accuracy)');
        } else {
            insights.push('⚠️ Predicciones con margen de mejora (<70% accuracy)');
        }

        if (summary.trend === 'STABLE') {
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
