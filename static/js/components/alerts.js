// Alerts Component

class AlertsComponent {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }

    render(alerts) {
        if (!alerts || alerts.length === 0) {
            this.container.innerHTML = this.renderNoAlerts();
            return;
        }

        const alertsHTML = `
            <div class="alerts-container">
                ${alerts.map(alert => this.renderAlert(alert)).join('')}
            </div>
        `;

        this.container.innerHTML = alertsHTML;
    }

    renderAlert(alert) {
        const icon = this.getAlertIcon(alert.type);
        const priorityClass = alert.priority ? `priority-${alert.priority}` : '';

        return `
            <div class="alert ${alert.type} ${priorityClass}">
                <div class="alert-icon">${icon}</div>
                <div class="alert-content">
                    <div class="alert-title">${alert.title}</div>
                    <div class="alert-message">${alert.message}</div>
                    ${alert.timestamp ? `<div class="alert-timestamp">${Formatters.datetime(alert.timestamp)}</div>` : ''}
                </div>
            </div>
        `;
    }

    renderNoAlerts() {
        return `
            <div class="no-alerts">
                <div class="no-alerts-icon">✅</div>
                <div class="no-alerts-message">No hay alertas activas</div>
            </div>
        `;
    }

    getAlertIcon(type) {
        const icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'danger': '❌',
            'error': '❌'
        };
        return icons[type] || 'ℹ️';
    }
}
