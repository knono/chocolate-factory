// Optimal Windows Component - Sprint 09
// Displays next 7 days optimal production windows

class OptimalWindowsComponent {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.data = null;
    }

    async render() {
        if (!this.container) {
            console.error('OptimalWindows container not found');
            return;
        }

        try {
            // Fetch optimal windows data
            this.data = await apiClient.get('/insights/optimal-windows?days=7');

            if (this.data.status === 'error') {
                this.renderError(this.data.message);
                return;
            }

            this.renderContent();

        } catch (error) {
            console.error('Failed to load optimal windows:', error);
            this.renderError('Error al cargar ventanas óptimas');
        }
    }

    renderContent() {
        const { optimal_windows, avoid_windows, summary } = this.data;

        const html = `
            <div class="optimal-windows-container">
                <!-- Summary Stats -->
                <div class="window-summary-grid">
                    <div class="summary-stat success">
                        <div class="stat-value">${summary.total_optimal_hours || 0}h</div>
                        <div class="stat-label">Horas Óptimas</div>
                    </div>
                    <div class="summary-stat info">
                        <div class="stat-value">${summary.best_price ? Formatters.decimal(summary.best_price, 4) : '--'}</div>
                        <div class="stat-label">Mejor Precio (€/kWh)</div>
                    </div>
                    <div class="summary-stat warning">
                        <div class="stat-value">${summary.total_avoid_hours || 0}h</div>
                        <div class="stat-label">Horas Evitar</div>
                    </div>
                </div>

                <!-- Optimal Windows List -->
                <div class="windows-section">
                    <h4 class="section-title">🟢 Ventanas Óptimas (Próximos 7 Días)</h4>
                    ${this.renderOptimalWindows(optimal_windows)}
                </div>

                <!-- Avoid Windows List -->
                ${avoid_windows && avoid_windows.length > 0 ? `
                    <div class="windows-section avoid-section">
                        <h4 class="section-title">⚠️ Ventanas a Evitar</h4>
                        ${this.renderAvoidWindows(avoid_windows)}
                    </div>
                ` : ''}
            </div>
        `;

        this.container.innerHTML = html;
    }

    renderOptimalWindows(windows) {
        if (!windows || windows.length === 0) {
            return '<div class="empty-state">No hay ventanas óptimas disponibles</div>';
        }

        return windows.map(window => {
            const date = new Date(window.datetime);
            const dayName = date.toLocaleDateString('es-ES', { weekday: 'short' });
            const dateStr = date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });

            return `
                <div class="window-card optimal">
                    <div class="window-header">
                        <div class="window-time">
                            <span class="window-icon">${window.icon}</span>
                            <span class="window-day">${dayName.toUpperCase()}</span>
                            <span class="window-date">${dateStr}</span>
                            <span class="window-hours">${window.hours}</span>
                        </div>
                        <div class="window-badge ${window.quality.toLowerCase()}">
                            ${window.quality}
                        </div>
                    </div>
                    <div class="window-content">
                        <div class="window-price">
                            <span class="price-label">Precio Promedio:</span>
                            <span class="price-value">${Formatters.decimal(window.avg_price_eur_kwh, 4)} €/kWh</span>
                        </div>
                        <div class="window-tariff">
                            <span class="tariff-badge ${this.getTariffClass(window.tariff_period)}">
                                ${window.tariff_period}
                            </span>
                            <span class="duration">${window.duration_hours}h duración</span>
                        </div>
                        <div class="window-recommendation">
                            <div class="rec-icon">→</div>
                            <div class="rec-text">${window.recommended_process}</div>
                        </div>
                        <div class="window-savings">
                            <span class="savings-icon">💰</span>
                            <span class="savings-text">Ahorro: ${Formatters.decimal(window.estimated_savings_eur, 2)}€ vs producir en pico</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    renderAvoidWindows(windows) {
        if (!windows || windows.length === 0) {
            return '';
        }

        return windows.map(window => {
            const date = new Date(window.datetime);
            const dayName = date.toLocaleDateString('es-ES', { weekday: 'short' });
            const dateStr = date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });

            return `
                <div class="window-card avoid">
                    <div class="window-header">
                        <div class="window-time">
                            <span class="window-icon">🔴</span>
                            <span class="window-day">${dayName.toUpperCase()}</span>
                            <span class="window-date">${dateStr}</span>
                            <span class="window-hours">${window.hours}</span>
                        </div>
                        <div class="window-badge avoid">EVITAR</div>
                    </div>
                    <div class="window-content">
                        <div class="window-price danger">
                            <span class="price-label">Precio:</span>
                            <span class="price-value">${Formatters.decimal(window.avg_price, 4)} €/kWh</span>
                        </div>
                        <div class="window-recommendation warning">
                            <div class="rec-icon">⚠️</div>
                            <div class="rec-text">${window.recommendation}</div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    getTariffClass(period) {
        const classes = {
            'P1': 'tariff-punta',
            'P2': 'tariff-llano',
            'P3': 'tariff-valle'
        };
        return classes[period] || '';
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

// CSS Styles for Optimal Windows Component
const optimalWindowsCSS = `
.optimal-windows-container {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.window-summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
}

.summary-stat {
    background: rgba(0, 0, 0, 0.02);
    padding: 1rem;
    border-radius: 8px;
    text-align: center;
}

.summary-stat.success {
    border-left: 4px solid #10b981;
}

.summary-stat.info {
    border-left: 4px solid #3b82f6;
}

.summary-stat.warning {
    border-left: 4px solid #f59e0b;
}

.stat-value {
    font-size: 1.8rem;
    font-weight: bold;
    color: #333;
}

.stat-label {
    font-size: 0.85rem;
    color: #666;
    margin-top: 0.25rem;
}

.windows-section {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.section-title {
    color: #333;
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
}

.window-card {
    background: rgba(0, 0, 0, 0.02);
    border-radius: 10px;
    padding: 1rem;
    border-left: 4px solid #10b981;
    transition: transform 0.2s, box-shadow 0.2s;
}

.window-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.window-card.avoid {
    border-left-color: #dc2626;
}

.window-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.window-time {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 600;
    color: #333;
}

.window-icon {
    font-size: 1.2rem;
}

.window-day {
    font-size: 0.9rem;
    color: #f59e0b;
}

.window-date {
    font-size: 0.85rem;
    color: #666;
}

.window-hours {
    font-size: 1rem;
    color: #333;
    font-weight: bold;
}

.window-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: bold;
    text-transform: uppercase;
}

.window-badge.excellent {
    background: #10b981;
    color: #333;
}

.window-badge.optimal {
    background: #3b82f6;
    color: #333;
}

.window-badge.avoid {
    background: #dc2626;
    color: #333;
}

.window-content {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.window-price {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.95rem;
}

.price-label {
    color: #666;
}

.price-value {
    color: #333;
    font-weight: bold;
    font-size: 1.1rem;
}

.window-price.danger .price-value {
    color: #ef4444;
}

.window-tariff {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.tariff-badge {
    padding: 0.25rem 0.5rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: bold;
}

.tariff-badge.tariff-valle {
    background: #10b981;
    color: #333;
}

.tariff-badge.tariff-llano {
    background: #f59e0b;
    color: #333;
}

.tariff-badge.tariff-punta {
    background: #dc2626;
    color: #333;
}

.duration {
    font-size: 0.85rem;
    color: #666;
}

.window-recommendation {
    display: flex;
    gap: 0.5rem;
    padding: 0.75rem;
    background: rgba(139, 92, 246, 0.15);
    border-radius: 6px;
    border-left: 3px solid #8b5cf6;
}

.window-recommendation.warning {
    background: rgba(239, 68, 68, 0.15);
    border-left-color: #ef4444;
}

.rec-icon {
    color: #8b5cf6;
    font-weight: bold;
}

.rec-text {
    flex: 1;
    font-size: 0.9rem;
    color: #666;
    line-height: 1.4;
}

.window-savings {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: #666;
}

.savings-icon {
    font-size: 1rem;
}

.empty-state, .error-state {
    text-align: center;
    padding: 2rem;
    color: #666;
}

.error-icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    display: block;
}
`;
