// Savings Tracking Component - Sprint 09
// Displays real energy savings vs baseline

class SavingsTrackingComponent {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.data = null;
    }

    async render() {
        if (!this.container) {
            console.error('SavingsTracking container not found');
            return;
        }

        try {
            // Fetch savings tracking data
            this.data = await apiClient.get('/insights/savings-tracking');

            if (this.data.status === 'error') {
                this.renderError(this.data.message);
                return;
            }

            this.renderContent();

        } catch (error) {
            console.error('Failed to load savings tracking:', error);
            this.renderError('Error al cargar tracking de ahorros');
        }
    }

    renderContent() {
        const { daily_savings, weekly_projection, monthly_tracking, annual_projection } = this.data;

        const html = `
            <div class="savings-tracking-container">
                <!-- Daily Comparison -->
                <div class="savings-section daily">
                    <h4 class="section-title">📊 Comparativa Hoy</h4>
                    <div class="comparison-grid">
                        <div class="comparison-card baseline">
                            <div class="card-label">Plan Baseline (08-16h)</div>
                            <div class="card-value">${daily_savings.baseline_cost_eur.toFixed(2)}€</div>
                            <div class="card-sublabel">Horario fijo tradicional</div>
                        </div>
                        <div class="comparison-arrow">→</div>
                        <div class="comparison-card optimized">
                            <div class="card-label">Plan Optimizado</div>
                            <div class="card-value">${daily_savings.optimized_cost_eur.toFixed(2)}€</div>
                            <div class="card-sublabel">Prophet + ML optimization</div>
                        </div>
                    </div>
                    <div class="savings-highlight">
                        <div class="savings-amount">💰 ${daily_savings.savings_eur.toFixed(2)}€</div>
                        <div class="savings-percentage">${daily_savings.savings_pct.toFixed(1)}% ahorro diario</div>
                    </div>
                </div>

                <!-- Weekly Projection -->
                <div class="savings-section weekly">
                    <h4 class="section-title">📅 Proyección Semanal</h4>
                    <div class="projection-grid">
                        <div class="projection-metric">
                            <div class="metric-label">Plan Optimizado</div>
                            <div class="metric-value success">${weekly_projection.optimized_cost_eur.toFixed(2)}€</div>
                        </div>
                        <div class="projection-metric">
                            <div class="metric-label">Plan Baseline</div>
                            <div class="metric-value warning">${weekly_projection.baseline_cost_eur.toFixed(2)}€</div>
                        </div>
                        <div class="projection-metric highlight">
                            <div class="metric-label">Ahorro Semanal</div>
                            <div class="metric-value highlight">${weekly_projection.savings_eur.toFixed(2)}€</div>
                        </div>
                    </div>
                </div>

                <!-- Monthly Progress -->
                <div class="savings-section monthly">
                    <h4 class="section-title">🎯 Objetivo Mensual</h4>
                    <div class="monthly-progress-container">
                        <div class="progress-stats">
                            <div class="stat-item">
                                <span class="stat-label">Meta:</span>
                                <span class="stat-value">${monthly_tracking.target_eur}€</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Proyectado:</span>
                                <span class="stat-value">${monthly_tracking.projected_eur}€</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Progreso:</span>
                                <span class="stat-value ${monthly_tracking.progress_pct >= 90 ? 'success' : 'warning'}">
                                    ${monthly_tracking.progress_pct.toFixed(1)}%
                                </span>
                            </div>
                        </div>
                        <div class="progress-bar-container">
                            <div class="progress-bar" style="width: ${Math.min(monthly_tracking.progress_pct, 100)}%">
                            </div>
                        </div>
                        <div class="progress-status ${monthly_tracking.progress_pct >= 90 ? 'on-track' : 'below-target'}">
                            ${monthly_tracking.status}
                        </div>
                    </div>
                </div>

                <!-- Annual Projection -->
                <div class="savings-section annual">
                    <h4 class="section-title">📈 ROI Anual Estimado</h4>
                    <div class="annual-roi-card">
                        <div class="roi-amount">${(annual_projection.baseline_theoretical_savings_eur || 0).toLocaleString('es-ES')}€</div>
                        <div class="roi-description">${annual_projection.roi_description || 'N/A'}</div>
                        <div class="roi-breakdown">
                            Basado en ahorro diario promedio de ${daily_savings.savings_eur.toFixed(2)}€ × 365 días
                        </div>
                    </div>
                </div>

                <!-- Info Note -->
                <div class="savings-note">
                    <div class="note-icon">ℹ️</div>
                    <div class="note-text">
                        Ahorros calculados comparando optimización horaria (Prophet ML + clima)
                        vs horario fijo tradicional 08-16h. ROI basado en proyección anual.
                    </div>
                </div>
            </div>
        `;

        this.container.innerHTML = html;
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

// CSS Styles for Savings Tracking Component
const savingsTrackingCSS = `
.savings-tracking-container {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.savings-section {
    background: rgba(0, 0, 0, 0.02);
    padding: 1.25rem;
    border-radius: 10px;
}

.section-title {
    color: #333;
    font-size: 1rem;
    margin-bottom: 1rem;
    font-weight: 600;
}

/* Daily Comparison */
.comparison-grid {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 1rem;
    align-items: center;
    margin-bottom: 1rem;
}

.comparison-card {
    background: rgba(0, 0, 0, 0.02);
    padding: 1rem;
    border-radius: 8px;
    text-align: center;
}

.comparison-card.baseline {
    border: 2px solid rgba(245, 158, 11, 0.4);
}

.comparison-card.optimized {
    border: 2px solid rgba(16, 185, 129, 0.4);
}

.card-label {
    font-size: 0.85rem;
    color: #666;
    margin-bottom: 0.5rem;
}

.card-value {
    font-size: 1.8rem;
    font-weight: bold;
    color: #333;
    margin-bottom: 0.25rem;
}

.card-sublabel {
    font-size: 0.75rem;
    color: #666;
}

.comparison-arrow {
    font-size: 2rem;
    color: #10b981;
    text-align: center;
}

.savings-highlight {
    text-align: center;
    padding: 1rem;
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.2));
    border-radius: 8px;
    border: 2px solid rgba(16, 185, 129, 0.4);
}

.savings-amount {
    font-size: 2rem;
    font-weight: bold;
    color: #10b981;
    margin-bottom: 0.25rem;
}

.savings-percentage {
    font-size: 0.95rem;
    color: #666;
}

/* Weekly Projection */
.projection-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
}

.projection-metric {
    background: rgba(0, 0, 0, 0.02);
    padding: 1rem;
    border-radius: 8px;
    text-align: center;
}

.projection-metric.highlight {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.2));
    border: 2px solid rgba(59, 130, 246, 0.4);
}

.metric-label {
    font-size: 0.85rem;
    color: #666;
    margin-bottom: 0.5rem;
}

.metric-value {
    font-size: 1.5rem;
    font-weight: bold;
    color: #333;
}

.metric-value.success {
    color: #10b981;
}

.metric-value.warning {
    color: #f59e0b;
}

.metric-value.highlight {
    color: #3b82f6;
    font-size: 1.8rem;
}

/* Monthly Progress */
.monthly-progress-container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.progress-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
}

.stat-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    background: rgba(0, 0, 0, 0.02);
    border-radius: 6px;
}

.stat-label {
    font-size: 0.85rem;
    color: #666;
}

.stat-value {
    font-size: 1.1rem;
    font-weight: bold;
    color: #333;
}

.stat-value.success {
    color: #10b981;
}

.stat-value.warning {
    color: #f59e0b;
}

.progress-bar-container {
    width: 100%;
    height: 24px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    overflow: hidden;
    position: relative;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #10b981, #059669);
    border-radius: 12px;
    transition: width 1s ease-in-out;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 0.5rem;
}

.progress-status {
    text-align: center;
    font-size: 0.95rem;
    font-weight: 600;
    padding: 0.5rem;
}

.progress-status.on-track {
    color: #10b981;
}

.progress-status.below-target {
    color: #f59e0b;
}

/* Annual ROI */
.annual-roi-card {
    text-align: center;
    padding: 1.5rem;
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(124, 58, 237, 0.2));
    border: 2px solid rgba(139, 92, 246, 0.4);
    border-radius: 10px;
}

.roi-amount {
    font-size: 2.5rem;
    font-weight: bold;
    color: #333;
    margin-bottom: 0.5rem;
}

.roi-description {
    font-size: 1.1rem;
    color: #333;
    margin-bottom: 1rem;
    font-weight: 600;
}

.roi-breakdown {
    font-size: 0.85rem;
    color: #666;
    font-style: italic;
}

/* Info Note */
.savings-note {
    display: flex;
    gap: 1rem;
    padding: 1rem;
    background: rgba(59, 130, 246, 0.1);
    border-radius: 8px;
    border-left: 4px solid #3b82f6;
}

.note-icon {
    font-size: 1.5rem;
    flex-shrink: 0;
}

.note-text {
    flex: 1;
    font-size: 0.85rem;
    line-height: 1.5;
    color: #666;
}
`;
