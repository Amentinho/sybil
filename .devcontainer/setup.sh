#!/bin/bash
# .devcontainer/setup.sh
# Runs automatically when Codespace is created
set -e

echo "================================================"
echo "  SYBIL — Codespaces Setup"
echo "================================================"

# ── Python dependencies ───────────────────────────────────────────────────────
echo "Installing Python dependencies..."
pip install --quiet \
    flask \
    requests \
    cryptography \
    python-dotenv \
    web3

echo "Python deps installed"

# ── Node dependencies ─────────────────────────────────────────────────────────
echo "Installing Node dependencies..."
npm install --legacy-peer-deps --silent
echo "Node deps installed"

# ── AXL directory setup ───────────────────────────────────────────────────────
mkdir -p ~/Projects/axl

# ── Download AXL binary ───────────────────────────────────────────────────────
echo "Downloading Gensyn AXL node binary..."
AXL_URL="https://github.com/gensyn-ai/axl/releases/latest/download/axl-node-linux-amd64"
AXL_BIN="$HOME/Projects/axl/axl-node"

if [ ! -f "$AXL_BIN" ]; then
    if curl -sL "$AXL_URL" -o "$AXL_BIN" 2>/dev/null; then
        chmod +x "$AXL_BIN"
        echo "AXL binary downloaded"
    else
        echo "Could not download AXL binary — will use mock mode"
        # Create a mock AXL node for demo purposes
        cat > "$AXL_BIN" << 'MOCK'
#!/bin/bash
# Mock AXL node for demo/testing
PORT=$(echo "$@" | grep -o '"listen_addr": *"[^"]*"' | grep -o '[0-9]*$' || echo "9002")
echo "[node] Mock AXL node started on port $PORT"
# Start a simple HTTP server that responds to /topology and /recv
python3 -c "
import sys, json
from http.server import HTTPServer, BaseHTTPRequestHandler
port = int('$PORT') if '$PORT'.isdigit() else 9002

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        if '/topology' in self.path:
            self.wfile.write(json.dumps({'our_public_key': 'mock' + str(port)}).encode())
        else:
            self.wfile.write(b'')
    def do_POST(self):
        self.send_response(200)
        self.end_headers()

HTTPServer(('127.0.0.1', port), Handler).serve_forever()
" &
wait
MOCK
        chmod +x "$AXL_BIN"
        echo "Mock AXL node created"
    fi
else
    echo "AXL binary already present"
fi

# ── Create AXL config files ───────────────────────────────────────────────────
echo "Creating AXL config files..."
for i in 1 2 3 4 5; do
    PORT=$((9000 + (i-1)*10 + 2))
    TCP_PORT=$((7000 + i - 1))
    cat > "$HOME/Projects/axl/config-agent${i}.json" << JSON
{
  "listen_addr": "127.0.0.1:${PORT}",
  "tcp_port": ${TCP_PORT},
  "peers": [
    "tls://34.46.48.224:9001",
    "tls://136.111.135.206:9001"
  ]
}
JSON
done
echo "AXL configs created"

# ── Generate ed25519 keys for all agents ──────────────────────────────────────
echo "Generating agent ed25519 keys..."
python3 - << 'PYEOF'
import os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

axl_dir = os.path.expanduser("~/Projects/axl")
os.makedirs(axl_dir, exist_ok=True)

for i in range(1, 6):
    path = os.path.join(axl_dir, f"private-agent{i}.pem")
    if not os.path.exists(path):
        key = Ed25519PrivateKey.generate()
        pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        with open(path, "wb") as f:
            f.write(pem)
        print(f"Generated key for agent{i}")
    else:
        print(f"Key exists for agent{i}")
PYEOF

# ── Create .env if not present ────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cat > .env << 'ENV'
# SYBIL Environment Variables
# Fill in your keys to enable onchain features

# 0G Storage (get from https://faucet.0g.ai)
OG_PRIVATE_KEY=

# Ethereum Sepolia
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY
DEPLOYER_PRIVATE_KEY=

# Contract addresses (already deployed on Sepolia)
SYBIL_REGISTRY_ADDRESS=0xeDa95B16CdbE1b0617A7233aC0204D0eB092223d
SYBIL_VAULT_ADDRESS=0x9fF5A06A828E9115986FC1EC8bAf92fa2182aF20
SYBIL_LEDGER_ADDRESS=0x8A208055787db8B9D399a4D59aBDFF54fB9Ba35B
ENV
    echo ".env created (fill in your keys)"
fi

echo ""
echo "================================================"
echo "  Setup complete!"
echo "  Run: bash start-sybil.sh"
echo "  Dashboard: http://localhost:5001"
echo "================================================"
