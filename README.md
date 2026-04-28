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

```bash
git clone https://github.com/Amentinho/sybil
cd sybil && pip install flask requests cryptography python-dotenv web3
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
└─────────────────────────────────────────────────────────────┘
         │                                      │
         ▼                                      ▼
  0G Storage Testnet               Ethereum Sepolia (verified)
  (threat records)             SYBILRegistry · SlashingVault
                                     ThreatLedger
```

### Attack Flow

```
1. attacker sends poison → AXL mesh
2. collective memory pre-filter: blacklisted? → REJECT instantly
3. victim detects poison → Proof of Attack (keccak256 hash)
4. broadcast to 4 validators over AXL
5. validators sign YES/NO with ed25519 keys
   votes weighted by trust score
6. 3/5 majority → CONFIRMED
7. SlashingVault.slash() onchain → attacker loses ETH
   30% to validators as reward
8. ThreatLedger.recordThreat() → immutable record + 0G upload
9. newcomer.getBootstrapData() → inherits collective memory
```

---

## Smart Contracts — Sepolia (All Verified ✓)

| Contract | Address | Source |
|----------|---------|--------|
| `SYBILRegistry` | `0xf95F7dd71EB7D4C94a97dAb58BBd2E92A0809a27` | [Etherscan ↗](https://sepolia.etherscan.io/address/0xf95F7dd71EB7D4C94a97dAb58BBd2E92A0809a27#code) |
| `SlashingVault` | `0x9fF5A06A828E9115986FC1EC8bAf92fa2182aF20` | [Etherscan ↗](https://sepolia.etherscan.io/address/0x9fF5A06A828E9115986FC1EC8bAf92fa2182aF20#code) |
| `ThreatLedger`  | `0x8A208055787db8B9D399a4D59aBDFF54fB9Ba35B` | [Etherscan ↗](https://sepolia.etherscan.io/address/0x8A208055787db8B9D399a4D59aBDFF54fB9Ba35B#code) |

**All 5 agents registered with real ETH stakes on Sepolia.**

---

## Improvements Built

| # | Feature | Status |
|---|---------|--------|
| 1 | Real AXL receive loops — autonomous defense | ✅ |
| 2 | ed25519 cryptographic vote signatures | ✅ |
| 3 | Collective memory bootstrap — onchain + local | ✅ |
| 4 | Smart contracts + real ETH staking + verified Etherscan | ✅ |
| 5 | Novel AI attacks + semantic poison detector | ✅ |
| 6 | ENS identity layer via SYBILRegistry | ✅ |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| P2P Mesh | Gensyn AXL (5 real TCP nodes, public mesh) |
| Cryptography | ed25519 keypairs, keccak256 proof hashes |
| Storage | 0G Storage testnet (TX hashes onchain) |
| Smart Contracts | Solidity 0.8.20, Sepolia, verified Etherscan |
| Tooling | Hardhat, Ethers.js, web3.py |
| Backend | Python 3, Flask |
| Novel Attacks | GPT-4o-mini + 10-category semantic detector |
| Identity | ENS-style naming, SYBILRegistry.sol |
| Dev Environment | GitHub Codespaces (.devcontainer) |

---

## Project Structure

```
sybil/
├── sybil_v2.py              # Core: 5 agents, AXL, 3/5 consensus
├── server_v2.py             # Flask API + live dashboard
├── agent4_bootstrap.py      # Collective memory (onchain + local)
├── novel_attacks.py         # AI attack generator + semantic detector
├── ens_resolver.py          # ENS resolution via SYBILRegistry.sol
├── contract_bridge.py       # Python → Ethereum integration
├── og_storage.js            # 0G Storage
├── start-sybil.sh           # Start all 5 AXL nodes + dashboard
├── contracts/
│   ├── SYBILRegistry.sol    # Registration + ENS + adminRegister
│   ├── SlashingVault.sol    # ETH stakes + 3/5 slashing + rewards
│   └── ThreatLedger.sol     # Immutable log + trust scores + bootstrap
├── scripts/
│   ├── deploy.js
│   ├── register_all_agents.js
│   └── verify_contracts.js
└── .devcontainer/           # GitHub Codespaces auto-setup
```

---

## Setup

```bash
pip install flask requests cryptography python-dotenv web3
npm install
```

```env
OG_PRIVATE_KEY=
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY
DEPLOYER_PRIVATE_KEY=0x...
SYBIL_REGISTRY_ADDRESS=0xf95F7dd71EB7D4C94a97dAb58BBd2E92A0809a27
SYBIL_VAULT_ADDRESS=0x9fF5A06A828E9115986FC1EC8bAf92fa2182aF20
SYBIL_LEDGER_ADDRESS=0x8A208055787db8B9D399a4D59aBDFF54fB9Ba35B
```

---

## Partner Technologies

**Gensyn AXL** — All 5 agents maintain real TCP connections to the public AXL mesh. The entire immune response is triggered by live AXL message events.

**0G Storage** — Every verified threat is uploaded to 0G testnet after consensus. TX hashes shown live in dashboard and cross-verified in ThreatLedger.sol.

**ENS** — All 5 agent identities use ENS-style names in SYBILRegistry.sol, mapping to AXL public keys and Ethereum addresses. Resolved at runtime via `/api/ens`.

---

## Built With

[Gensyn AXL](https://docs.gensyn.ai/tech/agent-exchange-layer) · [0G Storage](https://0g.ai) · [Ethereum](https://ethereum.org) · [Hardhat](https://hardhat.org) · [Claude](https://claude.ai) (Anthropic)

---

*SYBIL · ETHGlobal Open Agents 2026 · Andrea Amenta (@Amentinho)*
