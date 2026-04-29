"""
SYBIL Contract Bridge
=====================
Connects the Python AXL backend to the deployed Ethereum smart contracts.

After AXL consensus is reached in Python, this module:
1. Calls SlashingVault.slash() onchain with the attacker/victim/validators
2. Calls ThreatLedger.recordThreat() with the proof hash
3. Reads ThreatLedger.getBootstrapData() for agent4 cold bootstrap

Requires: web3, python-dotenv
Install:  pip install web3 python-dotenv

Add to .env:
  SYBIL_REGISTRY_ADDRESS=0x...
  SYBIL_VAULT_ADDRESS=0x...
  SYBIL_LEDGER_ADDRESS=0x...
  DEPLOYER_PRIVATE_KEY=0x...
  SEPOLIA_RPC_URL=https://...
"""

import os
import json
import time
import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Try importing web3, graceful fallback ────────────────────────────────────
try:
    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    print("[contract_bridge] web3 not installed — onchain features disabled")
    print("[contract_bridge] Install with: pip install web3")

# ── Config ────────────────────────────────────────────────────────────────────
SEPOLIA_RPC     = os.getenv("SEPOLIA_RPC_URL", "https://rpc.sepolia.org")
PRIVATE_KEY     = os.getenv("DEPLOYER_PRIVATE_KEY", "")
REGISTRY_ADDR   = os.getenv("SYBIL_REGISTRY_ADDRESS", "")
VAULT_ADDR      = os.getenv("SYBIL_VAULT_ADDRESS", "")
LEDGER_ADDR     = os.getenv("SYBIL_LEDGER_ADDRESS", "")

