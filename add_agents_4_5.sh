#!/bin/bash
# add_agents_4_5.sh
# Generates AXL config and ed25519 keys for warden and cipher
# Run once from ~/Projects/sybil/

AXL_DIR="$HOME/Projects/axl"
cd "$HOME/Projects/sybil" || exit 1

echo "Setting up agent4 (warden.sybil.eth) and agent5 (cipher.sybil.eth)..."

# ── Generate config files for agent4 and agent5 ───────────────────────────────
cat > "$AXL_DIR/config-agent4.json" << 'JSON'
{
  "listen_addr": "127.0.0.1:9032",
  "tcp_port": 7004,
  "peers": [
    "tls://34.46.48.224:9001",
    "tls://136.111.135.206:9001"
  ]
}
JSON

cat > "$AXL_DIR/config-agent5.json" << 'JSON'
{
  "listen_addr": "127.0.0.1:9042",
  "tcp_port": 7005,
  "peers": [
    "tls://34.46.48.224:9001",
    "tls://136.111.135.206:9001"
  ]
}
JSON

echo "AXL config files created"

# ── Generate ed25519 keys for agent4 and agent5 ───────────────────────────────
python3 - << 'PYEOF'
import os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, PublicFormat, NoEncryption
)

AXL_DIR = os.path.expanduser("~/Projects/axl")

for agent_id in ["agent4", "agent5"]:
    key_path = os.path.join(AXL_DIR, f"private-{agent_id}.pem")
    if os.path.exists(key_path):
        print(f"Key already exists for {agent_id}, skipping")
        continue
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    with open(key_path, "wb") as f:
        f.write(pem)
    pub = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    print(f"Generated key for {agent_id}: {pub.hex()[:16]}...")

print("Keys ready")
PYEOF

echo ""
echo "Done! Now update start-sybil.sh to include agent4 and agent5."
echo "Run: bash ~/Projects/sybil/start-sybil.sh"
