// Formatters Utility - Format data for display

const Formatters = {
    // Format price
    price(value, currency = '€') {
        if (value === null || value === undefined) return '--';
        return `${value.toFixed(4)} ${currency}/kWh`;
    },

    // Format large price
    largePrice(value, currency = '€') {
        if (value === null || value === undefined) return '--';
        return `${value.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
    },

    // Format temperature
    temperature(value) {
        if (value === null || value === undefined) return '--';
        return `${value.toFixed(1)}°C`;
    },

    // Format percentage
    percentage(value) {
        if (value === null || value === undefined) return '--';
        return `${value.toFixed(1)}%`;
    },

    // Format datetime
    datetime(dateString) {
        if (!dateString) return '--';
        const date = new Date(dateString);
        return date.toLocaleString('es-ES', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // Format date only
    date(dateString) {
        if (!dateString) return '--';
        const date = new Date(dateString);
        return date.toLocaleDateString('es-ES', {
            weekday: 'short',
            day: '2-digit',
            month: 'short'
        });
    },

    // Format time only
    time(dateString) {
        if (!dateString) return '--';
        const date = new Date(dateString);
        return date.toLocaleTimeString('es-ES', {
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // Format number with units
    withUnit(value, unit) {
        if (value === null || value === undefined) return '--';
        return `${value} ${unit}`;
    },

    // Format status
    status(status) {
        const statusMap = {
            'healthy': '✅ Operativo',
            'degraded': '⚠️ Degradado',
            'unhealthy': '❌ Error',
            'connected': '✅ Conectado',
            'disconnected': '❌ Desconectado'
        };
        return statusMap[status] || status;
    },

    // Format recommendation level
    recommendationLevel(level) {
        const levelMap = {
            'OPTIMAL': '🟢 PRODUCCIÓN ÓPTIMA',
            'MODERATE': '🟡 PRODUCCIÓN MODERADA',
            'REDUCED': '🟠 PRODUCCIÓN REDUCIDA',
            'HALT': '🔴 PRODUCCIÓN MÍNIMA'
        };
        return levelMap[level] || level;
    },

    // Truncate text
    truncate(text, maxLength = 50) {
        if (!text) return '--';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },

    // Format large numbers
    largeNumber(value) {
        if (value === null || value === undefined) return '--';
        if (value >= 1000000) {
            return `${(value / 1000000).toFixed(1)}M`;
        }
        if (value >= 1000) {
            return `${(value / 1000).toFixed(1)}k`;
        }
        return value.toString();
    }
};
