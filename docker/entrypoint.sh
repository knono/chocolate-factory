#!/bin/bash
# =============================================================================
# CHOCOLATE FACTORY - ENTRYPOINT SCRIPT
# =============================================================================
# Ensures proper permissions for logs directory (bind mounts + named volumes)
# Compatible with CI/CD runners and local development
# =============================================================================

set -e

# Function to setup log file permissions
setup_logs() {
    local log_file="/app/logs/fastapi.log"

    # Ensure logs directory exists
    if [ ! -d "/app/logs" ]; then
        mkdir -p /app/logs 2>/dev/null || {
            echo "Warning: Could not create /app/logs directory"
            return 1
        }
    fi

    # Remove old log file if it has wrong permissions
    if [ -f "$log_file" ]; then
        if ! touch "$log_file" 2>/dev/null; then
            echo "Warning: Existing log file not writable, attempting removal..."
            rm -f "$log_file" 2>/dev/null || {
                echo "Error: Cannot remove old log file, logging may fail"
                return 1
            }
        fi
    fi

    # Create fresh log file with proper permissions
    touch "$log_file" 2>/dev/null || {
        echo "Warning: Could not create log file (may require host permissions)"
        return 1
    }

    # Set universal write permissions (works for bind mounts and named volumes)
    chmod 666 "$log_file" 2>/dev/null || {
        echo "Warning: Could not set log file permissions (may require host permissions)"
    }

    echo "✅ Log file ready: $log_file"
    return 0
}

# Function to setup domain directories permissions
setup_domain_permissions() {
    # Fix permissions for newly added domain modules (machinery, etc.)
    if [ -d "/app/domain/machinery" ]; then
        chmod -R 755 /app/domain/machinery 2>/dev/null || {
            echo "Warning: Could not set machinery module permissions"
        }
    fi
    return 0
}

# Setup logging
setup_logs

# Setup domain permissions (for new modules)
setup_domain_permissions

# Execute the main command (uvicorn)
exec "$@"
