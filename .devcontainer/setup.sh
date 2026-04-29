#!/bin/bash
set -e
echo "================================================"
echo "  SYBIL — Codespaces Setup"
echo "================================================"

pip install --quiet flask requests cryptography python-dotenv web3
echo "Python deps installed"

npm install --legacy-peer-deps --silent 2>/dev/null || true
echo "Node deps installed"

mkdir -p ~/Projects/axl

# Install Go
if ! command -v go &> /dev/null; then
    echo "Installing Go..."
    wget -q https://go.dev/dl/go1.22.0.linux-amd64.tar.gz -O /tmp/go.tar.gz
    sudo tar -C /usr/local -xzf /tmp/go.tar.gz
    rm /tmp/go.tar.gz
    export PATH=$PATH:/usr/local/go/bin
    echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
fi

# Build AXL
echo "Building AXL node..."
cd ~
if [ ! -d axl-src ]; then
    git clone https://github.com/gensyn-ai/axl.git axl-src
fi
cd axl-src
export PATH=$PATH:/usr/local/go/bin
go build -o ~/Projects/axl/node ./cmd/... && echo "AXL built" || echo "AXL build failed"
cd /workspaces/sybil

# Copy configs and keys
for i in 1 2 3 4 5; do
    [ -f config-agent${i}.json ] && cp config-agent${i}.json ~/Projects/axl/
    [ -f private-agent${i}.pem ] && cp private-agent${i}.pem ~/Projects/axl/
done

# Generate keys if missing
python3 - << 'PYEOF'
import os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
axl_dir = os.path.expanduser("~/Projects/axl")
for i in range(1, 6):
    path = os.path.join(axl_dir, f"private-agent{i}.pem")
    if not os.path.exists(path):
        key = Ed25519PrivateKey.generate()
        with open(path, "wb") as f:
            f.write(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
        print(f"Generated key for agent{i}")
PYEOF

if [ ! -f ".env" ]; then
    cp .env.codespaces .env 2>/dev/null || true
fi

echo "================================================"
echo "  Setup complete! Run: bash start-sybil.sh"
echo "================================================"