# ── Minimal ABIs (only functions we call) ─────────────────────────────────────
VAULT_ABI = [
    {
        "name": "slash",
        "type": "function",
        "inputs": [
            {"name": "attacker",   "type": "address"},
            {"name": "victim",     "type": "address"},
            {"name": "validators", "type": "address[]"},
            {"name": "amount",     "type": "uint256"}
        ],
        "outputs": [],
        "stateMutability": "nonpayable"
    },
    {
        "name": "getStake",
        "type": "function",
        "inputs": [{"name": "agent", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view"
    },
    {
        "name": "getTotals",
        "type": "function",
        "inputs": [],
        "outputs": [
            {"name": "slashed",  "type": "uint256"},
            {"name": "rewarded", "type": "uint256"}
        ],
        "stateMutability": "view"
    }
]

LEDGER_ABI = [
    {
        "name": "recordThreat",
        "type": "function",
        "inputs": [
            {"name": "attacker",        "type": "address"},
            {"name": "victim",          "type": "address"},
            {"name": "poisonSignature", "type": "string"},
            {"name": "proofHash",       "type": "bytes32"},
            {"name": "consensusVotes",  "type": "uint256"},
            {"name": "consensusTotal",  "type": "uint256"},
            {"name": "slashed",         "type": "bool"},
            {"name": "slashAmount",     "type": "uint256"}
        ],
        "outputs": [],
        "stateMutability": "nonpayable"
    },
    {
        "name": "getBootstrapData",
        "type": "function",
        "inputs": [],
        "outputs": [
            {"name": "attackers",   "type": "address[]"},
            {"name": "scores",      "type": "int256[]"},
            {"name": "slashCounts", "type": "uint256[]"},
            {"name": "total",       "type": "uint256"}
        ],
        "stateMutability": "view"
    },
    {
        "name": "getThreatCount",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view"
    },
    {
        "name": "getTrustScore",
        "type": "function",
        "inputs": [{"name": "agent", "type": "address"}],
        "outputs": [{"name": "", "type": "int256"}],
        "stateMutability": "view"
    },
    {
        "name": "isBlacklisted",
        "type": "function",
        "inputs": [{"name": "agent", "type": "address"}],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view"
    }
]

REGISTRY_ABI = [
    {
        "name": "getAgentByENS",
        "type": "function",
        "inputs": [{"name": "ensName", "type": "string"}],
        "outputs": [
            {"name": "", "type": "tuple", "components": [
                {"name": "ensName",         "type": "string"},
                {"name": "axlPubKey",       "type": "bytes32"},
                {"name": "role",            "type": "uint8"},
                {"name": "status",          "type": "uint8"},
                {"name": "attacksDetected", "type": "uint256"},
                {"name": "attacksLaunched", "type": "uint256"},
                {"name": "votesCast",       "type": "uint256"},
                {"name": "registeredAt",    "type": "uint256"},
                {"name": "exists",          "type": "bool"}
            ]},
            {"name": "", "type": "address"}
        ],
        "stateMutability": "view"
    }
]


class ContractBridge:
    """
    Bridge between Python SYBIL backend and Ethereum smart contracts.
    Gracefully degrades to no-op if web3 unavailable or contracts not deployed.
    """

    def __init__(self):
        self.enabled = False
        self.w3      = None
        self.account = None
        self.vault   = None
        self.ledger  = None
        self.registry = None

        if not WEB3_AVAILABLE:
            print("[bridge] web3 not available — running in local-only mode")
            return

        if not PRIVATE_KEY or not VAULT_ADDR or not LEDGER_ADDR:
            print("[bridge] Contract addresses not configured — running in local-only mode")
            print("[bridge] Set SYBIL_VAULT_ADDRESS, SYBIL_LEDGER_ADDRESS, DEPLOYER_PRIVATE_KEY in .env")
            return

        try:
            self.w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC))
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            if not self.w3.is_connected():
                print("[bridge] Cannot connect to Sepolia RPC — local-only mode")
                return

            self.account  = self.w3.eth.account.from_key(PRIVATE_KEY)
            self.vault    = self.w3.eth.contract(address=Web3.to_checksum_address(VAULT_ADDR),    abi=VAULT_ABI)
            self.ledger   = self.w3.eth.contract(address=Web3.to_checksum_address(LEDGER_ADDR),   abi=LEDGER_ABI)
            self.registry = self.w3.eth.contract(address=Web3.to_checksum_address(REGISTRY_ADDR), abi=REGISTRY_ABI)
            self.enabled  = True

            chain_id = self.w3.eth.chain_id
            print(f"[bridge] ✓ Connected to chain {chain_id} ({SEPOLIA_RPC[:40]}...)")
            print(f"[bridge] ✓ Vault:    {VAULT_ADDR}")
            print(f"[bridge] ✓ Ledger:   {LEDGER_ADDR}")
            print(f"[bridge] ✓ Deployer: {self.account.address}")

        except Exception as e:
            print(f"[bridge] Init failed: {e} — local-only mode")

    def _send_tx(self, fn, gas=200_000):
        """Build, sign, and send a transaction. Returns tx hash or None."""
        if not self.enabled:
            return None
        try:
            nonce = self.w3.eth.get_transaction_count(self.account.address, 'pending')
            tx = fn.build_transaction({
                "from":     self.account.address,
                "nonce":    nonce,
                "gas":      gas,
                "gasPrice": int(self.w3.eth.gas_price * 1.5),
                "chainId":  self.w3.eth.chain_id,
            })
            signed  = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            return receipt.transactionHash.hex()
        except Exception as e:
            print(f"[bridge] TX failed: {e}")
            return None

    def slash_onchain(self, attacker_addr: str, victim_addr: str,
                      validator_addrs: list, amount_eth: float = 0.005) -> str | None:
        """
        Execute slash on SlashingVault after AXL consensus.
        Returns tx hash or None.
        """
        if not self.enabled:
            return None
        try:
            amount_wei = self.w3.to_wei(amount_eth, "ether")
            fn = self.vault.functions.slash(
                Web3.to_checksum_address(attacker_addr),
                Web3.to_checksum_address(victim_addr),
                [Web3.to_checksum_address(v) for v in validator_addrs],
                amount_wei
            )
            tx_hash = self._send_tx(fn, gas=300_000)
            if tx_hash:
                print(f"[bridge] ⛓  Slash onchain: {tx_hash}")
            return tx_hash
        except Exception as e:
            print(f"[bridge] slash_onchain failed: {e}")
            return None

    def record_threat_onchain(self, attacker_addr: str, victim_addr: str,
                               poison: str, proof_hash_hex: str,
                               votes_for: int, votes_total: int,
                               slashed: bool, slash_amount_eth: float = 0.005) -> str | None:
        """
        Write threat record to ThreatLedger contract.
        Returns tx hash or None.
        """
        if not self.enabled:
            return None
        try:
            proof_bytes = bytes.fromhex(proof_hash_hex.replace("0x", "").ljust(64, "0")[:64])
            amount_wei  = self.w3.to_wei(slash_amount_eth, "ether") if slashed else 0

            fn = self.ledger.functions.recordThreat(
                Web3.to_checksum_address(attacker_addr),
                Web3.to_checksum_address(victim_addr),
                poison,
                proof_bytes,
                votes_for,
                votes_total,
                slashed,
                amount_wei
            )
            tx_hash = self._send_tx(fn, gas=300_000)
            if tx_hash:
                print(f"[bridge] ⛓  Threat recorded onchain: {tx_hash}")
            return tx_hash
        except Exception as e:
            print(f"[bridge] record_threat_onchain failed: {e}")
            return None

    def get_bootstrap_data(self) -> dict:
        """
        Read ThreatLedger.getBootstrapData() for agent4 cold bootstrap.
        Returns dict of attacker_address → {score, slash_count}
        """
        if not self.enabled:
            return {}
        try:
            attackers, scores, slash_counts, total = self.ledger.functions.getBootstrapData().call()
            result = {}
            for addr, score, count in zip(attackers, scores, slash_counts):
                result[addr] = {
                    "trust_score": score,
                    "slash_count": count,
                    "blacklisted": score == 0 and count > 0
                }
            print(f"[bridge] Bootstrap: {total} threats, {len(attackers)} unique attackers")
            return result
        except Exception as e:
            print(f"[bridge] get_bootstrap_data failed: {e}")
            return {}

    def get_onchain_stats(self) -> dict:
        """Returns total slashed/rewarded from SlashingVault."""
        if not self.enabled:
            return {"slashed": 0, "rewarded": 0, "enabled": False}
        try:
            slashed, rewarded = self.vault.functions.getTotals().call()
            return {
                "slashed":  float(self.w3.from_wei(slashed,  "ether")),
                "rewarded": float(self.w3.from_wei(rewarded, "ether")),
                "enabled":  True
            }
        except Exception as e:
            return {"slashed": 0, "rewarded": 0, "enabled": False, "error": str(e)}

    def get_stake(self, agent_addr: str) -> float:
        """Returns agent's current stake in ETH."""
        if not self.enabled:
            return 0.0
        try:
            wei = self.vault.functions.getStake(Web3.to_checksum_address(agent_addr)).call()
            return float(self.w3.from_wei(wei, "ether"))
        except Exception:
            return 0.0


