// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ThreatLedger
 * @notice Permanent onchain record of all verified threats in the SYBIL network.
 *         This is the "collective memory" — new agents query this to bootstrap
 *         their trust model before their first interaction.
 *
 *         Replaces the 0G Storage mirror for ETH-native storage.
 *         Each threat record is immutable once written.
 *
 * ETHGlobal Open Agents 2026 | Andrea Amenta
 */

contract ThreatLedger {

    // ── Types ──────────────────────────────────────────────────────────────────

    struct ThreatRecord {
        uint256 id;
        address attacker;
        address victim;
        string  attackerENS;
        string  victimENS;
        string  poisonSignature;
        bytes32 proofHash;
        uint256 consensusVotes;
        uint256 consensusTotal;
        bool    slashed;
        uint256 slashAmount;
        uint256 timestamp;
        uint256 blockNumber;
    }

    // ── Storage ────────────────────────────────────────────────────────────────

    address public owner;
    address public vault;          // only vault can write
    address public registry;       // for ENS lookups

    ThreatRecord[] public threats;

    // Reputation index: attacker address → list of threat IDs
    mapping(address => uint256[]) public attackerHistory;
    // Poison signature → threat IDs (detect repeat patterns)
    mapping(bytes32 => uint256[]) public poisonHistory;
    // Trust scores: address → score (starts at 100, decreases with slashes)
    mapping(address => int256) public trustScore;

    uint256 public constant INITIAL_TRUST     = 100;
    int256  public constant SLASH_TRUST_PENALTY = 35;

    // ── Events ─────────────────────────────────────────────────────────────────

    event ThreatRecorded(
        uint256 indexed id,
        address indexed attacker,
        address indexed victim,
        bytes32 proofHash,
        bool slashed,
        uint256 slashAmount
    );
    event TrustUpdated(address indexed agent, int256 newScore);

    // ── Modifiers ──────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier onlyAuthorized() {
        require(msg.sender == vault || msg.sender == owner, "Not authorized");
        _;
    }

    // ── Constructor ────────────────────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
    }

    function setVault(address _vault) external onlyOwner {
        vault = _vault;
    }

    function setRegistry(address _registry) external onlyOwner {
        registry = _registry;
    }

    // ── Write ──────────────────────────────────────────────────────────────────

    /**
     * @notice Record a verified threat. Called by SlashingVault after consensus.
     */
    function recordThreat(
        address attacker,
        address victim,
        string calldata poisonSignature,
        bytes32 proofHash,
        uint256 consensusVotes,
        uint256 consensusTotal,
        bool    slashed,
        uint256 slashAmount
    ) external onlyAuthorized {

        uint256 id = threats.length;

        threats.push(ThreatRecord({
            id:              id,
            attacker:        attacker,
            victim:          victim,
            attackerENS:     "",   // populated off-chain or via registry
            victimENS:       "",
            poisonSignature: poisonSignature,
            proofHash:       proofHash,
            consensusVotes:  consensusVotes,
            consensusTotal:  consensusTotal,
            slashed:         slashed,
            slashAmount:     slashAmount,
            timestamp:       block.timestamp,
            blockNumber:     block.number
        }));

        attackerHistory[attacker].push(id);

        bytes32 poisonKey = keccak256(abi.encodePacked(poisonSignature));
        poisonHistory[poisonKey].push(id);

        // Update trust score
        if (slashed) {
            if (trustScore[attacker] == 0) {
                trustScore[attacker] = int256(INITIAL_TRUST);
            }
            trustScore[attacker] -= SLASH_TRUST_PENALTY;
            if (trustScore[attacker] < 0) trustScore[attacker] = 0;
            emit TrustUpdated(attacker, trustScore[attacker]);
        }

        emit ThreatRecorded(id, attacker, victim, proofHash, slashed, slashAmount);
    }

    /**
     * @notice Update ENS names on a record (called after ENS resolution).
     */
    function updateENSNames(
        uint256 id,
        string calldata attackerENS,
        string calldata victimENS
    ) external onlyAuthorized {
        require(id < threats.length, "Invalid ID");
        threats[id].attackerENS = attackerENS;
        threats[id].victimENS   = victimENS;
    }

    // ── Read ───────────────────────────────────────────────────────────────────

    function getThreat(uint256 id) external view returns (ThreatRecord memory) {
        require(id < threats.length, "Invalid ID");
        return threats[id];
    }

    function getThreatCount() external view returns (uint256) {
        return threats.length;
    }

    function getAttackerHistory(address attacker) external view returns (uint256[] memory) {
        return attackerHistory[attacker];
    }

    function getTrustScore(address agent) external view returns (int256) {
        if (attackerHistory[agent].length == 0) return int256(INITIAL_TRUST);
        return trustScore[agent];
    }

    function isBlacklisted(address agent) external view returns (bool) {
        return trustScore[agent] == 0 && attackerHistory[agent].length > 0;
    }

    /**
     * @notice Returns the full threat history for bootstrap.
     *         A new agent calls this to learn who to trust before first interaction.
     *         This is the "collective memory" function.
     */
    function getBootstrapData() external view returns (
        address[] memory attackers,
        int256[]  memory scores,
        uint256[] memory slashCounts,
        uint256   total
    ) {
        // Collect unique attackers
        address[] memory seen = new address[](threats.length);
        uint256 uniqueCount = 0;

        for (uint256 i = 0; i < threats.length; i++) {
            address a = threats[i].attacker;
            bool found = false;
            for (uint256 j = 0; j < uniqueCount; j++) {
                if (seen[j] == a) { found = true; break; }
            }
            if (!found) seen[uniqueCount++] = a;
        }

        attackers   = new address[](uniqueCount);
        scores      = new int256[](uniqueCount);
        slashCounts = new uint256[](uniqueCount);

        for (uint256 i = 0; i < uniqueCount; i++) {
            attackers[i]   = seen[i];
            scores[i]      = trustScore[seen[i]] == 0 && attackerHistory[seen[i]].length > 0
                             ? int256(0)
                             : (trustScore[seen[i]] == 0 ? int256(INITIAL_TRUST) : trustScore[seen[i]]);
            slashCounts[i] = attackerHistory[seen[i]].length;
        }

        return (attackers, scores, slashCounts, threats.length);
    }

    /**
     * @notice Get recent threats (last N).
     */
    function getRecentThreats(uint256 n) external view returns (ThreatRecord[] memory) {
        uint256 count = threats.length < n ? threats.length : n;
        ThreatRecord[] memory result = new ThreatRecord[](count);
        for (uint256 i = 0; i < count; i++) {
            result[i] = threats[threats.length - count + i];
        }
        return result;
    }
}
