// Main Application - Chocolate Factory Dashboard

class DashboardApp {
    constructor() {
        this.components = {
            heatmap: new WeeklyHeatmap('weeklyHeatmap'),
            alerts: new AlertsComponent('alerts'),
            recommendations: new RecommendationsComponent('recommendations')
            // siarAnalysis removed - Sprint 07 component not loaded in index.html
        };

        this.autoRefreshInterval = null;
        this.autoRefreshDelay = 30000; // 30 seconds
    }

    async init() {
        console.log('🍫 Initializing Chocolate Factory Dashboard...');

        // Initial data load
        await this.loadDashboard();

        // Setup auto-refresh
        this.startAutoRefresh();

        // Setup event listeners
        this.setupEventListeners();

        console.log('✅ Dashboard initialized successfully');
    }

    async loadDashboard() {
        try {
            this.updateSystemStatus('loading');

            const data = await dashboardService.fetchDashboardData();

            this.renderSystemInfo(data.system_status);
            this.renderCurrentInfo(data.current_info);
            this.renderPredictions(data.predictions);
            this.renderAnalytics(data.current_info?.analytics);

            // Render components
            if (data.weekly_forecast) {
                this.components.heatmap.render(data.weekly_forecast);
            }

            if (data.alerts) {
                this.components.alerts.render(data.alerts);
            }

            if (data.recommendations) {
                this.components.recommendations.render(data.recommendations);
            }

            // Sprint 07: SIAR component removed (not loaded in this version)

            this.updateSystemStatus('success');
            this.updateLastUpdateTime();

        } catch (error) {
            console.error('Failed to load dashboard:', error);
            this.updateSystemStatus('error');
            this.showError('Error al cargar el dashboard. Reintentando...');
        }
    }

    renderSystemInfo(systemStatus) {
        const container = document.getElementById('systemInfo');
        if (!systemStatus) {
            container.innerHTML = '<div class="loading">No hay información del sistema</div>';
            return;
        }

        const dataSourcesHTML = Object.entries(systemStatus.data_sources || {})
            .map(([key, value]) => `
                <div class="data-source-item">
                    <span class="data-source-name">${key.toUpperCase()}</span>
                    <span class="data-source-status">${value}</span>
                </div>
            `).join('');

        const featuresHTML = Object.entries(systemStatus.enhanced_features || {})
            .map(([key, value]) => `
                <div class="feature-item">
                    <span class="feature-icon">${value.includes('✅') ? '✅' : '❌'}</span>
                    <span class="feature-text">${key.replace(/_/g, ' ')}</span>
                </div>
            `).join('');

        container.innerHTML = `
            <div class="system-grid">
                <div class="metric">
                    <div class="metric-label">Estado</div>
                    <div class="metric-value status-success">${systemStatus.status || '--'}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Última Actualización</div>
                    <div class="metric-value">${Formatters.time(systemStatus.last_update)}</div>
                </div>
            </div>
            <div style="margin-top: 1rem;">
                <h3 style="color: var(--secondary-color); margin-bottom: 0.5rem;">Fuentes de Datos</h3>
                ${dataSourcesHTML}
            </div>
            <div style="margin-top: 1rem;">
                <h3 style="color: var(--secondary-color); margin-bottom: 0.5rem;">Características Enhanced</h3>
                ${featuresHTML}
            </div>
        `;
    }

    renderCurrentInfo(currentInfo) {
        const container = document.getElementById('currentInfo');
        if (!currentInfo) {
            container.innerHTML = '<div class="loading">No hay información actual disponible</div>';
            return;
        }

        const ree = currentInfo.ree || {};
        const weather = currentInfo.weather || {};
        const factory = currentInfo.factory_state || {};

        container.innerHTML = `
            <div class="current-info-grid">
                <div class="metric info-card">
                    <div class="metric-label">⚡ Precio Energía</div>
                    <div class="metric-value">${ree.price_eur_kwh ? ree.price_eur_kwh.toFixed(4) : '--'}</div>
                    <div class="metric-unit">€/kWh</div>
                </div>
                <div class="metric info-card">
                    <div class="metric-label">📊 Período Tarifa</div>
                    <div class="metric-value">${ree.tariff_period || '--'}</div>
                </div>
                <div class="metric info-card">
                    <div class="metric-label">🌡️ Temperatura</div>
                    <div class="metric-value">${weather.temperature ? weather.temperature.toFixed(1) : '--'}</div>
                    <div class="metric-unit">°C</div>
                </div>
                <div class="metric info-card">
                    <div class="metric-label">💧 Humedad</div>
                    <div class="metric-value">${weather.humidity ? weather.humidity.toFixed(1) : '--'}</div>
                    <div class="metric-unit">%</div>
                </div>
                <div class="metric info-card">
                    <div class="metric-label">🏭 Estado Fábrica</div>
                    <div class="metric-value">${factory.status || '--'}</div>
                </div>
                <div class="metric info-card">
                    <div class="metric-label">🍫 Índice Producción</div>
                    <div class="metric-value">${factory.chocolate_production_index ? factory.chocolate_production_index.toFixed(1) : '--'}</div>
                </div>
            </div>
        `;
    }

