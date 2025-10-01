// Dashboard Service - Main data fetching service

class DashboardService {
    constructor() {
        this.data = null;
        this.lastUpdate = null;
        this.updateCallbacks = [];
    }

    // Fetch complete dashboard data
    async fetchDashboardData() {
        try {
            const data = await apiClient.get('/dashboard/complete');
            this.data = data;
            this.lastUpdate = new Date();
            this.notifyCallbacks(data);
            return data;
        } catch (error) {
            console.error('Failed to fetch dashboard data:', error);
            throw error;
        }
    }

    // Register callback for data updates
    onUpdate(callback) {
        this.updateCallbacks.push(callback);
    }

    // Notify all callbacks
    notifyCallbacks(data) {
        this.updateCallbacks.forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error('Callback error:', error);
            }
        });
    }

    // Get current data without fetching
    getCurrentData() {
        return this.data;
    }

    // Get last update time
    getLastUpdate() {
        return this.lastUpdate;
    }
}

// Export singleton
const dashboardService = new DashboardService();
