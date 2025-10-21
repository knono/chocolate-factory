#!/bin/bash
# Tailscale HTTP Proxy Server
# Simple HTTP server that exposes tailscale commands via HTTP
# Runs on localhost:8765 (only accessible within sidecar container)

PORT=8765
HANDLER_SCRIPT="/tmp/tailscale-handler.sh"

# Create request handler script
cat > "${HANDLER_SCRIPT}" << 'HANDLER_EOF'
#!/bin/sh
# Read HTTP request
read method path version

# Process request based on path
case "$path" in
    /status)
        echo "HTTP/1.1 200 OK"
        echo "Content-Type: application/json"
        echo "Connection: close"
        echo ""
        /usr/local/bin/tailscale status --json 2>&1
        ;;
    /whois/*)
        ip=$(echo "$path" | sed 's|/whois/||')
        echo "HTTP/1.1 200 OK"
        echo "Content-Type: text/plain"
        echo "Connection: close"
        echo ""
        /usr/local/bin/tailscale whois "$ip" 2>&1
        ;;
    *)
        echo "HTTP/1.1 404 Not Found"
        echo "Content-Type: application/json"
        echo "Connection: close"
        echo ""
        echo '{"error": "Unknown endpoint"}'
        ;;
esac
HANDLER_EOF

chmod +x "${HANDLER_SCRIPT}"

echo "Starting Tailscale HTTP Proxy on port ${PORT}..."

# Run socat HTTP server
socat TCP-LISTEN:${PORT},fork,reuseaddr EXEC:"${HANDLER_SCRIPT}"
