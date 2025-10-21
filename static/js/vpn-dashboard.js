/**
 * Tailscale Health Monitoring Dashboard (Sprint 13 - Pivotado)
 *
 * Funcionalidad:
 * - Muestra salud de nodos Tailscale críticos
 * - Uptime tracking y disponibilidad
 * - Alertas proactivas de nodos caídos
 * - Auto-refresh cada 30 segundos
 */

// Global state
let refreshInterval = null;
const REFRESH_INTERVAL_MS = 30000; // 30 segundos

// Logs pagination state
let currentPage = 1;
const PAGE_SIZE = 20;
let currentSeverityFilter = '';
let currentEventTypeFilter = '';

// Initialize dashboard on load
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initializing Tailscale Health Monitoring Dashboard...');
    loadDashboard();
    startAutoRefresh();
});

/**
 * Main dashboard loader
 */
async function loadDashboard() {
    try {
        console.log('📊 Loading health monitoring data...');

        // Fetch data in parallel
        const [summary, criticalNodes, alerts, allNodes] = await Promise.all([
            fetchHealthSummary(),
            fetchCriticalNodes(),
            fetchAlerts(),
            fetchAllNodes()
        ]);

        // Render all sections
        renderHealthSummary(summary, criticalNodes);
        renderCriticalNodesGrid(criticalNodes);
        renderAlerts(alerts);
        renderNodesTable(allNodes);

        // Load logs
        await loadLogs(currentPage);

        updateTimestamp();

        console.log('✅ Dashboard loaded successfully');

    } catch (error) {
        console.error('❌ Error loading dashboard:', error);
        showError(error.message);
    }
}

/**
 * Manual refresh button
 */
function refreshDashboard() {
    console.log('🔄 Manual refresh triggered');
    loadDashboard();
}

/**
 * Auto-refresh setup
 */
function startAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }

    refreshInterval = setInterval(() => {
        console.log('⏰ Auto-refresh triggered');
        loadDashboard();
    }, REFRESH_INTERVAL_MS);

    console.log(`✅ Auto-refresh started (${REFRESH_INTERVAL_MS / 1000}s interval)`);
}

// ============ API CALLS ============

async function fetchHealthSummary() {
    const response = await fetch('/health-monitoring/summary');
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    return await response.json();
}

async function fetchCriticalNodes() {
    const response = await fetch('/health-monitoring/critical');
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    return await response.json();
}

async function fetchAlerts() {
    const response = await fetch('/health-monitoring/alerts');
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    return await response.json();
}

async function fetchAllNodes() {
    // Fetch only project nodes by default (production, development, git)
    const response = await fetch('/health-monitoring/nodes?project_only=true');
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    return await response.json();
}

// ============ RENDER FUNCTIONS ============

/**
 * Render health summary card with gauge
 */
function renderHealthSummary(summary, criticalNodes) {
    const healthPercentage = criticalNodes.health_percentage || 0;
    const healthStatus = criticalNodes.status || 'unknown';

    // Update gauge
    const gaugeEl = document.getElementById('health-gauge');
    const percentageEl = document.getElementById('health-percentage');
    const statusEl = document.getElementById('health-status');
    const criticalOnlineEl = document.getElementById('critical-online');
    const totalOnlineEl = document.getElementById('total-online');
    const alertEl = document.getElementById('health-alert');
    const alertTextEl = document.getElementById('health-alert-text');

    // Set percentage text
    if (percentageEl) {
        percentageEl.textContent = `${healthPercentage.toFixed(0)}%`;
    }

    // Set gauge color based on health
    if (gaugeEl) {
        gaugeEl.className = 'gauge-circle';
        if (healthStatus === 'healthy') {
            gaugeEl.classList.add('gauge-healthy');
        } else if (healthStatus === 'degraded') {
            gaugeEl.classList.add('gauge-degraded');
        } else {
            gaugeEl.classList.add('gauge-critical');
        }
    }

    // Set status badge
    if (statusEl) {
        statusEl.className = 'stat-value status-badge';
        if (healthStatus === 'healthy') {
            statusEl.classList.add('status-healthy');
            statusEl.textContent = '🟢 Healthy';
        } else if (healthStatus === 'degraded') {
            statusEl.classList.add('status-degraded');
            statusEl.textContent = '🟡 Degraded';
        } else {
            statusEl.classList.add('status-critical');
            statusEl.textContent = '🔴 Critical';
        }
    }

    // Set critical nodes count
    if (criticalOnlineEl) {
        criticalOnlineEl.textContent = `${criticalNodes.online}/${criticalNodes.total_critical}`;
    }

    // Set total network count
    if (totalOnlineEl) {
        totalOnlineEl.textContent = `${summary.online_nodes}/${summary.total_nodes}`;
    }

    // Show alert if health is not 100%
    if (alertEl && alertTextEl) {
        if (healthPercentage < 100) {
            const offlineCount = criticalNodes.total_critical - criticalNodes.online;
            alertTextEl.textContent = `${offlineCount} nodo(s) crítico(s) offline. Revisar conectividad Tailscale.`;
            alertEl.style.display = 'block';
        } else {
            alertEl.style.display = 'none';
        }
    }
}

