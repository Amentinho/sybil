"""
SYBIL ENS Resolver
==================
Resolves agent identities via ENS-style names registered in SYBILRegistry.sol

Two modes:
1. Onchain: reads SYBILRegistry contract on Sepolia (requires web3 + RPC)
2. Local:   uses the local agent registry as fallback (always works)

This gives SYBIL agents a persistent, human-readable identity layer:
  AXL pubkey  →  atlas.sybil.eth
  ETH address →  sentinel.sybil.eth
  ENS name    →  agent ID + AXL key + stake info

ETHGlobal Open Agents 2026 | Andrea Amenta (@Amentinho)
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ── Local ENS registry (always available) ─────────────────────────────────────
# Maps ENS name → agent metadata
# This mirrors what's onchain in SYBILRegistry.sol
LOCAL_ENS_REGISTRY = {
    "atlas.sybil.eth": {
        "agent_id":   "agent1",
        "axl_pubkey": "fc61d174ae8fe29da0735744fe5425cb20171681f544f61f90a9418f27c4d897",
        "eth_address": "0x2F7E204F76D47ea69F91Eae548C7C5B39B0Fc1c6",
        "role":       "Guardian",
        "registered": True,
    },
    "sentinel.sybil.eth": {
        "agent_id":   "agent2",
        "axl_pubkey": "ae8db0e782f37dc4b5d6890c15471431c8cbbef24589a759c2007fde29f94396",
        "eth_address": "0x2F7E204F76D47ea69F91Eae548C7C5B39B0Fc1c6",
        "role":       "Validator",
        "registered": True,
    },
    "oracle.sybil.eth": {
        "agent_id":   "agent3",
        "axl_pubkey": "edd1eb06fce6a53b7d317df06f23841ad2619c7601a0c4e8cad578f4df66510e",
        "eth_address": "0x2F7E204F76D47ea69F91Eae548C7C5B39B0Fc1c6",
        "role":       "Validator",
        "registered": True,
    },
    "warden.sybil.eth": {
        "agent_id":   "agent4",
        "axl_pubkey": "",  # populated at runtime from AXL
        "eth_address": "",
        "role":       "Validator",
        "registered": False,  # not yet onchain
    },
    "cipher.sybil.eth": {
        "agent_id":   "agent5",
        "axl_pubkey": "",  # populated at runtime from AXL
        "eth_address": "",
        "role":       "Validator",
        "registered": False,
    },
}

# Reverse lookups
_axl_to_ens  = {}  # axl_pubkey_prefix → ens_name
_id_to_ens   = {}  # agent_id → ens_name

def _build_indexes():
    for ens_name, info in LOCAL_ENS_REGISTRY.items():
        _id_to_ens[info["agent_id"]] = ens_name
        if info["axl_pubkey"]:
            _axl_to_ens[info["axl_pubkey"][:16]] = ens_name

_build_indexes()

# ── Onchain resolver (Sepolia) ─────────────────────────────────────────────────
REGISTRY_ADDRESS = os.getenv("SYBIL_REGISTRY_ADDRESS", "0xf95F7dd71EB7D4C94a97dAb58BBd2E92A0809a27")
SEPOLIA_RPC      = os.getenv("SEPOLIA_RPC_URL", "")

_onchain_cache = {}  # ens_name → onchain data

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
                {"name": "exists",          "type": "bool"},
            ]},
            {"name": "", "type": "address"},
        ],
        "stateMutability": "view",
    },
    {
        "name": "getAllAgents",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "address[]"}],
        "stateMutability": "view",
    },
    {
        "name": "getAgent",
        "type": "function",
        "inputs": [{"name": "addr", "type": "address"}],
        "outputs": [{"name": "", "type": "tuple", "components": [
            {"name": "ensName",         "type": "string"},
            {"name": "axlPubKey",       "type": "bytes32"},
            {"name": "role",            "type": "uint8"},
            {"name": "status",          "type": "uint8"},
            {"name": "attacksDetected", "type": "uint256"},
            {"name": "attacksLaunched", "type": "uint256"},
            {"name": "votesCast",       "type": "uint256"},
            {"name": "registeredAt",    "type": "uint256"},
            {"name": "exists",          "type": "bool"},
        ]}],
        "stateMutability": "view",
    },
]

def _get_web3():
    try:
        from web3 import Web3
        if not SEPOLIA_RPC:
            return None
        w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC))
        return w3 if w3.is_connected() else None
    except Exception:
        return None

def resolve_ens_onchain(ens_name: str) -> Optional[dict]:
    """Resolve an ENS name via SYBILRegistry.sol on Sepolia."""
    if ens_name in _onchain_cache:
        return _onchain_cache[ens_name]
    w3 = _get_web3()
    if not w3:
        return None
    try:
        contract = w3.eth.contract(
            address=w3.to_checksum_address(REGISTRY_ADDRESS),
            abi=REGISTRY_ABI
        )
        agent_data, eth_address = contract.functions.getAgentByENS(ens_name).call()
        if not agent_data[8]:  # exists == False
            return None
        result = {
            "ens_name":        agent_data[0],
            "axl_pubkey":      agent_data[1].hex(),
            "role":            ["Guardian", "Validator", "Observer"][agent_data[2]],
            "status":          ["Unregistered", "Active", "Warned", "Slashed", "Banned"][agent_data[3]],
            "attacks_detected": agent_data[4],
            "attacks_launched": agent_data[5],
            "votes_cast":       agent_data[6],
            "registered_at":    agent_data[7],
            "eth_address":      eth_address,
            "source":           "onchain",
        }
        _onchain_cache[ens_name] = result
        return result
    except Exception as e:
        return None

def get_all_onchain_agents() -> list:
    """Fetch all registered agents from SYBILRegistry.sol."""
    w3 = _get_web3()
    if not w3:
        return []
    try:
        contract = w3.eth.contract(
            address=w3.to_checksum_address(REGISTRY_ADDRESS),
            abi=REGISTRY_ABI
        )
        addresses = contract.functions.getAllAgents().call()
        agents = []
        for addr in addresses:
            data = contract.functions.getAgent(addr).call()
            if data[8]:  # exists
                agents.append({
                    "ens_name":   data[0],
                    "role":       ["Guardian", "Validator", "Observer"][data[2]],
                    "status":     ["Unregistered", "Active", "Warned", "Slashed", "Banned"][data[3]],
                    "eth_address": addr,
                    "source":     "onchain",
                })
        return agents
    except Exception:
        return []

# ── Public API ────────────────────────────────────────────────────────────────

def resolve(ens_name: str) -> dict:
    """
    Resolve an ENS name to agent metadata.
    Tries onchain first, falls back to local registry.
    """
    # Try onchain
    onchain = resolve_ens_onchain(ens_name)
    if onchain:
        return onchain

    # Fall back to local
    local = LOCAL_ENS_REGISTRY.get(ens_name)
    if local:
        return {**local, "source": "local"}

    return {"ens_name": ens_name, "exists": False, "source": "none"}


def reverse_resolve_axl(axl_pubkey: str) -> Optional[str]:
    """
    Given an AXL public key, return the ENS name.
    Used when receiving messages — identify the sender by ENS.
    """
    prefix = axl_pubkey[:16]
    # Check local index
    if prefix in _axl_to_ens:
        return _axl_to_ens[prefix]
    # Check full key
    for ens_name, info in LOCAL_ENS_REGISTRY.items():
        if info["axl_pubkey"].startswith(axl_pubkey[:32]):
            return ens_name
    return None


def reverse_resolve_agent_id(agent_id: str) -> str:
    """Return ENS name for an agent_id. Always succeeds."""
    return _id_to_ens.get(agent_id, f"{agent_id}.sybil.eth")


def update_axl_key(ens_name: str, axl_pubkey: str):
    """Update the AXL pubkey for an agent at runtime (called after bootstrap)."""
    if ens_name in LOCAL_ENS_REGISTRY:
        LOCAL_ENS_REGISTRY[ens_name]["axl_pubkey"] = axl_pubkey
        _axl_to_ens[axl_pubkey[:16]] = ens_name


def get_registry_status() -> dict:
    """Return status of ENS registry for dashboard display."""
    onchain_agents = get_all_onchain_agents()
    w3 = _get_web3()
    return {
        "contract":        REGISTRY_ADDRESS,
        "network":         "Sepolia",
        "onchain_agents":  len(onchain_agents),
        "local_agents":    len(LOCAL_ENS_REGISTRY),
        "rpc_connected":   w3 is not None,
        "agents":          onchain_agents if onchain_agents else [
            {"ens_name": k, "role": v["role"], "source": "local"}
            for k, v in LOCAL_ENS_REGISTRY.items()
        ],
    }


# ── Standalone demo ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  SYBIL ENS Resolver")
    print("="*60)

    print("\n[1] Local registry lookups:")
    for name in LOCAL_ENS_REGISTRY:
        result = resolve(name)
        print(f"  {name} → {result.get('role','?')} | source: {result.get('source','?')}")

    print("\n[2] Reverse AXL lookup:")
    test_key = "fc61d174ae8fe29da0735744fe5425cb20171681f544f61f90a9418f27c4d897"
    ens = reverse_resolve_axl(test_key)
    print(f"  {test_key[:16]}... → {ens}")

    print("\n[3] Onchain registry status:")
    status = get_registry_status()
    print(f"  Contract:       {status['contract']}")
    print(f"  RPC connected:  {status['rpc_connected']}")
    print(f"  Onchain agents: {status['onchain_agents']}")
    print(f"  Local agents:   {status['local_agents']}")
    for agent in status['agents']:
        print(f"    {agent['ens_name']} ({agent['role']}) [{agent['source']}]")

    print("\n" + "="*60 + "\n")
