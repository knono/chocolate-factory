// Recommendations Component

class RecommendationsComponent {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }

    render(recommendations) {
        if (!recommendations) {
            this.container.innerHTML = '<div class="loading">No hay recomendaciones disponibles</div>';
            return;
        }

        const recsHTML = `
            <div class="recommendations-container">
                ${this.renderSection('Producción', recommendations.production)}
                ${this.renderSection('Energía', recommendations.energy)}
                ${this.renderSection('Operacional', recommendations.operational)}
                ${recommendations.summary ? this.renderSummary(recommendations.summary) : ''}
            </div>
        `;

        this.container.innerHTML = recsHTML;
    }

    renderSection(title, items) {
        if (!items || items.length === 0) return '';

        return `
            <div class="recommendation-section">
                <h3 class="recommendation-section-title">💡 ${title}</h3>
                <ul class="recommendation-list">
                    ${items.map(item => `
                        <li class="recommendation-item">
                            <span class="recommendation-icon">▸</span>
                            <span class="recommendation-text">${item}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
    }

    renderSummary(summary) {
        return `
            <div class="recommendation-summary">
                <h3 class="recommendation-section-title">📋 Resumen</h3>
                <div class="recommendation-summary-content">
                    ${summary}
                </div>
            </div>
        `;
    }
}

// Add CSS for recommendations
const recommendationsCSS = `
.recommendations-container {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
}

.recommendation-section {
    background-color: rgba(255, 255, 255, 0.05);
    padding: var(--spacing-md);
    border-radius: var(--border-radius);
}

.recommendation-section-title {
    font-size: 1.1rem;
    margin-bottom: var(--spacing-md);
    color: var(--secondary-color);
}

.recommendation-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.recommendation-item {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.recommendation-item:last-child {
    border-bottom: none;
}

.recommendation-icon {
    color: var(--secondary-color);
    font-weight: bold;
}

.recommendation-text {
    flex: 1;
    line-height: 1.5;
}

.recommendation-summary {
    background: linear-gradient(135deg, rgba(111, 78, 55, 0.1), rgba(139, 111, 71, 0.1));
    padding: var(--spacing-md);
    border-radius: var(--border-radius);
    border-left: 4px solid var(--secondary-color);
}

.recommendation-summary-content {
    line-height: 1.6;
    color: var(--text-secondary);
}
`;
