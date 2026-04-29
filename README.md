# 🛡️ SYBIL — Decentralized Agent Immune System

> *"New agents don't start blind — they inherit the swarm's collective memory."*

**ETHGlobal Open Agents 2026** | Andrea Amenta ([@Amentinho](https://github.com/Amentinho))

---

## The Problem

As AI agents proliferate and form autonomous networks, they become targets for **prompt injection**, identity spoofing, and coordinated manipulation. Existing defenses are siloed — each agent protects only itself, and when it's gone, its threat intelligence dies with it.

## The Solution

SYBIL is a **decentralized immune system** for AI agent networks. When one agent detects a prompt injection attack over the Gensyn AXL P2P mesh, it broadcasts a cryptographically signed Proof of Attack to validator agents. They vote via ed25519 signatures — if **3/5 strict majority** is reached, the attacker is **slashed onchain** via Ethereum smart contracts. The threat is permanently recorded on 0G Storage and in `ThreatLedger.sol`.

New agents bootstrap by calling `ThreatLedger.getBootstrapData()` — immediately knowing who the attackers are, pre-blocking them, and weighting validator votes by trust score.

**This is institutional memory for machines.**

---

## Live Demo

**GitHub Codespaces (browser, no install):**
1. Click **Code → Codespaces → Create codespace**
2. Wait ~5 min for auto-setup (Go install + AXL build)
3. Run `cp .env.codespaces .env` → add your keys → `bash start-sybil.sh`
4. Port 5001 opens automatically

**Local:**
```bash
git clone https://github.com/Amentinho/sybil
cd sybil
pip install flask requests cryptography python-dotenv web3
npm install
cp .env.codespaces .env  # fill in keys
bash start-sybil.sh
# Open http://127.0.0.1:5001
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  SYBIL Network — 5 agents                   │
│                                                             │
│  atlas.sybil.eth   sentinel   oracle   warden   cipher      │
│  [Guardian]        [Validator x 4]                          │
│       │                 │         │       │        │        │
│       └─────────────────┴─────────┴───────┴────────┘        │
│                  Gensyn AXL P2P Mesh (real TCP)             │
│              tls://34.46.48.224:9001                        │
└─────────────────────────────────────────────────────────────┘
         │                                      │
         ▼                                      ▼
  0G Storage Testnet               Ethereum Sepolia (verified ✓)
  (threat records +            SYBILRegistry · SlashingVault
   real TX hashes)                  ThreatLedger
```

### Attack & Defense Flow

```
1. attacker sends poison → AXL P2P mesh (real TCP)
2. collective memory pre-filter: blacklisted? → REJECT instantly
3. victim detects poison → Proof of Attack (keccak256 hash)
4. broadcast to 4 validators over AXL
5. validators sign YES/NO with ed25519 keys
   votes weighted by trust score from ThreatLedger
6. 3/5 majority → CONFIRMED
7. SlashingVault.slash() → attacker loses real ETH on Sepolia
   30% distributed to YES validators as reward
8. ThreatLedger.recordThreat() → immutable onchain record
   + 0G Storage upload with TX hash
9. newcomer calls ThreatLedger.getBootstrapData()
   → inherits collective memory instantly
   → pre-blocks known attackers before first message
```

---

## Smart Contracts — Sepolia (All Verified ✓)

| Contract | Address | Etherscan |
|----------|---------|-----------|
| `SYBILRegistry` | `0xf95F7dd71EB7D4C94a97dAb58BBd2E92A0809a27` | [View source ↗](https://sepolia.etherscan.io/address/0xf95F7dd71EB7D4C94a97dAb58BBd2E92A0809a27#code) |
| `SlashingVault` | `0x9fF5A06A828E9115986FC1EC8bAf92fa2182aF20` | [View source ↗](https://sepolia.etherscan.io/address/0x9fF5A06A828E9115986FC1EC8bAf92fa2182aF20#code) |
| `ThreatLedger`  | `0x8A208055787db8B9D399a4D59aBDFF54fB9Ba35B` | [View source ↗](https://sepolia.etherscan.io/address/0x8A208055787db8B9D399a4D59aBDFF54fB9Ba35B#code) |

- **All 5 agents registered** with real ETH stakes on Sepolia
- **ThreatLedger has live onchain data** — call `getThreatCount()` to verify
- **All contracts source-verified** on Sepolia Etherscan

### Verify Live on Etherscan

```
# Check threat count (should be 6+)
ThreatLedger → Read Contract → getThreatCount()

# Check agent stakes
SlashingVault → Read Contract → getStake(0x2F7E204F...)

# Check agent registrations
SYBILRegistry → Read Contract → getAgentByENS("atlas.sybil.eth")
```

---

## Improvements Built

| # | Feature | Status |
|---|---------|--------|
| 1 | Real AXL receive loops — autonomous P2P defense | ✅ |
| 2 | ed25519 cryptographic vote signatures | ✅ |
| 3 | Collective memory bootstrap — onchain + local ledger | ✅ |
| 4 | Smart contracts + real ETH staking + Etherscan verified | ✅ |
| 5 | Novel AI attacks + 10-category semantic detector | ✅ |
| 6 | ENS identity layer via SYBILRegistry.sol | ✅ |
| 7 | Live onchain ThreatLedger with real threat records | ✅ |
| 8 | GitHub Codespaces auto-setup | ✅ |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| P2P Mesh | Gensyn AXL (5 real TCP nodes, public mesh) |
| Cryptography | ed25519 keypairs, keccak256 proof hashes |
| Storage | 0G Storage testnet (real TX hashes) |
| Smart Contracts | Solidity 0.8.20, Ethereum Sepolia, Hardhat |
| Contract Bridge | web3.py (Python → Sepolia live calls) |
| Backend | Python 3, Flask |
| Novel Attacks | Template engine + 10-category semantic detector |
| Identity | ENS-style naming via SYBILRegistry.sol |
| Dev Environment | GitHub Codespaces (.devcontainer auto-setup) |

---

## Project Structure

```
sybil/
├── sybil_v2.py              # Core: 5 agents, AXL, 3/5 consensus, slash
├── server_v2.py             # Flask API + live dashboard
├── agent4_bootstrap.py      # Collective memory (onchain + local)
├── novel_attacks.py         # Attack generator + semantic detector
├── ens_resolver.py          # ENS resolution via SYBILRegistry.sol
├── contract_bridge.py       # Python → Ethereum live integration
├── og_storage.js            # 0G Storage upload/download
├── start-sybil.sh           # Start all 5 AXL nodes + dashboard
├── contracts/
│   ├── SYBILRegistry.sol    # Agent registration + ENS + adminRegister
│   ├── SlashingVault.sol    # ETH stakes + 3/5 slashing + rewards
│   └── ThreatLedger.sol     # Immutable log + trust scores + bootstrap
├── scripts/
│   ├── deploy.js            # Deploy all 3 contracts
│   ├── register_all_agents.js
│   └── verify_contracts.js  # Etherscan verification
└── .devcontainer/
    ├── devcontainer.json    # Codespaces config
    └── setup.sh             # Auto-installs Go, builds AXL, sets up keys
```

---

## Environment Variables

```env
OG_PRIVATE_KEY=                    # 0G Storage signing key
SEPOLIA_RPC_URL=https://...        # Infura/Alchemy Sepolia RPC
DEPLOYER_PRIVATE_KEY=0x...         # Ethereum wallet private key
SYBIL_REGISTRY_ADDRESS=0xf95F7dd71EB7D4C94a97dAb58BBd2E92A0809a27
SYBIL_VAULT_ADDRESS=0x9fF5A06A828E9115986FC1EC8bAf92fa2182aF20
SYBIL_LEDGER_ADDRESS=0x8A208055787db8B9D399a4D59aBDFF54fB9Ba35B
```

---

## Partner Technologies

**Gensyn AXL** — All 5 agents maintain real TCP connections to the public AXL mesh at `tls://34.46.48.224:9001`. Every attack, vote, and consensus event travels over live peer-to-peer connections. Code: [`sybil_v2.py`](sybil_v2.py)

**0G Storage** — Every verified threat is uploaded to 0G Galileo testnet after consensus. TX hashes appear live in the dashboard and are cross-verified in `ThreatLedger.sol`. Explorer: [storagescan-newton.0g.ai](https://storagescan-newton.0g.ai). Code: [`og_storage.js`](og_storage.js)

**ENS** — All 5 agent identities use ENS-style names (`atlas.sybil.eth` etc.) registered in `SYBILRegistry.sol`, mapping to AXL public keys and Ethereum addresses. Resolved at runtime via `/api/ens`. Code: [`ens_resolver.py`](ens_resolver.py)

---

## Why SYBIL

| Property | SYBIL |
|----------|-------|
| Decentralized | No central authority — P2P consensus |
| Cryptoeconomic | Real ETH at stake — attacks are expensive |
| Persistent | Memory survives agent restarts and new deployments |
| Composable | Any agent can call `ThreatLedger.getBootstrapData()` |
| Live | Real P2P mesh, real onchain TX, real dashboard |

---

## Built With

[Gensyn AXL](https://docs.gensyn.ai/tech/agent-exchange-layer) · [0G Storage](https://0g.ai) · [Ethereum Sepolia](https://ethereum.org) · [Hardhat](https://hardhat.org) · [Claude](https://claude.ai) (Anthropic)

---

*SYBIL · ETHGlobal Open Agents 2026 · Andrea Amenta (@Amentinho)*

