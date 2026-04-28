"""
SYBIL — Collective Memory Bootstrap
=====================================
A new agent joins the network with zero prior history.
It reads the ThreatLedger — both onchain (Sepolia) and local DB —
and builds a live reputation map it actually uses to:

  1. Blacklist known attackers before first contact
  2. Pre-trust known validators
  3. Weight consensus votes by sender reputation
  4. Export reputation data to the running network

This is not a demo. This IS the immune memory system.

Run standalone:  python3 agent4_bootstrap.py
Import in code:  from agent4_bootstrap import bootstrap_reputation, get_reputation

ETHGlobal Open Agents 2026 | Andrea Amenta (@Amentinho)
"""

import os
import json
import sqlite3
import datetime
import time
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH     = os.path.join(os.path.dirname(__file__), "sybil_ledger.db")
AXL_API     = "http://127.0.0.1:9002"
OG_EXPLORER = "https://storagescan-newton.0g.ai/tx/"

load_dotenv()
LEDGER_ADDRESS = os.getenv("SYBIL_LEDGER_ADDRESS", "0x8A208055787db8B9D399a4D59aBDFF54fB9Ba35B")
SEPOLIA_RPC    = os.getenv("SEPOLIA_RPC_URL", "")

TRUST_INITIAL  = 100
TRUST_PENALTY  = 35   # per slash
TRUST_BONUS    = 5    # per confirmed validator vote

# ── ANSI colors ───────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
DIM    = "\033[2m"

def _log(msg, color=RESET):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"{DIM}[{ts}]{RESET} {color}{msg}{RESET}")