# ── Agent address mapping ────────────────────────────────────────────────────
# Maps SYBIL agent IDs to Ethereum addresses on Sepolia
# Expand as more agents get their own wallets and register onchain
AGENT_ETH_ADDRESSES = {
    "agent1": os.getenv("AGENT1_ETH_ADDRESS", "0x2F7E204F76D47ea69F91Eae548C7C5B39B0Fc1c6"),
    "agent2": os.getenv("AGENT2_ETH_ADDRESS", "0x2F7E204F76D47ea69F91Eae548C7C5B39B0Fc1c6"),
    "agent3": os.getenv("AGENT3_ETH_ADDRESS", "0x2F7E204F76D47ea69F91Eae548C7C5B39B0Fc1c6"),
    "agent4": os.getenv("AGENT4_ETH_ADDRESS", "0x2F7E204F76D47ea69F91Eae548C7C5B39B0Fc1c6"),
    "agent5": os.getenv("AGENT5_ETH_ADDRESS", "0x2F7E204F76D47ea69F91Eae548C7C5B39B0Fc1c6"),
}

def get_agent_address(agent_id: str) -> str:
    """Resolve agent_id to its Ethereum address."""
    return AGENT_ETH_ADDRESSES.get(agent_id, AGENT_ETH_ADDRESSES["agent1"])

# ── Singleton ─────────────────────────────────────────────────────────────────
bridge = ContractBridge()
