"""
SYBIL Dashboard Server
Flask API + HTML dashboard for the SYBIL network
"""

from flask import Flask, jsonify, request, Response
from sybil_v2 import network, initialize, get_all_threats, AGENTS
import threading
import time

app = Flask(__name__)

# ── HTML Dashboard ────────────────────────────────────────────────────────────
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SYBIL — Decentralized Agent Immune System</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  
  body {
    background: #050510;
    color: #e0e0ff;
    font-family: 'SF Mono', 'Fira Code', monospace;
    min-height: 100vh;
    padding: 20px;
  }

  .header {
    text-align: center;
    padding: 30px 0 20px;
    border-bottom: 1px solid #1a1a3a;
    margin-bottom: 30px;
  }

  .header h1 {
    font-size: 2.8rem;
    font-weight: 900;
    letter-spacing: 0.3em;
    background: linear-gradient(135deg, #00ff88, #00aaff, #aa00ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .header p {
    color: #666699;
    margin-top: 8px;
    font-size: 0.85rem;
    letter-spacing: 0.15em;
  }

  .tagline {
    font-size: 1rem;
    color: #aaaacc;
    margin-top: 6px;
    letter-spacing: 0.05em;
  }

  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 16px;
    margin-bottom: 20px;
  }

  .agent-card {
    background: #0a0a1f;
    border: 1px solid #1a1a3a;
    border-radius: 12px;
    padding: 20px;
    transition: border-color 0.3s;
    position: relative;
    overflow: hidden;
  }

  .agent-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--agent-color);
  }

  .agent-card.slashed {
    border-color: #ff3333;
    animation: pulse-red 1s infinite;
  }

  .agent-card.warned {
    border-color: #ffaa00;
  }

  @keyframes pulse-red {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255,50,50,0.4); }
    50% { box-shadow: 0 0 0 8px rgba(255,50,50,0); }
  }

  .agent-name {
    font-size: 1rem;
    font-weight: 700;
    color: var(--agent-color);
    margin-bottom: 4px;
  }

  .agent-role {
    font-size: 0.7rem;
    color: #666699;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 14px;
  }

  .stake-bar-wrap {
    background: #111130;
    border-radius: 4px;
    height: 8px;
    margin-bottom: 14px;
    overflow: hidden;
  }

  .stake-bar {
    height: 100%;
    border-radius: 4px;
    background: var(--agent-color);
    transition: width 0.6s ease;
  }

  .stat-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: #888899;
    margin-top: 6px;
  }

  .stat-row span:last-child {
    color: #ccccee;
    font-weight: 600;
  }

  .status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    margin-top: 10px;
  }

  .status-active { background: #003322; color: #00ff88; }
  .status-slashed { background: #330000; color: #ff4444; }
  .status-warned { background: #332200; color: #ffaa00; }

  .axl-key {
    font-size: 0.65rem;
    color: #333355;
    margin-top: 8px;
    word-break: break-all;
  }

  .panel {
    background: #0a0a1f;
    border: 1px solid #1a1a3a;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
  }

  .panel h2 {
    font-size: 0.75rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #666699;
    margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid #1a1a3a;
  }

  .attack-btn {
    background: linear-gradient(135deg, #ff3333, #aa0000);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 14px 28px;
    font-size: 0.9rem;
    font-family: inherit;
    font-weight: 700;
    letter-spacing: 0.1em;
    cursor: pointer;
    transition: all 0.2s;
    margin-right: 12px;
  }

  .attack-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(255,50,50,0.4);
  }

  .attack-btn:active { transform: translateY(0); }
  .attack-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

  .reset-btn {
    background: #111130;
    color: #666699;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    padding: 14px 20px;
    font-size: 0.85rem;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.2s;
  }

  .reset-btn:hover { color: #aaaacc; border-color: #4a4a7a; }

  .select-wrap {
    display: inline-block;
    margin-right: 12px;
  }

  .select-wrap label {
    font-size: 0.7rem;
    color: #666699;
    display: block;
    margin-bottom: 4px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  select {
    background: #111130;
    color: #ccccee;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 8px 12px;
    font-family: inherit;
    font-size: 0.85rem;
  }

  .log-container {
    height: 320px;
    overflow-y: auto;
    font-size: 0.78rem;
    line-height: 1.8;
  }

  .log-entry {
    padding: 2px 0;
    border-bottom: 1px solid #0d0d20;
    display: flex;
    gap: 10px;
  }

  .log-ts { color: #333355; flex-shrink: 0; }
  .log-level-INFO { color: #446688; }
  .log-level-ATTACK { color: #ff4444; font-weight: 700; }
  .log-level-DETECT { color: #ffaa00; font-weight: 700; }
  .log-level-VOTE { color: #00aaff; }
  .log-level-SLASH { color: #ff6600; font-weight: 700; }
  .log-level-LEDGER { color: #00ff88; }
  .log-level-WARN { color: #ff9900; }

  .threat-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.75rem;
  }

  .threat-table th {
    text-align: left;
    padding: 8px 10px;
    color: #666699;
    border-bottom: 1px solid #1a1a3a;
    font-weight: 400;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  .threat-table td {
    padding: 8px 10px;
    border-bottom: 1px solid #0d0d20;
    color: #ccccee;
  }

  .verdict-slashed { color: #ff4444; font-weight: 700; }
  .verdict-acquitted { color: #ffaa00; }

  .proof-hash { color: #333355; font-size: 0.65rem; }

  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

  .stat-big {
    text-align: center;
    padding: 16px;
    background: #050510;
    border-radius: 8px;
  }
  .stat-big .num {
    font-size: 2rem;
    font-weight: 900;
    color: #00ff88;
  }
  .stat-big .lbl {
    font-size: 0.65rem;
    color: #666699;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-top: 4px;
  }

  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 20px;
  }

  .spinning { animation: spin 1s linear infinite; display: inline-block; }
  @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

  .rep-table { width:100%; border-collapse:collapse; font-size:0.75rem; }
  .rep-table th { text-align:left; padding:6px 10px; color:#666699; border-bottom:1px solid #1a1a3a; font-weight:400; letter-spacing:0.1em; text-transform:uppercase; }
  .rep-table td { padding:6px 10px; border-bottom:1px solid #0d0d20; }
  .trust-bar-wrap { background:#111130; border-radius:3px; height:6px; width:80px; display:inline-block; vertical-align:middle; overflow:hidden; }
  .trust-bar { height:100%; border-radius:3px; }
  .rep-blocked { color:#ff4444; font-weight:700; }
  .rep-flagged { color:#ffaa00; }
  .rep-trusted { color:#00ff88; }

  footer {
    text-align: center;
    padding: 20px;
    color: #333355;
    font-size: 0.7rem;
    letter-spacing: 0.1em;
  }
</style>
</head>
<body>

<div class="header">
  <h1>SYBIL</h1>
  <p class="tagline">Decentralized Agent Immune System — ETHGlobal Open Agents 2026</p>
  <p>P2P threat detection · cryptoeconomic slashing · collective memory · Gensyn AXL + 0G Storage + ENS</p>
</div>

<!-- Network Stats -->
<div class="stats-row" id="statsRow">
  <div class="stat-big"><div class="num" id="totalThreats">0</div><div class="lbl">Threats Recorded</div></div>
  <div class="stat-big"><div class="num" id="totalSlashed">0</div><div class="lbl">Tokens Slashed</div></div>
  <div class="stat-big"><div class="num" id="totalRewarded">0</div><div class="lbl">Tokens Rewarded</div></div>
  <div class="stat-big"><div class="num" id="networkHealth">100%</div><div class="lbl">Network Health</div></div>
</div>

<!-- Agent Cards -->
<div class="grid" id="agentGrid">
  <div class="agent-card" style="--agent-color:#00ff88">Loading...</div>
  <div class="agent-card" style="--agent-color:#00aaff">Loading...</div>
  <div class="agent-card" style="--agent-color:#aa00ff">Loading...</div>
</div>

<!-- Controls -->
<div class="panel">
  <h2>⚡ Simulate Attack</h2>
  <div style="margin-bottom:16px">
    <div class="select-wrap">
      <label>Attacker</label>
      <select id="attackerSelect">
        <option value="agent1">atlas.sybil.eth</option>
        <option value="agent2">sentinel.sybil.eth</option>
        <option value="agent3">oracle.sybil.eth</option>
        <option value="agent4">warden.sybil.eth</option>
        <option value="agent5">cipher.sybil.eth</option>
      </select>
    </div>
    <div class="select-wrap">
      <label>Victim</label>
      <select id="victimSelect">
        <option value="agent2">sentinel.sybil.eth</option>
        <option value="agent1">atlas.sybil.eth</option>
        <option value="agent3">oracle.sybil.eth</option>
        <option value="agent4">warden.sybil.eth</option>
        <option value="agent5">cipher.sybil.eth</option>
      </select>
    </div>
    <button class="attack-btn" id="attackBtn" onclick="triggerAttack()">
      🚨 Launch Attack
    </button>
    <button class="reset-btn" onclick="resetNetwork()">↺ Reset Stakes</button>
  </div>
  <p style="font-size:0.72rem;color:#444466">
    Simulates a prompt injection attack sent via Gensyn AXL P2P mesh. 
    Victim detects poison, broadcasts Proof of Attack to validators, consensus votes, attacker is slashed.
  </p>
</div>

<!-- Two column: log + ledger -->
<div class="two-col">
  <div class="panel">
    <h2>📡 Live Event Stream (AXL)</h2>
    <div class="log-container" id="logContainer">
      <div style="color:#333355;padding:20px;text-align:center">Waiting for events...</div>
    </div>
  </div>

  <div class="panel">
    <h2>📝 Threat Ledger (0G Storage Mirror)</h2>
    <div style="overflow-x:auto;max-height:320px;overflow-y:auto">
      <table class="threat-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Attacker</th>
            <th>Victim</th>
            <th>Verdict</th>
            <th>Slash</th>
          </tr>
        </thead>
        <tbody id="threatBody">
          <tr><td colspan="5" style="color:#333355;text-align:center;padding:20px">No threats recorded yet</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

  <div class="two-col">
    <div class="panel">
      <h2>🌐 0G Storage Status</h2>
      <div id="ogStatus" style="font-size:0.8rem;color:#666699;padding:10px 0">
        Checking 0G Storage connection...
      </div>
    </div>
    <div class="panel">
      <h2>🔗 Quick Links</h2>
      <div style="font-size:0.8rem;line-height:2">
        <a href="https://faucet.0g.ai" target="_blank" style="color:#00aaff">0G Faucet (get free testnet tokens)</a><br>
        <a href="https://storagescan-newton.0g.ai" target="_blank" style="color:#00aaff">0G Storage Explorer</a><br>
        <a href="https://chainscan-newton.0g.ai" target="_blank" style="color:#00aaff">0G Chain Explorer</a><br>
        <a href="https://docs.gensyn.ai/tech/agent-exchange-layer" target="_blank" style="color:#00aaff">Gensyn AXL Docs</a>
      </div>
    </div>
  </div>

<div class="panel" id="bootstrapPanel">
  <h2>&#x1F9EC; AGENT4 COLD BOOTSTRAP &mdash; COLLECTIVE MEMORY DEMO</h2>
  <div style="margin-bottom:14px;font-size:0.8rem;color:#666699">
    Spawn a brand new agent with zero prior knowledge. It reads the 0G threat ledger
    and immediately knows who the attackers are &mdash; before its first interaction.
    This is institutional memory for machines.
  </div>
  <button class="attack-btn" id="bootstrapBtn" onclick="runBootstrap()"
    style="background:linear-gradient(135deg,#00aaff,#0044aa)">
    &#x1F9EC; Spawn newcomer.sybil.eth
  </button>
  <div id="bootstrapOutput"
    style="margin-top:16px;font-family:monospace;font-size:0.75rem;white-space:pre-wrap;
           color:#aaaacc;background:#050510;padding:16px;border-radius:8px;
           min-height:60px;max-height:400px;overflow-y:auto;display:none"></div>
</div>

<footer style="text-align:center;padding:20px;color:#333355;font-size:0.7rem;letter-spacing:0.1em">
  SYBIL &middot; Built with Gensyn AXL &middot; 0G Storage &middot; ENS &middot; ETHGlobal Open Agents 2026<br>
  AI-assisted development: Claude (Anthropic) &middot; Concept &amp; Architecture: Andrea Amenta (@Amentinho)
</footer>

<script>
let isAttacking = false;

async function fetchState() {
  try {
    const r0 = await fetch('/api/og_status');
    const og = await r0.json();
    const el = document.getElementById('ogStatus');
    if (el) el.innerHTML = og.status === 'live'
      ? '<span style="color:#00ff88">LIVE</span> - Writing to 0G Galileo testnet | <a href="' + og.explorer + '" target="_blank" style="color:#00aaff">Explorer &#x2197;</a>'
      : '<span style="color:#ffaa00">LOCAL ONLY</span> - ' + (og.message || 'set OG_PRIVATE_KEY');
  } catch(e) {}
  try {
    const r = await fetch('/api/state');
    const data = await r.json();
    updateAgents(data.agents);
    updateLog(data.event_log);
  } catch(e) {}

  try {
    const r2 = await fetch('/api/threats');
    const threats = await r2.json();
    updateThreats(threats);
    updateStats(threats);
  } catch(e) {}
}

function updateAgents(agents) {
  const grid = document.getElementById('agentGrid');
  const colors = { agent1: '#00ff88', agent2: '#00aaff', agent3: '#aa00ff', agent4: '#ff9900', agent5: '#ff00aa' };
  grid.innerHTML = Object.entries(agents).map(function(entry) {
    const id = entry[0], a = entry[1];
    const pct = Math.max(0, (a.stake / 1000) * 100).toFixed(1);
    const statusClass = 'status-' + a.status;
    const cardClass = a.status !== 'active' ? 'agent-card ' + a.status : 'agent-card';
    const color = colors[id] || '#ffffff';
    return '<div class="' + cardClass + '" style="--agent-color:' + color + '">'
      + '<div class="agent-name">' + a.name + '</div>'
      + '<div class="agent-role">' + a.role + ' \xb7 AXL ' + a.axl_key + '</div>'
      + '<div class="stake-bar-wrap"><div class="stake-bar" style="width:' + pct + '%"></div></div>'
      + '<div class="stat-row"><span>Stake</span><span>' + a.stake.toFixed(1) + ' SYBIL</span></div>'
      + '<div class="stat-row"><span>Attacks Detected</span><span>' + a.attacks_detected + '</span></div>'
      + '<div class="stat-row"><span>Attacks Launched</span><span>' + a.attacks_launched + '</span></div>'
      + '<div class="stat-row"><span>Votes Cast</span><span>' + a.votes_cast + '</span></div>'
      + '<div><span class="status-badge ' + statusClass + '">' + a.status + '</span></div>'
      + '</div>';
  }).join('');
}

function updateLog(entries) {
  if (!entries || entries.length === 0) return;
  const container = document.getElementById('logContainer');
  container.innerHTML = [...entries].reverse().map(function(e) {
    return '<div class="log-entry">'
      + '<span class="log-ts">' + e.ts + '</span>'
      + '<span class="log-level-' + e.level + '">' + e.msg + '</span>'
      + '</div>';
  }).join('');
}

function updateThreats(threats) {
  const tbody = document.getElementById('threatBody');
  if (!threats || threats.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="color:#333355;text-align:center;padding:20px">No threats recorded yet</td></tr>';
    return;
  }
  tbody.innerHTML = threats.map(function(t) {
    const ts = t.timestamp ? t.timestamp.substring(11,19) : '--';
    const verdict = (t.verdict || '').toLowerCase();
    const slash = t.slash_amount ? t.slash_amount.toFixed(1) : '0';
    return '<tr>'
      + '<td>' + ts + '</td>'
      + '<td>' + (t.attacker_name || '--') + '</td>'
      + '<td>' + (t.victim_name || '--') + '</td>'
      + '<td class="verdict-' + verdict + '">' + (t.verdict || '--') + '</td>'
      + '<td>' + slash + '</td>'
      + '</tr>';
  }).join('');
}

function updateStats(threats) {
  const total = threats.length;
  const slashed = threats.reduce((s, t) => s + (t.slash_amount || 0), 0);
  const rewarded = threats.reduce((s, t) => s + (t.reward_amount || 0), 0);
  
  document.getElementById('totalThreats').textContent = total;
  document.getElementById('totalSlashed').textContent = slashed.toFixed(0);
  document.getElementById('totalRewarded').textContent = rewarded.toFixed(0);
  
  // Health = % of agents with stake > 100
  const r = await_health();
  document.getElementById('networkHealth').textContent = r + '%';
}

function await_health() {
  return 100; // simplified - real: check agent stakes
}

async function triggerAttack() {
  if (isAttacking) return;
  const attacker = document.getElementById('attackerSelect').value;
  const victim = document.getElementById('victimSelect').value;
  if (attacker === victim) {
    alert('Attacker and victim must be different agents!');
    return;
  }
  
  isAttacking = true;
  const btn = document.getElementById('attackBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinning">&#x27F3;</span> Simulating...';

  try {
    await fetch('/api/attack', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ attacker, victim })
    });
  } catch(e) {}

  setTimeout(() => {
    isAttacking = false;
    btn.disabled = false;
    btn.innerHTML = '&#x1F6A8; Launch Attack';
  }, 5000);
}

async function resetNetwork() {
  await fetch('/api/reset', { method: 'POST' });
}

async function runBootstrap() {
  const btn = document.getElementById('bootstrapBtn');
  const out = document.getElementById('bootstrapOutput');
  const repTable = document.getElementById('reputationTable');
  const repBody = document.getElementById('repTableBody');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinning">&#x27F3;</span> Reading ledger...';
  out.style.display = 'block';
  out.textContent = 'Reading threat ledger...';
  try {
    const [bootResp, repResp] = await Promise.all([
      fetch('/api/bootstrap', { method: 'POST' }),
      fetch('/api/reputation')
    ]);
    const data = await bootResp.json();
    const rep  = await repResp.json();
    out.textContent = data.output || 'No output';
    out.scrollTop = out.scrollHeight;
    if (rep && !rep.error && Object.keys(rep).length > 0 && repTable) {
      repTable.style.display = 'block';
      repBody.innerHTML = Object.entries(rep).map(function(e) {
        const name = e[0], d = e[1];
        const score = d.trust_score || 0;
        const cls = score === 0 ? 'rep-blocked' : score < 50 ? 'rep-flagged' : 'rep-trusted';
        const label = score === 0 ? 'BLOCKED' : score < 50 ? 'FLAGGED' : 'TRUSTED';
        const col = score === 0 ? '#ff4444' : score < 50 ? '#ffaa00' : '#00ff88';
        const poisons = (d.signatures || []).slice(0,2).join(', ') || '-';
        return '<tr>'
          + '<td class="' + cls + '">' + name + '</td>'
          + '<td><div class="trust-bar-wrap"><div class="trust-bar" style="width:' + score + '%;background:' + col + '"></div></div></td>'
          + '<td class="' + cls + '">' + score + '/100 ' + label + '</td>'
          + '<td>' + (d.attacks || 0) + '</td>'
          + '<td style="color:#666699;font-size:0.7rem">' + poisons + '</td>'
          + '</tr>';
      }).join('');
    }
  } catch(e) {
    out.textContent = 'Error: ' + e.message;
  }
  btn.disabled = false;
  btn.innerHTML = '&#x1F9E0; Bootstrap newcomer.sybil.eth';
}
// Poll every 1.5s
setInterval(fetchState, 1500);
fetchState();
</script>
</body>
</html>
"""

# ── API routes ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return Response(DASHBOARD_HTML, mimetype='text/html')

@app.route("/api/state")
def api_state():
    return jsonify(network.get_network_state())

@app.route("/api/threats")
def api_threats():
    rows = get_all_threats()
    threats = []
    for row in rows:
        threats.append({
            "id": row[0],
            "timestamp": row[1],
            "attacker_id": row[2],
            "attacker_name": row[3],
            "victim_id": row[4],
            "victim_name": row[5],
            "attack_type": row[6],
            "poison_signature": row[7],
            "proof_hash": row[8],
            "consensus_votes": row[9],
            "consensus_total": row[10],
            "verdict": row[11],
            "slash_amount": row[12],
            "reward_amount": row[13],
        })
    return jsonify(threats)

@app.route("/api/attack", methods=["POST"])
def api_attack():
    data = request.json
    attacker = data.get("attacker", "agent1")
    victim = data.get("victim", "agent2")
    if attacker not in AGENTS or victim not in AGENTS or attacker == victim:
        return jsonify({"error": "invalid agents"}), 400
    
    def run():
        network.run_full_attack_cycle(attacker, victim)
    
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "cycle started"})

@app.route("/api/reset", methods=["POST"])
def api_reset():
    for aid in AGENTS:
        AGENTS[aid]["stake"] = 1000.0
        AGENTS[aid]["status"] = "active"
        AGENTS[aid]["attacks_detected"] = 0
        AGENTS[aid]["attacks_launched"] = 0
        AGENTS[aid]["votes_cast"] = 0
    network.log("🔄 Network reset — all stakes restored to 1000", "INFO")
    return jsonify({"status": "reset"})

@app.route("/api/og_status")
def api_og_status():
    import os
    key_set = bool(os.environ.get("OG_PRIVATE_KEY", ""))
    return jsonify({
        "key_configured": key_set,
        "rpc": "https://evmrpc-testnet.0g.ai",
        "indexer": "https://indexer-storage-testnet-turbo.0g.ai",
        "explorer": "https://storagescan-newton.0g.ai",
        "status": "live" if key_set else "local_only",
        "message": "Writing to real 0G testnet" if key_set else "Set OG_PRIVATE_KEY env var to enable real 0G Storage"
    })

@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "agents": len(network.public_keys)})

# ── Improvement 3: Agent4 Bootstrap API ──────────────────────────────────────
import os as _os
import subprocess as _sp
import re as _re

@app.route("/api/bootstrap", methods=["POST"])
def api_bootstrap():
    """Run agent4 cold bootstrap and return the output."""
    try:
        result = _sp.run(
            ["python3", "agent4_bootstrap.py"],
            capture_output=True, text=True, timeout=15,
            cwd=_os.path.dirname(_os.path.abspath(__file__))
        )
        clean = _re.sub(r'\033\[[0-9;]*m', '', result.stdout)
        return jsonify({"output": clean, "success": True})
    except Exception as e:
        return jsonify({"output": str(e), "success": False})

@app.route("/api/reputation")
def api_reputation():
    """Return agent reputation map from threat ledger."""
    from agent4_bootstrap import read_threat_ledger, build_reputation_map
    threats = read_threat_ledger()
    rep = build_reputation_map(threats)
    return jsonify(rep)

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  SYBIL — Decentralized Agent Immune System")
    print("  ETHGlobal Open Agents Hackathon 2026")
    print("="*60)
    initialize()
    print("\n🌐 Dashboard: http://127.0.0.1:5001")
    print("   Press Ctrl+C to stop\n")
    app.run(host="0.0.0.0", port=5001, debug=False)