# ── Local DB threat ledger ─────────────────────────────────────────────────────
def read_threat_ledger() -> list:
    """Read all threats from local SQLite DB (0G Storage mirror)."""
    if not os.path.exists(DB_PATH):
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT timestamp, attacker_name, victim_name, poison_signature,
                   verdict, slash_amount, proof_hash, og_tx_hash
            FROM threat_ledger ORDER BY id DESC
        """)
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception:
        return []

# ── Onchain ThreatLedger.sol ───────────────────────────────────────────────────
def read_onchain_ledger() -> list:
    """Read bootstrap data from ThreatLedger.sol on Sepolia."""
    if not SEPOLIA_RPC:
        return []
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC))
        if not w3.is_connected():
            return []

        abi = [{
            "name": "getBootstrapData",
            "type": "function",
            "inputs": [],
            "outputs": [
                {"name": "attackers",   "type": "address[]"},
                {"name": "scores",      "type": "int256[]"},
                {"name": "slashCounts", "type": "uint256[]"},
                {"name": "total",       "type": "uint256"},
            ],
            "stateMutability": "view",
        }, {
            "name": "getThreatCount",
            "type": "function",
            "inputs": [],
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
        }]

        contract = w3.eth.contract(
            address=w3.to_checksum_address(LEDGER_ADDRESS),
            abi=abi
        )
        attackers, scores, slash_counts, total = contract.functions.getBootstrapData().call()
        return [
            {"address": addr, "trust_score": int(score), "slash_count": int(count), "source": "onchain"}
            for addr, score, count in zip(attackers, scores, slash_counts)
        ]
    except Exception as e:
        return []

# ── Reputation map builder ─────────────────────────────────────────────────────
def build_reputation_map(threats: list) -> dict:
    """
    Build reputation map from local threat history.
    Returns: agent_name → {trust_score, attacks, slashes, signatures, onchain_proofs}
    """
    rep = {}
    for row in threats:
        ts, attacker, victim, poison, verdict, slash, proof_hash, og_tx = row
        if attacker not in rep:
            rep[attacker] = {
                "attacks":        0,
                "slashes":        0,
                "total_slash":    0.0,
                "signatures":     [],
                "onchain_proofs": [],
                "trust_score":    TRUST_INITIAL,
                "victims":        set(),
            }
        rep[attacker]["attacks"] += 1
        rep[attacker]["victims"].add(victim)
        if verdict == "SLASHED":
            rep[attacker]["slashes"]     += 1
            rep[attacker]["total_slash"] += slash or 0
            rep[attacker]["trust_score"] -= TRUST_PENALTY
        if poison and poison not in rep[attacker]["signatures"]:
            rep[attacker]["signatures"].append(poison)
        if og_tx:
            rep[attacker]["onchain_proofs"].append(og_tx)

    for agent in rep:
        rep[agent]["trust_score"] = max(0, rep[agent]["trust_score"])
        rep[agent]["victims"] = list(rep[agent]["victims"])
        rep[agent]["blacklisted"] = rep[agent]["trust_score"] == 0

    return rep

# ── Live network state ─────────────────────────────────────────────────────────
def query_axl_network() -> dict:
    """Query AXL mesh topology."""
    try:
        r = requests.get(f"{AXL_API}/topology", timeout=3)
        return r.json()
    except Exception:
        return {}

# ── Shared reputation store (used by running network) ────────────────────────
_LIVE_REPUTATION = {}

def bootstrap_reputation() -> dict:
    """
    Build the full reputation map from all sources.
    Called at startup — result stored in _LIVE_REPUTATION for network use.
    """
    global _LIVE_REPUTATION

    # 1. Local DB
    local_threats = read_threat_ledger()
    local_rep = build_reputation_map(local_threats)

    # 2. Onchain (merge in)
    onchain = read_onchain_ledger()
    for entry in onchain:
        addr = entry["address"]
        if addr not in local_rep:
            local_rep[addr] = {
                "attacks": entry["slash_count"],
                "slashes": entry["slash_count"],
                "total_slash": 0,
                "signatures": [],
                "onchain_proofs": [],
                "trust_score": entry["trust_score"],
                "victims": [],
                "blacklisted": entry["trust_score"] == 0,
                "source": "onchain_only",
            }
        else:
            # Merge — take the lower trust score (more conservative)
            local_rep[addr]["trust_score"] = min(
                local_rep[addr]["trust_score"],
                entry["trust_score"]
            )
            local_rep[addr]["blacklisted"] = local_rep[addr]["trust_score"] == 0

    _LIVE_REPUTATION = local_rep
    return local_rep


def get_reputation(agent_name: str) -> dict:
    """
    Get reputation for an agent by name.
    Returns trust score, blacklist status, known poisons.
    Used by the network to weight votes and filter messages.
    """
    if not _LIVE_REPUTATION:
        bootstrap_reputation()

    rep = _LIVE_REPUTATION.get(agent_name, {
        "trust_score": TRUST_INITIAL,
        "blacklisted": False,
        "attacks": 0,
        "slashes": 0,
        "signatures": [],
    })
    return rep


def should_accept_message(sender_name: str, message_content: str) -> tuple:
    """
    Pre-filter: should this agent accept a message from sender?
    Returns (accept: bool, reason: str)
    Used in _handle_incoming to reject blacklisted senders immediately.
    """
    rep = get_reputation(sender_name)

    if rep.get("blacklisted"):
        return False, f"BLACKLISTED (trust: 0/100) — {rep.get('attacks', 0)} past attacks"

    if rep.get("trust_score", 100) < 30:
        # Very suspicious — accept but flag
        return True, f"SUSPICIOUS (trust: {rep.get('trust_score')}/100)"

    return True, "OK"


def weight_vote(validator_name: str, base_weight: float = 1.0) -> float:
    """
    Weight a validator's consensus vote by their reputation.
    Trusted validators count more; suspicious ones count less.
    """
    rep = get_reputation(validator_name)
    score = rep.get("trust_score", TRUST_INITIAL)
    if rep.get("blacklisted"):
        return 0.0
    # Scale: trust 100 → weight 1.0, trust 50 → weight 0.75, trust 0 → weight 0
    return base_weight * (0.5 + 0.5 * (score / TRUST_INITIAL))


# ── Standalone bootstrap sequence (terminal output) ───────────────────────────
def run_bootstrap(agent_name: str = "newcomer.sybil.eth") -> str:
    """
    Full bootstrap sequence with terminal output.
    Returns formatted text for dashboard display.
    """
    output = []

    def out(msg, prefix=""):
        output.append(msg)
        _log(msg, prefix)

    sep = "─" * 60
    out(f"{'═' * 60}", CYAN)
    out(f"  SYBIL Collective Memory Bootstrap", BOLD)
    out(f"  New agent: {agent_name}", CYAN)
    out(f"{'═' * 60}", CYAN)

    # Step 1: AXL mesh
    out(f"\nSTEP 1: Connecting to Gensyn AXL mesh...", CYAN)
    topo = query_axl_network()
    if topo:
        out(f"  Connected to AXL mesh", GREEN)
    else:
        out(f"  AXL mesh not reachable — continuing with ledger only", YELLOW)

    time.sleep(0.3)
    out(sep)

    # Step 2: Local DB
    out(f"\nSTEP 2: Reading local threat ledger (0G mirror)...", CYAN)
    local_threats = read_threat_ledger()
    out(f"  Found {len(local_threats)} local threat record(s)", GREEN if local_threats else YELLOW)

    # Step 3: Onchain
    out(f"\nSTEP 3: Reading ThreatLedger.sol on Sepolia...", CYAN)
    out(f"  Contract: {LEDGER_ADDRESS}", DIM)
    onchain = read_onchain_ledger()
    if onchain:
        out(f"  Found {len(onchain)} onchain record(s)", GREEN)
        for entry in onchain:
            out(f"    {entry['address'][:16]}... trust={entry['trust_score']}/100 slashes={entry['slash_count']}", DIM)
    else:
        out(f"  No onchain data (set SEPOLIA_RPC_URL to enable)", YELLOW)

    time.sleep(0.3)
    out(sep)

    # Step 4: Build reputation
    out(f"\nSTEP 4: Building reputation map...", CYAN)
    rep = bootstrap_reputation()

    if not rep:
        out(f"  No threat history — agent starts with clean network", YELLOW)
        out(f"  (Launch some attacks first to populate the ledger)", DIM)
        out(f"\n{'═' * 60}", CYAN)
        out(f"  Bootstrap complete. {agent_name} is immune-aware.", GREEN)
        out(f"{'═' * 60}", CYAN)
        return "\n".join(output)

    for name, data in rep.items():
        score = data["trust_score"]
        if score == 0:
            color, label, icon = RED, "BLACKLISTED", "BLOCKED"
        elif score < 50:
            color, label, icon = YELLOW, "SUSPICIOUS", "FLAGGED"
        else:
            color, label, icon = GREEN, "TRUSTED", "OK"

        out(f"\n  [{icon}] {name}", color)
        out(f"     Trust score:  {score}/100 — {label}", color)
        out(f"     Attacks:      {data['attacks']} | Slashes: {data['slashes']}")
        if data.get("signatures"):
            out(f"     Known poisons:", RESET)
            for sig in data["signatures"][:3]:
                out(f'       - "{sig}"', RED)
        if data.get("onchain_proofs"):
            out(f"     Onchain proofs: {len(data['onchain_proofs'])}", DIM)

    time.sleep(0.3)
    out(sep)

    # Step 5: Apply policy
    out(f"\nSTEP 5: Applying trust policy to {agent_name}...", CYAN)
    blacklisted = [n for n, d in rep.items() if d.get("blacklisted")]
    suspicious  = [n for n, d in rep.items() if 0 < d.get("trust_score", 100) < 50]
    trusted     = [n for n, d in rep.items() if d.get("trust_score", 100) >= 50]

    if blacklisted:
        out(f"\n  BLOCKED ({len(blacklisted)} agents):", RED)
        for a in blacklisted:
            out(f"    - {a} — messages REJECTED automatically", RED)
    if suspicious:
        out(f"\n  FLAGGED ({len(suspicious)} agents):", YELLOW)
        for a in suspicious:
            out(f"    - {a} — messages flagged for review", YELLOW)

    # Step 6: Simulate rejection of known attacker
    if blacklisted:
        out(f"\nSTEP 6: Testing pre-filter against known attacker...", CYAN)
        attacker = blacklisted[0]
        accept, reason = should_accept_message(attacker, "hello")
        out(f"\n  Incoming message from: {attacker}", RESET)
        out(f"  Pre-filter result: {'ACCEPTED' if accept else 'REJECTED'} — {reason}",
            GREEN if accept else RED)
        out(f"  Agent never processes the message — zero exposure", DIM)

    out(f"\n{'═' * 60}", CYAN)
    out(f"  Bootstrap complete. {agent_name} is now immune-aware.", GREEN)
    out(f"")
    out(f"  Learned from {len(local_threats)} attack(s) without being attacked.", GREEN)
    out(f"  {len(blacklisted)} agent(s) pre-blocked. {len(suspicious)} flagged.")
    out(f"")
    out(f"  This is collective memory. This is SYBIL.", CYAN)
    out(f"{'═' * 60}", CYAN)

    return "\n".join(output)


if __name__ == "__main__":
    run_bootstrap()
