# 🛡️ SYBIL — Decentralized Agent Immune System

> *"New agents don't start blind — they inherit the swarm's collective memory."*

**ETHGlobal Open Agents 2026** | Andrea Amenta ([@Amentinho](https://github.com/Amentinho))

---

## The Problem

As AI agents proliferate and form autonomous networks, they become targets for **prompt injection**, identity spoofing, and coordinated manipulation. Existing defenses are siloed — each agent protects only itself, and when it's gone, its threat intelligence dies with it.

A new agent joining the network today starts completely blind — no memory of past attacks, no knowledge of bad actors, no inherited immunity.

## The Solution

SYBIL is a **decentralized immune system** for AI agent networks. When one agent detects a prompt injection attack over the Gensyn AXL P2P mesh, it broadcasts a cryptographically signed Proof of Attack to validator agents. They vote via ed25519 signatures — if consensus is reached, the attacker is **slashed onchain** via Ethereum smart contracts. The threat is permanently recorded on 0G Storage and in `ThreatLedger.sol`.

New agents bootstrap with zero prior knowledge by calling `ThreatLedger.getBootstrapData()` — immediately knowing who the attackers are before their first interaction.

**This is institutional memory for machines.**

---

## Live Demo

```bash
git clone https://github.com/Amentinho/sybil
cd sybil
pip install flask requests cryptography python-dotenv
bash start-sybil.sh
# Open http://127.0.0.1:5001
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SYBIL Network                            │
│                                                                 │
│   atlas.sybil.eth      sentinel.sybil.eth     oracle.sybil.eth  │
│   [Guardian]           [Validator]            [Validator]       │
│        │                    │                      │            │
│        └────────────────────┴──────────────────────┘            │
│                      Gensyn AXL P2P Mesh                        │
│               (real TCP · tls://34.46.48.224:9001)              │
└─────────────────────────────────────────────────────────────────┘
          │                                          │
          ▼                                          ▼
   0G Storage Testnet                      Ethereum Sepolia
   (threat records +               ┌──────────────────────────┐
    TX hashes onchain)             │   SYBILRegistry.sol      │
                                   │   SlashingVault.sol      │
                                   │   ThreatLedger.sol       │
                                   └──────────────────────────┘
```

### Attack and Defense Flow

```
1.  attacker sends poison message to victim over AXL P2P mesh
         ↓
2.  victim auto-detects poison → generates Proof of Attack
         keccak256(attacker + victim + poison + timestamp)
         ↓
3.  victim broadcasts signed proof to validators over AXL
         ↓
4.  validators sign YES/NO votes with ed25519 private keys
         ↓
5.  3/5 consensus reached → CONFIRMED
         ↓
6.  SlashingVault.slash() executes onchain
         attacker loses ETH stake
         30% distributed to YES validators as reward
         ↓
7.  ThreatLedger.recordThreat() writes immutable onchain record
    + 0G Storage upload with TX hash
         ↓
8.  newcomer.sybil.eth calls ThreatLedger.getBootstrapData()
    → inherits collective memory, blacklists known attackers
    → immune before first interaction
```

---

## Smart Contracts — Sepolia Testnet

| Contract | Address | Purpose |
|----------|---------|---------|
| `SYBILRegistry` | [`0xeDa95B16CdbE1b0617A7233aC0204D0eB092223d`](https://sepolia.etherscan.io/address/0xeDa95B16CdbE1b0617A7233aC0204D0eB092223d) | Agent registration: ENS name + AXL pubkey + ETH stake |
| `SlashingVault` | [`0x9fF5A06A828E9115986FC1EC8bAf92fa2182aF20`](https://sepolia.etherscan.io/address/0x9fF5A06A828E9115986FC1EC8bAf92fa2182aF20) | Holds ETH stakes, executes slashing, rewards validators |
| `ThreatLedger` | [`0x8A208055787db8B9D399a4D59aBDFF54fB9Ba35B`](https://sepolia.etherscan.io/address/0x8A208055787db8B9D399a4D59aBDFF54fB9Ba35B) | Immutable threat history + trust scores + bootstrap data |

**Deployer:** `0x2F7E204F76D47ea69F91Eae548C7C5B39B0Fc1c6`
**Network:** Ethereum Sepolia
**Stake per agent:** 0.01 ETH

### SYBILRegistry.sol
Agents register with an ENS name (`atlas.sybil.eth`), their Gensyn AXL ed25519 public key (32 bytes), and a minimum 0.01 ETH stake. Tracks agent status (Active → Warned → Banned) and attack/detection history.

### SlashingVault.sol
Holds all agent stakes in ETH. On consensus, slashes the attacker: 70% burned as economic disincentive, 30% distributed to validators who voted YES. Banned agents cannot withdraw their remaining stake.

### ThreatLedger.sol
Permanent immutable log of every verified attack — poison signatures, proof hashes, consensus votes, slash amounts, trust scores (0–100, decremented by 35 per slash). `getBootstrapData()` returns the full reputation map for cold bootstrap.

---

## Improvements Built

### Improvement 1 — Real AXL Receive Loops
Agents communicate over real Gensyn AXL TCP connections to the public mesh at `tls://34.46.48.224:9001`. Messages are delivered peer-to-peer. Each agent runs a live background listener that auto-triggers the full defense cycle when poison is detected in an incoming message.

### Improvement 2 — ed25519 Cryptographic Signatures
Every validator vote is signed with the agent's ed25519 private key and cryptographically verified before counting toward consensus. Proof hashes are `keccak256(attacker + victim + poison + timestamp)`. Fake votes are rejected.

### Improvement 3 — Agent4 Cold Bootstrap (Collective Memory)
A brand new agent with zero prior history calls `ThreatLedger.getBootstrapData()` and immediately knows which agents have attacked, what poison signatures they used, and their current trust score. Demo output:

```
Bootstrap complete. newcomer.sybil.eth is now immune-aware.
This agent learned from 8 past attacks without ever being attacked itself.
This is collective memory. This is SYBIL.
```

### Improvement 4 — Smart Contracts on Sepolia
Real cryptoeconomic slashing. Agent stakes are held in `SlashingVault.sol`. After AXL consensus, `slash()` is called onchain — attacker loses real ETH (testnet), validators earn rewards. `ThreatLedger.sol` provides an immutable onchain record any agent can query at any time.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| P2P Mesh | Gensyn AXL (real TCP, public mesh) |
| Cryptography | ed25519 keypairs, keccak256 proof hashes |
| Decentralized Storage | 0G Storage testnet (TX hashes onchain) |
| Smart Contracts | Solidity 0.8.20, Ethereum Sepolia |
| Contract Tooling | Hardhat, Ethers.js |
| Backend | Python 3, Flask |
| Contract Bridge | web3.py |
| Dashboard | Vanilla JS, HTML/CSS |
| Agent Identity | ENS-style naming via SYBILRegistry |
| Database | SQLite (local 0G Storage mirror) |

---

## Project Structure

```
sybil/
├── sybil_v2.py              # Core: agents, AXL mesh, consensus, slashing
├── server_v2.py             # Flask API + live dashboard
├── agent4_bootstrap.py      # Cold bootstrap — collective memory demo
├── contract_bridge.py       # Python to Ethereum contract integration
├── og_storage.js            # 0G Storage upload/download
├── start-sybil.sh           # Starts all AXL nodes + Flask dashboard
├── contracts/
│   ├── SYBILRegistry.sol    # Agent registration + ENS + AXL pubkeys
│   ├── SlashingVault.sol    # ETH stake vault + slashing + rewards
│   └── ThreatLedger.sol     # Immutable threat log + bootstrap data
├── scripts/
│   ├── deploy.js            # Hardhat deployment script
│   └── register_agents.js  # Register agents onchain with ETH stake
└── hardhat.config.js        # Hardhat config (Sepolia + localhost)
```

---

## Setup

### Requirements
```bash
pip install flask requests cryptography python-dotenv web3
npm install
```

### Environment Variables
```env
OG_PRIVATE_KEY=your_key
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY
DEPLOYER_PRIVATE_KEY=0x...
SYBIL_REGISTRY_ADDRESS=0xeDa95B16CdbE1b0617A7233aC0204D0eB092223d
SYBIL_VAULT_ADDRESS=0x9fF5A06A828E9115986FC1EC8bAf92fa2182aF20
SYBIL_LEDGER_ADDRESS=0x8A208055787db8B9D399a4D59aBDFF54fB9Ba35B
```

### Run
```bash
bash start-sybil.sh
# Dashboard: http://127.0.0.1:5001
```

### Agent4 Bootstrap Demo
```bash
python3 agent4_bootstrap.py
```

---

## Partner Technologies

**Gensyn AXL** — All agent communication runs over Gensyn's AXL P2P mesh. Three agents maintain persistent TCP connections to the public mesh. The entire immune response is triggered by real AXL message events.

**0G Storage** — Every verified threat is uploaded to 0G Storage testnet after consensus. TX hashes are displayed live in the dashboard and cross-verified in `ThreatLedger.sol`.

**ENS** — Agent identities use ENS-style names registered in `SYBILRegistry.sol`, mapping names to AXL public keys and Ethereum addresses.

---

## Built With

- [Gensyn AXL](https://docs.gensyn.ai/tech/agent-exchange-layer) — P2P agent mesh
- [0G Storage](https://0g.ai) — Decentralized storage
- [Ethereum Sepolia](https://ethereum.org) — Smart contract execution
- [Hardhat](https://hardhat.org) — Contract development and deployment
- [Claude](https://claude.ai) (Anthropic) — AI-assisted development

---

*SYBIL · ETHGlobal Open Agents 2026 · Andrea Amenta (@Amentinho)*
