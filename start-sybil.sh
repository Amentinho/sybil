#!/bin/bash
# SYBIL — Start all 5 AXL nodes + Flask dashboard
# 5-agent network: atlas (Guardian) + sentinel, oracle, warden, cipher (Validators)
# Consensus: 3/5 strict majority required to slash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AXL_DIR="$HOME/Projects/axl"
AXL_BIN="$AXL_DIR/axl-node"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "============================================================"
echo "  SYBIL — Decentralized Agent Immune System"
echo "  ETHGlobal Open Agents Hackathon 2026"
echo "  5-agent network · 3/5 consensus"
echo "============================================================"

# Kill any existing processes
pkill -f "axl-node" 2>/dev/null
pkill -f "server_v2.py" 2>/dev/null
sleep 1

cd "$AXL_DIR" || { echo "AXL dir not found: $AXL_DIR"; exit 1; }

echo "Starting SYBIL network..."

# Start all 5 AXL nodes
$AXL_BIN --config config-agent1.json > /tmp/axl-agent1.log 2>&1 &
sleep 0.5
$AXL_BIN --config config-agent2.json > /tmp/axl-agent2.log 2>&1 &
sleep 0.5
$AXL_BIN --config config-agent3.json > /tmp/axl-agent3.log 2>&1 &
sleep 0.5
$AXL_BIN --config config-agent4.json > /tmp/axl-agent4.log 2>&1 &
sleep 0.5
$AXL_BIN --config config-agent5.json > /tmp/axl-agent5.log 2>&1 &
sleep 2

# Verify all 5 are up
ALL_UP=true
for port in 9002 9012 9022 9032 9042; do
    if curl -s "http://127.0.0.1:$port/topology" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Port $port online"
    else
        echo "✗ Port $port OFFLINE"
        ALL_UP=false
    fi
done

if [ "$ALL_UP" = false ]; then
    echo ""
    echo "Some AXL nodes failed to start. Check logs:"
    echo "  tail /tmp/axl-agent4.log"
    echo "  tail /tmp/axl-agent5.log"
    echo ""
    echo "If agent4/agent5 configs are missing, run first:"
    echo "  bash $SCRIPT_DIR/add_agents_4_5.sh"
    echo ""
    echo "Continuing with available nodes..."
fi

echo "AXL nodes running"

# Start Flask dashboard
echo "Starting SYBIL dashboard..."
cd "$SCRIPT_DIR"
python3 server_v2.py
