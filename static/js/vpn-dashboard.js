// VPN Dashboard JavaScript

let currentHours = 24;

// Initialize dashboard on load
document.addEventListener('DOMContentLoaded', () => {
    console.log('🔐 VPN Dashboard initializing...');
    loadDashboard();

    // Auto-refresh every 30 seconds
    setInterval(loadDashboard, 30000);
});

async function loadDashboard() {
    try {
        await Promise.all([
            loadQuotaStatus(),
            loadDevices(),
            loadAccessLogs(currentHours)
        ]);

        updateTimestamp();
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

async function loadQuotaStatus() {
    try {
        const response = await fetch('/analytics/quota-status');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();

        // Update quota gauge
        const percentage = data.quota_percentage || 0;
        const quotaGauge = document.getElementById('quota-gauge');
        const angle = (percentage / 100) * 360;

        // Change color based on quota usage
        let color = '#10b981'; // green
        if (percentage >= 100) {
            color = '#ef4444'; // red
        } else if (percentage >= 66) {
            color = '#f59e0b'; // orange
        }

        quotaGauge.style.setProperty('--quota-angle', `${angle}deg`);
        quotaGauge.style.background = `conic-gradient(
            ${color} 0deg,
            ${color} ${angle}deg,
            #475569 ${angle}deg,
            #475569 360deg
        )`;

        // Update quota numbers
        document.getElementById('quota-number').textContent = `${data.users_count}/${data.quota_limit}`;
        document.getElementById('quota-available').textContent = data.quota_available;
        document.getElementById('quota-percentage').textContent = `${percentage.toFixed(1)}%`;

        // Update alert
        const alertDiv = document.getElementById('quota-alert');
        if (data.alert) {
            alertDiv.style.display = 'block';
            alertDiv.className = 'quota-alert danger';
            document.getElementById('quota-alert-text').textContent =
                `Cuota EXCEDIDA: ${data.users_count}/${data.quota_limit} usuarios. Considera actualizar a plan de pago.`;
        } else if (data.warning) {
            alertDiv.style.display = 'block';
            alertDiv.className = 'quota-alert warning';
            document.getElementById('quota-alert-text').textContent =
                `Advertencia: Quedan ${data.quota_available} usuarios disponibles.`;
        } else {
            alertDiv.style.display = 'none';
        }

        // Render external users list
        const externalUsersDiv = document.getElementById('external-users-list');
        if (data.external_users && data.external_users.length > 0) {
            externalUsersDiv.innerHTML = `
                <h3 style="margin-bottom: 15px;">Usuarios Externos (cuentan hacia cuota):</h3>
                ${data.external_users.map(user => `
                    <div class="external-user-item">
                        <div class="user-info">
                            <span class="user-email">${user.email}</span>
                            <span class="user-hostname">${user.hostname}</span>
                        </div>
                        <span class="user-status ${user.online ? 'online' : 'offline'}">
                            ${user.online ? '🟢 Online' : '⚪ Offline'}
                        </span>
                    </div>
                `).join('')}
            `;
        } else {
            externalUsersDiv.innerHTML = '';
        }

    } catch (error) {
        console.error('Error loading quota status:', error);
        document.getElementById('quota-number').textContent = 'Error';
    }
}

async function loadDevices() {
    try {
        const response = await fetch('/analytics/devices');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();

        // Update own nodes
        renderDevicesList(
            'own-devices',
            data.own_nodes.devices,
            'own',
            data.own_nodes.count
        );
        document.getElementById('own-count').textContent = `${data.own_nodes.count} dispositivos`;

        // Update shared nodes
        renderDevicesList(
            'shared-devices',
            data.shared_nodes.devices,
            'shared',
            data.shared_nodes.count
        );
        document.getElementById('shared-count').textContent = `${data.shared_nodes.count} dispositivos`;

        // Update external users
        renderDevicesList(
            'external-devices',
            data.external_users.devices,
            'external',
            data.external_users.count
        );
        document.getElementById('external-count').textContent = `${data.external_users.count} dispositivos`;

    } catch (error) {
        console.error('Error loading devices:', error);
        ['own-devices', 'shared-devices', 'external-devices'].forEach(id => {
            document.getElementById(id).innerHTML = '<p class="loading">Error cargando dispositivos</p>';
        });
    }
}

function renderDevicesList(containerId, devices, type, count) {
    const container = document.getElementById(containerId);

    if (!devices || devices.length === 0) {
        container.innerHTML = '<p style="color: #94a3b8; text-align: center;">No hay dispositivos</p>';
        return;
    }

    container.innerHTML = devices.map(device => `
        <div class="device-item ${type}">
            <div class="device-name">
                <span>${device.hostname}</span>
                <span class="device-status ${device.online ? 'online' : 'offline'}">
                    ${device.online ? '●' : '○'}
                </span>
            </div>
            <div class="device-details">
                <span class="device-ip">${device.ip}</span>
                <span>SO: ${device.os}</span>
                ${device.user ? `<span>👤 ${device.user}</span>` : ''}
            </div>
        </div>
    `).join('');
}

async function loadAccessLogs(hours) {
    try {
        const response = await fetch(`/analytics/access-logs?hours=${hours}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();

        // Update summary
        document.getElementById('total-requests').textContent = data.summary.total_requests;
        document.getElementById('unique-users').textContent = data.summary.unique_users;
        document.getElementById('unique-devices').textContent = data.summary.unique_devices;

        // Render logs table
        const tbody = document.getElementById('logs-tbody');

        if (!data.logs || data.logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #94a3b8;">No hay accesos registrados</td></tr>';
            return;
        }

        tbody.innerHTML = data.logs.slice(0, 100).map(log => {
            const timestamp = new Date(log.timestamp);
            const statusClass = log.status >= 200 && log.status < 300 ? 'success' : 'error';
            const methodClass = log.method;

            return `
                <tr>
                    <td class="log-timestamp">${formatTimestamp(timestamp)}</td>
                    <td class="log-user">${log.user || 'unknown'}</td>
                    <td>${log.device || 'unknown'}</td>
                    <td class="log-endpoint">${log.endpoint}</td>
                    <td class="log-method ${methodClass}">${log.method}</td>
                    <td class="log-status ${statusClass}">${log.status}</td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading access logs:', error);
        document.getElementById('logs-tbody').innerHTML =
            '<tr><td colspan="6" style="text-align: center; color: #ef4444;">Error cargando logs</td></tr>';
    }
}

function changeTimeRange() {
    const select = document.getElementById('hours-select');
    currentHours = parseInt(select.value);
    loadAccessLogs(currentHours);
}

function refreshDashboard() {
    console.log('🔄 Refreshing dashboard...');
    loadDashboard();
}

function formatTimestamp(date) {
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    return `${day}/${month} ${hours}:${minutes}:${seconds}`;
}

function updateTimestamp() {
    const now = new Date();
    document.getElementById('last-update').textContent = formatTimestamp(now);
}