    renderPredictions(predictions) {
        const container = document.getElementById('predictions');
        if (!predictions) {
            container.innerHTML = '<div class="loading">No hay predicciones disponibles</div>';
            return;
        }

        const enhanced = predictions.enhanced_ml || {};
        const direct = predictions.direct_ml || {};

        container.innerHTML = `
            <div class="predictions-grid">
                <div class="metric success-card">
                    <div class="metric-label">🎯 Score Optimización</div>
                    <div class="metric-value">${enhanced.energy_optimization_score || direct.energy_optimization_score || '--'}</div>
                    <div class="metric-unit">/100</div>
                </div>
                <div class="metric success-card">
                    <div class="metric-label">🏭 Nivel Producción</div>
                    <div class="metric-value">${Formatters.recommendationLevel(enhanced.production_level || direct.production_recommendation || '--')}</div>
                </div>
                <div class="metric success-card">
                    <div class="metric-label">💰 Costo Estimado</div>
                    <div class="metric-value">${enhanced.estimated_cost_per_kg ? enhanced.estimated_cost_per_kg.toFixed(2) : '--'}</div>
                    <div class="metric-unit">€/kg</div>
                </div>
                <div class="metric info-card">
                    <div class="metric-label">🤖 Modelo Activo</div>
                    <div class="metric-value">${predictions.model_version || 'Enhanced ML'}</div>
                </div>
            </div>
            ${enhanced.human_recommendation ? `
                <div style="margin-top: 1rem; padding: 1rem; background: rgba(139, 111, 71, 0.1); border-radius: 8px; border-left: 4px solid var(--secondary-color);">
                    <strong>💡 Recomendación:</strong> ${enhanced.human_recommendation}
                </div>
            ` : ''}
        `;
    }

    renderAnalytics(analytics) {
        const container = document.getElementById('analytics');
        if (!analytics) {
            container.innerHTML = '<div class="loading">No hay datos de análisis disponibles</div>';
            return;
        }

        const factoryMetrics = analytics.factory_metrics || {};
        const priceAnalysis = analytics.price_analysis || {};

        container.innerHTML = `
            <div class="analytics-grid">
                <div class="metric warning-card">
                    <div class="metric-label">📊 Costo Total Histórico</div>
                    <div class="metric-value">${Formatters.largePrice(factoryMetrics.total_cost)}</div>
                </div>
                <div class="metric info-card">
                    <div class="metric-label">⚡ Consumo Total</div>
                    <div class="metric-value">${factoryMetrics.total_consumption_mwh ? factoryMetrics.total_consumption_mwh.toFixed(2) : '--'}</div>
                    <div class="metric-unit">MWh</div>
                </div>
                <div class="metric success-card">
                    <div class="metric-label">💰 Precio Mínimo</div>
                    <div class="metric-value">${priceAnalysis.min_price_eur_kwh ? priceAnalysis.min_price_eur_kwh.toFixed(4) : '--'}</div>
                    <div class="metric-unit">€/kWh</div>
                </div>
                <div class="metric danger-card">
                    <div class="metric-label">💰 Precio Máximo</div>
                    <div class="metric-value">${priceAnalysis.max_price_eur_kwh ? priceAnalysis.max_price_eur_kwh.toFixed(4) : '--'}</div>
                    <div class="metric-unit">€/kWh</div>
                </div>
            </div>
        `;
    }

    updateSystemStatus(status) {
        const indicator = document.getElementById('systemStatus');
        if (!indicator) {
            console.warn('systemStatus element not found, skipping status update');
            return;
        }
        const dot = indicator.querySelector('.status-dot');
        const text = indicator.querySelector('.status-text');

        dot.classList.remove('error', 'warning');

        switch (status) {
            case 'success':
                text.textContent = '✅ Operativo';
                break;
            case 'loading':
                text.textContent = '⏳ Cargando...';
                break;
            case 'error':
                text.textContent = '❌ Error';
                dot.classList.add('error');
                break;
            default:
                text.textContent = 'Desconocido';
        }
    }

    updateLastUpdateTime() {
        const element = document.getElementById('lastUpdate');
        const now = new Date();
        element.textContent = now.toLocaleString('es-ES', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    startAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }

        this.autoRefreshInterval = setInterval(() => {
            console.log('🔄 Auto-refresh triggered');
            this.loadDashboard();
        }, this.autoRefreshDelay);

        console.log(`✅ Auto-refresh enabled (${this.autoRefreshDelay / 1000}s)`);
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
            console.log('❌ Auto-refresh disabled');
        }
    }

    setupEventListeners() {
        // Handle visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopAutoRefresh();
            } else {
                this.loadDashboard();
                this.startAutoRefresh();
            }
        });

        // Manual refresh on click (header)
        document.querySelector('.dashboard-header').addEventListener('click', () => {
            console.log('🔄 Manual refresh triggered');
            this.loadDashboard();
        });
    }

    showError(message) {
        // Could implement a toast notification here
        console.error('Dashboard Error:', message);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new DashboardApp();
    app.init();
});
