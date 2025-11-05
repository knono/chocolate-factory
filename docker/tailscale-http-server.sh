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
    /netcheck)
        echo "HTTP/1.1 200 OK"
        echo "Content-Type: application/json"
        echo "Connection: close"
        echo ""
        /usr/local/bin/tailscale netcheck --format=json 2>&1
        ;;
    /ping/*)
        host=$(echo "$path" | sed 's|/ping/||')
        echo "HTTP/1.1 200 OK"
        echo "Content-Type: text/plain"
        echo "Connection: close"
        echo ""
        /usr/local/bin/tailscale ping --c 5 "$host" 2>&1
        ;;
    /debug/*)
        peer=$(echo "$path" | sed 's|/debug/||')
        echo "HTTP/1.1 200 OK"
        echo "Content-Type: text/plain"
        echo "Connection: close"
        echo ""
        # Limited output to avoid hanging
        timeout 5 /usr/local/bin/tailscale debug watch-ipn 2>&1 | head -50
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
