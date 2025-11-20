// Weekly Heatmap Component

class WeeklyHeatmap {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }

    render(forecastData) {
        if (!forecastData || !forecastData.days || forecastData.days.length === 0) {
            this.container.innerHTML = '<div class="loading">No hay datos de pronóstico disponibles</div>';
            return;
        }

        const heatmapHTML = `
            <div class="heatmap-container">
                <div class="heatmap-grid">
                    ${forecastData.days.map(day => this.renderDay(day)).join('')}
                </div>
                ${this.renderLegend()}
            </div>
        `;

        this.container.innerHTML = heatmapHTML;
    }

    renderDay(day) {
        const priceClass = this.getPriceClass(day.price_eur_kwh);
        const recClass = this.getRecommendationClass(day.production_recommendation);

        return `
            <div class="heatmap-day ${priceClass}" data-day="${day.date}">
                <div class="heatmap-day-header">
                    <div class="heatmap-day-name">${this.getDayName(day.date)}</div>
                    <div class="heatmap-day-date">${Formatters.date(day.date)}</div>
                </div>
                <div class="heatmap-day-content">
                    <div class="heatmap-price">
                        ${day.price_eur_kwh ? Formatters.decimal(day.price_eur_kwh, 3) : '--'}
                        <span class="heatmap-price-unit">€/kWh</span>
                    </div>
                    ${day.weather ? this.renderWeather(day.weather) : ''}
                    <div class="heatmap-recommendation">
                        ${Formatters.recommendationLevel(day.production_recommendation)}
                    </div>
                </div>
            </div>
        `;
    }

    renderWeather(weather) {
        return `
            <div class="heatmap-weather">
                <div class="heatmap-weather-item">
                    <span>🌡️ Temp:</span>
                    <span>${Formatters.temperature(weather.temperature)}</span>
                </div>
                <div class="heatmap-weather-item">
                    <span>💧 Humedad:</span>
                    <span>${Formatters.percentage(weather.humidity)}</span>
                </div>
            </div>
        `;
    }

    renderLegend() {
        return `
            <div class="heatmap-legend">
                <div class="heatmap-legend-item">
                    <div class="heatmap-legend-color optimal"></div>
                    <span class="heatmap-legend-label">Óptimo (&lt;0.10 €/kWh)</span>
                </div>
                <div class="heatmap-legend-item">
                    <div class="heatmap-legend-color moderate"></div>
                    <span class="heatmap-legend-label">Moderado (0.10-0.15 €/kWh)</span>
                </div>
                <div class="heatmap-legend-item">
                    <div class="heatmap-legend-color expensive"></div>
                    <span class="heatmap-legend-label">Caro (0.15-0.20 €/kWh)</span>
                </div>
                <div class="heatmap-legend-item">
                    <div class="heatmap-legend-color very-expensive"></div>
                    <span class="heatmap-legend-label">Muy Caro (&gt;0.20 €/kWh)</span>
                </div>
            </div>
        `;
    }

    getPriceClass(price) {
        if (!price) return '';
        if (price < 0.10) return 'optimal';
        if (price < 0.15) return 'moderate';
        if (price < 0.20) return 'expensive';
        return 'very-expensive';
    }

    getRecommendationClass(rec) {
        const recMap = {
            'OPTIMAL': 'success',
            'MODERATE': 'info',
            'REDUCED': 'warning',
            'HALT': 'danger'
        };
        return recMap[rec] || '';
    }

    getDayName(dateString) {
        const date = new Date(dateString);
        const days = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
        return days[date.getDay()];
    }
}