/**
 * Render critical nodes grid (production, development, git)
 */
function renderCriticalNodesGrid(criticalNodes) {
    const nodes = criticalNodes.nodes || [];

    // Group by node_type
    const production = nodes.filter(n => n.node_type === 'production');
    const development = nodes.filter(n => n.node_type === 'development');
    const git = nodes.filter(n => n.node_type === 'git');

    // Render each category
    renderNodesList('production-nodes', production, 'production-count');
    renderNodesList('development-nodes', development, 'development-count');
    renderNodesList('git-nodes', git, 'git-count');
}

function renderNodesList(containerId, nodes, countId) {
    const container = document.getElementById(containerId);
    const countEl = document.getElementById(countId);

    if (!container) return;

    // Update count
    if (countEl) {
        countEl.textContent = `${nodes.length} nodo${nodes.length !== 1 ? 's' : ''}`;
    }

    // Render nodes
    if (nodes.length === 0) {
        container.innerHTML = '<div class="no-nodes">Sin nodos</div>';
        return;
    }

    container.innerHTML = nodes.map(node => {
        const statusIcon = node.online ? '🟢' : '🔴';
        const statusClass = node.online ? 'status-online' : 'status-offline';
        const lastSeen = node.online ? 'Conectado' : (node.last_seen ? formatTimestamp(node.last_seen) : 'N/A');

        return `
            <div class="node-item ${statusClass}">
                <div class="node-header">
                    <span class="node-status">${statusIcon}</span>
                    <span class="node-hostname">${node.hostname}</span>
                </div>
                <div class="node-details">
                    <div class="node-detail">IP: ${node.ip}</div>
                    <div class="node-detail">Última: ${lastSeen}</div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Render alerts section
 */
function renderAlerts(alerts) {
    const alertsList = document.getElementById('alerts-list');
    const criticalAlertsEl = document.getElementById('critical-alerts');
    const warningAlertsEl = document.getElementById('warning-alerts');
    const okStatusEl = document.getElementById('ok-status');

    const activeAlerts = alerts.active_alerts || [];
    const criticalCount = activeAlerts.filter(a => a.severity === 'critical').length;
    const warningCount = activeAlerts.filter(a => a.severity === 'warning').length;

    // Update summary counts
    if (criticalAlertsEl) criticalAlertsEl.textContent = criticalCount;
    if (warningAlertsEl) warningAlertsEl.textContent = warningCount;
    if (okStatusEl) okStatusEl.textContent = activeAlerts.length === 0 ? '✅' : '0';

    // Render alerts list
    if (!alertsList) return;

    if (activeAlerts.length === 0) {
        alertsList.innerHTML = '<div class="no-alerts">✅ No hay alertas activas</div>';
        return;
    }

    alertsList.innerHTML = activeAlerts.map(alert => {
        const severityIcon = alert.severity === 'critical' ? '🔴' : '⚠️';
        const severityClass = alert.severity === 'critical' ? 'alert-critical' : 'alert-warning';

        return `
            <div class="alert-item ${severityClass}">
                <div class="alert-header">
                    <span class="alert-icon">${severityIcon}</span>
                    <span class="alert-title">${alert.hostname} - ${alert.node_type}</span>
                </div>
                <div class="alert-message">${alert.message}</div>
                <div class="alert-action">💡 ${alert.action}</div>
                ${alert.last_seen ? `<div class="alert-timestamp">Última vez visto: ${formatTimestamp(alert.last_seen)}</div>` : ''}
            </div>
        `;
    }).join('');
}

/**
 * Render detailed nodes table
 */
function renderNodesTable(nodesData) {
    const tbody = document.getElementById('nodes-tbody');
    if (!tbody) return;

    const nodes = nodesData.nodes || [];

    if (nodes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem; opacity: 0.7;">No hay nodos disponibles</td></tr>';
        return;
    }

    tbody.innerHTML = nodes.map(node => {
        const statusBadge = node.online
            ? '<span class="badge badge-online">🟢 ONLINE</span>'
            : '<span class="badge badge-offline">🔴 OFFLINE</span>';

        const typeEmoji = node.node_type === 'production' ? '🏭'
                       : node.node_type === 'development' ? '🔧'
                       : node.node_type === 'git' ? '📦' : '💻';

        const lastSeen = node.online ? 'Conectado ahora' : (node.last_seen ? formatTimestamp(node.last_seen) : 'Desconocido');

        return `
            <tr>
                <td>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span>${typeEmoji}</span>
                        <strong>${node.hostname}</strong>
                    </div>
                </td>
                <td style="text-align: center;">${statusBadge}</td>
                <td style="font-family: monospace; font-size: 0.9rem;">${node.ip}</td>
                <td style="text-transform: capitalize;">${node.node_type}</td>
                <td style="font-size: 0.9rem;">${node.os || 'N/A'}</td>
                <td style="text-align: right; font-size: 0.9rem;">${lastSeen}</td>
            </tr>
        `;
    }).join('');
}

// ============ UTILITY FUNCTIONS ============

function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
}

function updateTimestamp() {
    const lastUpdateEl = document.getElementById('last-update');
    if (lastUpdateEl) {
        lastUpdateEl.textContent = new Date().toLocaleTimeString('es-ES');
    }
}

function showError(message) {
    console.error('Error:', message);
    // You could add a toast notification here
    alert(`Error cargando dashboard: ${message}`);
}

// ============ LOGS FUNCTIONS ============

async function loadLogs(page = 1) {
    try {
        const params = new URLSearchParams({
            page: page,
            page_size: PAGE_SIZE
        });

        if (currentSeverityFilter) params.append('severity', currentSeverityFilter);
        if (currentEventTypeFilter) params.append('event_type', currentEventTypeFilter);

        const response = await fetch(`/health-monitoring/logs?${params.toString()}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        renderLogs(data);

    } catch (error) {
        console.error('Error loading logs:', error);
        document.getElementById('logs-list').innerHTML = `
            <div style="text-align: center; padding: 2rem; color: #ef4444;">
                ⚠️ Error cargando logs: ${error.message}
            </div>
        `;
    }
}

function renderLogs(data) {
    const logsList = document.getElementById('logs-list');
    const { logs, pagination, summary } = data;

    // Update summary
    document.getElementById('logs-total').textContent = summary.total;
    document.getElementById('logs-critical').textContent = summary.critical;
    document.getElementById('logs-warning').textContent = summary.warning;
    document.getElementById('logs-ok').textContent = summary.ok;

    // Render logs
    if (logs.length === 0) {
        logsList.innerHTML = '<div style="text-align: center; padding: 2rem; opacity: 0.7;">No hay eventos para mostrar</div>';
        return;
    }

    logsList.innerHTML = logs.map(log => {
        const severityIcon = log.severity === 'critical' ? '🔴'
                           : log.severity === 'warning' ? '⚠️' : '✅';

        const timestamp = new Date(log.timestamp).toLocaleString('es-ES', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        return `
            <div class="log-entry severity-${log.severity}">
                <div class="log-header">
                    <span class="log-timestamp">${severityIcon} ${timestamp}</span>
                    <span class="log-event-type">${log.event_type.replace('_', ' ')}</span>
                </div>
                <div class="log-node">${log.hostname} (${log.node_type})</div>
                <div class="log-message">${log.message}</div>
            </div>
        `;
    }).join('');

    // Update pagination controls
    currentPage = pagination.page;
    document.getElementById('page-info').textContent = `Página ${pagination.page} de ${pagination.total_pages}`;
    document.getElementById('prev-page').disabled = !pagination.has_prev;
    document.getElementById('next-page').disabled = !pagination.has_next;
}

function nextPage() {
    loadLogs(currentPage + 1);
}

function previousPage() {
    loadLogs(currentPage - 1);
}

function filterLogs() {
    currentSeverityFilter = document.getElementById('severity-filter').value;
    currentEventTypeFilter = document.getElementById('event-type-filter').value;
    currentPage = 1; // Reset to first page
    loadLogs(1);
}

console.log('✅ VPN Dashboard script loaded');
