#!/bin/bash
# .devcontainer/setup.sh
# Auto-runs when Codespace is created
set -e

echo "================================================"
echo "  SYBIL — Codespaces Setup"
echo "================================================"

# ── Python dependencies ───────────────────────────────────────────────────────
echo "Installing Python dependencies..."
pip install --quiet flask requests cryptography python-dotenv web3
echo "Python deps installed"

# ── Node dependencies ─────────────────────────────────────────────────────────
echo "Installing Node dependencies..."
npm install --legacy-peer-deps --silent 2>/dev/null || true
echo "Node deps installed"

# ── Go + AXL binary ───────────────────────────────────────────────────────────
mkdir -p ~/Projects/axl

# Copy AXL keys and configs from repo if they exist
if [ -f "config-agent4.json" ]; then
    cp config-agent4.json ~/Projects/axl/
    cp config-agent5.json ~/Projects/axl/ 2>/dev/null || true
fi

# Install Go if needed
if ! command -v go &> /dev/null; then
    echo "Installing Go..."
    curl -sL https://go.dev/dl/go1.22.0.linux-amd64.tar.gz -o /tmp/go.tar.gz
    tar -C /usr/local -xzf /tmp/go.tar.gz 2>/dev/null || true
    export PATH=$PATH:/usr/local/go/bin
    echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
fi

# Build AXL from source if available
if [ -d ~/Projects/axl/cmd ] && command -v go &> /dev/null; then
    echo "Building AXL node from source..."
    cd ~/Projects/axl
    go build -o node ./cmd/... 2>/dev/null && echo "AXL built" || echo "AXL build failed - using mock"
    cd -
fi

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
        print(f"  Generated key for agent{i}")
    else:
        print(f"  Key exists for agent{i}")
PYEOF

# ── Create AXL config files ───────────────────────────────────────────────────
echo "Creating AXL config files..."
for i in 1 2 3 4 5; do
    PORT=$((9000 + (i-1)*10 + 2))
    cat > ~/Projects/axl/config-agent${i}.json << JSON
{
  "PrivateKeyPath": "private-agent${i}.pem",
  "Peers": ["tls://34.46.48.224:9001", "tls://136.111.135.206:9001"],
  "Listen": [],
  "api_port": ${PORT}
}
JSON
done
echo "AXL configs created (ports 9002, 9012, 9022, 9032, 9042)"

# ── Create .env if not present ────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cat > .env << 'ENVEOF'
# SYBIL — Fill in to enable onchain features
OG_PRIVATE_KEY=
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY
DEPLOYER_PRIVATE_KEY=
SYBIL_REGISTRY_ADDRESS=0xeDa95B16CdbE1b0617A7233aC0204D0eB092223d
SYBIL_VAULT_ADDRESS=0x9fF5A06A828E9115986FC1EC8bAf92fa2182aF20
SYBIL_LEDGER_ADDRESS=0x8A208055787db8B9D399a4D59aBDFF54fB9Ba35B
ENVEOF
    echo ".env created"
fi

echo ""
echo "================================================"
echo "  Setup complete!"
echo "  Run: bash start-sybil.sh"
echo "  Dashboard opens automatically at port 5001"
echo "================================================"
