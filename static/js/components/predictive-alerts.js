// Predictive Alerts Component - Sprint 09
// Displays real-time predictive alerts for next 24-48h

class PredictiveAlertsComponent {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.data = null;
    }

    async render() {
        if (!this.container) {
            console.error('PredictiveAlerts container not found');
            return;
        }

        try {
            // Fetch predictive alerts
            this.data = await apiClient.get('/insights/alerts');

            if (this.data.status === 'error') {
                this.renderError(this.data.message);
                return;
            }

            this.renderContent();

        } catch (error) {
            console.error('Failed to load predictive alerts:', error);
            this.renderError('Error al cargar alertas predictivas');
        }
    }

    renderContent() {
        const { alerts, active_count, high_severity_count } = this.data;

        const html = `
            <div class="predictive-alerts-container">
                <!-- Alert Summary -->
                <div class="alerts-summary">
                    <div class="summary-badge ${high_severity_count > 0 ? 'high-severity' : 'normal'}">
                        ${active_count} ${active_count === 1 ? 'Alerta Activa' : 'Alertas Activas'}
                        ${high_severity_count > 0 ? `(${high_severity_count} crítica${high_severity_count > 1 ? 's' : ''})` : ''}
                    </div>
                </div>

                <!-- Alerts List -->
                <div class="alerts-list">
                    ${alerts && alerts.length > 0
                        ? alerts.map(alert => this.renderAlert(alert)).join('')
                        : this.renderNoAlerts()
                    }
                </div>
            </div>
        `;

        this.container.innerHTML = html;
    }

    renderAlert(alert) {
        const severityClass = this.getSeverityClass(alert.severity);
        const severityLabel = this.getSeverityLabel(alert.severity);

        return `
            <div class="alert-card ${severityClass}">
                <div class="alert-header">
                    <div class="alert-icon">${alert.icon}</div>
                    <div class="alert-title">
                        <div class="alert-type">${this.getAlertTypeLabel(alert.type)}</div>
                        <div class="alert-severity-badge ${severityClass}">${severityLabel}</div>
                    </div>
                </div>
                <div class="alert-content">
                    <div class="alert-message">${alert.message}</div>
                    <div class="alert-recommendation">
                        <div class="rec-label">💡 Recomendación:</div>
                        <div class="rec-text">${alert.recommendation}</div>
                    </div>
                </div>
                <div class="alert-footer">
                    <div class="alert-time">${this.formatDateTime(alert.datetime)}</div>
                </div>
            </div>
        `;
    }

    renderNoAlerts() {
        return `
            <div class="no-alerts-state">
                <div class="no-alerts-icon">✅</div>
                <div class="no-alerts-message">No hay alertas activas</div>
                <div class="no-alerts-submessage">Las condiciones son favorables para la producción</div>
            </div>
        `;
    }

    getAlertTypeLabel(type) {
        const labels = {
            'price_spike': 'Pico de Precio Inminente',
            'heat_wave': 'Ola de Calor',
            'optimal_window': 'Ventana Óptima Abierta',
            'production_boost': 'Oportunidad Producción Intensiva'
        };
        return labels[type] || type;
    }

    getSeverityClass(severity) {
        return `severity-${severity}`;
    }

    getSeverityLabel(severity) {
        const labels = {
            'high': 'ALTA',
            'medium': 'MEDIA',
            'info': 'INFO'
        };
        return labels[severity] || severity.toUpperCase();
    }

    formatDateTime(datetime) {
        if (!datetime) return '--';
        const date = new Date(datetime);
        return date.toLocaleString('es-ES', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
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

// CSS Styles for Predictive Alerts Component
const predictiveAlertsCSS = `
.predictive-alerts-container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.alerts-summary {
    text-align: center;
    margin-bottom: 0.5rem;
}

.summary-badge {
    display: inline-block;
    padding: 0.5rem 1.5rem;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.95rem;
    background: rgba(59, 130, 246, 0.2);
    border: 2px solid rgba(59, 130, 246, 0.4);
    color: #333;
}

.summary-badge.high-severity {
    background: rgba(239, 68, 68, 0.2);
    border-color: rgba(239, 68, 68, 0.4);
    animation: pulse-alert 2s ease-in-out infinite;
}

@keyframes pulse-alert {
    0%, 100% {
        opacity: 1;
    }
    50% {
        opacity: 0.7;
    }
}

.alerts-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.alert-card {
    background: rgba(0, 0, 0, 0.02);
    border-radius: 10px;
    padding: 1rem;
    border-left: 4px solid #3b82f6;
    transition: transform 0.2s, box-shadow 0.2s;
}

.alert-card:hover {
    transform: translateX(4px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.alert-card.severity-high {
    border-left-color: #ef4444;
    background: rgba(239, 68, 68, 0.08);
}

.alert-card.severity-medium {
    border-left-color: #f59e0b;
    background: rgba(245, 158, 11, 0.08);
}

.alert-card.severity-info {
    border-left-color: #3b82f6;
    background: rgba(59, 130, 246, 0.08);
}

.alert-header {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1rem;
}

.alert-icon {
    font-size: 2rem;
    flex-shrink: 0;
}

.alert-title {
    flex: 1;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
}

.alert-type {
    font-weight: 700;
    font-size: 1.05rem;
    color: #333;
}

.alert-severity-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: bold;
}

.alert-severity-badge.severity-high {
    background: #ef4444;
    color: #333;
}

.alert-severity-badge.severity-medium {
    background: #f59e0b;
    color: #333;
}

.alert-severity-badge.severity-info {
    background: #3b82f6;
    color: #333;
}

.alert-content {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.alert-message {
    font-size: 0.95rem;
    color: #333;
    line-height: 1.5;
    font-weight: 500;
}

.alert-recommendation {
    background: rgba(139, 92, 246, 0.15);
    padding: 0.75rem;
    border-radius: 6px;
    border-left: 3px solid #8b5cf6;
}

.rec-label {
    font-size: 0.8rem;
    color: #8b5cf6;
    font-weight: 600;
    margin-bottom: 0.25rem;
}

.rec-text {
    font-size: 0.9rem;
    color: #666;
    line-height: 1.4;
}

.alert-footer {
    margin-top: 0.75rem;
    padding-top: 0.75rem;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.alert-time {
    font-size: 0.8rem;
    color: #666;
    text-align: right;
}

.no-alerts-state {
    text-align: center;
    padding: 3rem 1rem;
    background: rgba(16, 185, 129, 0.1);
    border-radius: 10px;
    border: 2px dashed rgba(16, 185, 129, 0.3);
}

.no-alerts-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}

.no-alerts-message {
    font-size: 1.2rem;
    font-weight: 600;
    color: #10b981;
    margin-bottom: 0.5rem;
}

.no-alerts-submessage {
    font-size: 0.9rem;
    color: #666;
}
`;
