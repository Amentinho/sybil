// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SlashingVault
 * @notice Holds agent stakes and executes cryptoeconomic slashing on consensus.
 *         When 3/5 validators confirm an attack proof, the attacker is slashed:
 *         - 70% of slash amount burned (disincentive)
 *         - 30% distributed to participating validators (reward)
 *
 * ETHGlobal Open Agents 2026 | Andrea Amenta
 */

interface ISYBILRegistry {
    function recordSlash(address attacker) external;
    function recordDetection(address victim) external;
    function recordVote(address validator) external;
    function isActive(address addr) external view returns (bool);
    function isBanned(address addr) external view returns (bool);
}

interface IThreatLedger {
    function recordThreat(
        address attacker,
        address victim,
        string calldata poisonSignature,
        bytes32 proofHash,
        uint256 consensusVotes,
        uint256 consensusTotal,
        bool slashed,
        uint256 slashAmount
    ) external;
}

contract SlashingVault {

    // ── Types ──────────────────────────────────────────────────────────────────

    struct AttackProof {
        address  attacker;
        address  victim;
        string   poisonSignature;
        bytes32  proofHash;         // keccak256(attacker+victim+poison+timestamp)
        uint256  timestamp;
        bool     executed;
        uint256  votesFor;
        uint256  votesAgainst;
        uint256  totalValidators;
        mapping(address => bool) hasVoted;
        mapping(address => bool) voteValue;
    }

    // ── Storage ────────────────────────────────────────────────────────────────

    address public owner;
    ISYBILRegistry public registry;
    IThreatLedger  public ledger;

    mapping(address => uint256) public stakes;          // agent → stake balance
    mapping(bytes32 => AttackProof) public proofs;      // proofHash → proof
    bytes32[] public proofList;

    // Consensus parameters
    uint256 public constant SLASH_AMOUNT      = 0.005 ether;
    uint256 public constant VALIDATOR_REWARD  = 0.0005 ether; // per validator
    uint256 public constant CONSENSUS_NUMERATOR   = 3;  // 3/5 majority
    uint256 public constant CONSENSUS_DENOMINATOR = 5;

    uint256 public totalSlashed;
    uint256 public totalRewarded;

    // ── Events ─────────────────────────────────────────────────────────────────

    event Deposited(address indexed agent, uint256 amount);
    event ProofSubmitted(bytes32 indexed proofHash, address attacker, address victim, string poison);
    event VoteCast(bytes32 indexed proofHash, address validator, bool vote);
    event ConsensusReached(bytes32 indexed proofHash, bool slashed, uint256 votesFor, uint256 total);
    event Slashed(address indexed attacker, uint256 amount, address[] validators);
    event ValidatorRewarded(address indexed validator, uint256 amount);
    event StakeWithdrawn(address indexed agent, uint256 amount);

    // ── Modifiers ──────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier onlyRegistry() {
        require(msg.sender == address(registry), "Not registry");
        _;
    }

    // ── Constructor ────────────────────────────────────────────────────────────

    constructor(address _registry) {
        owner    = msg.sender;
        registry = ISYBILRegistry(_registry);
    }

    function setLedger(address _ledger) external onlyOwner {
        ledger = IThreatLedger(_ledger);
    }

    // ── Deposits ───────────────────────────────────────────────────────────────

    /**
     * @notice Called by Registry when an agent registers and sends stake.
     */
    function deposit(address agent) external payable {
        require(msg.value > 0, "Zero deposit");
        stakes[agent] += msg.value;
        emit Deposited(agent, msg.value);
    }

    function getStake(address agent) external view returns (uint256) {
        return stakes[agent];
    }

    // ── Attack Proof Submission ────────────────────────────────────────────────

    /**
     * @notice Victim submits a proof of attack after detecting poison on AXL.
     * @param attacker        Address of the attacking agent
     * @param poisonSignature The detected poison string
     * @param proofHash       keccak256(abi.encodePacked(attacker, msg.sender, poisonSig, block.timestamp))
     */
    function submitProof(
        address attacker,
        string calldata poisonSignature,
        bytes32 proofHash
    ) external {
        require(stakes[msg.sender] > 0,       "Victim not staked");
        require(stakes[attacker] > 0,         "Attacker not staked");
        require(!proofs[proofHash].executed,  "Already executed");
        require(proofs[proofHash].timestamp == 0, "Proof exists");

        AttackProof storage p = proofs[proofHash];
        p.attacker        = attacker;
        p.victim          = msg.sender;
        p.poisonSignature = poisonSignature;
        p.proofHash       = proofHash;
        p.timestamp       = block.timestamp;
        p.executed        = false;
        p.votesFor        = 0;
        p.votesAgainst    = 0;

        proofList.push(proofHash);

        emit ProofSubmitted(proofHash, attacker, msg.sender, poisonSignature);
    }

    // ── Validator Voting ───────────────────────────────────────────────────────

    /**
     * @notice Validator casts a signed vote on an attack proof.
     * @param proofHash  The proof to vote on
     * @param vote       true = confirm attack, false = acquit
     * @param validators Full list of active validators (for quorum calculation)
     */
    function castVote(
        bytes32 proofHash,
        bool    vote,
        address[] calldata validators
    ) external {
        AttackProof storage p = proofs[proofHash];
        require(p.timestamp > 0,        "Proof not found");
        require(!p.executed,            "Already executed");
        require(!p.hasVoted[msg.sender],"Already voted");
        require(stakes[msg.sender] > 0, "Validator not staked");

        p.hasVoted[msg.sender]  = true;
        p.voteValue[msg.sender] = vote;
        p.totalValidators       = validators.length;

        if (vote) {
            p.votesFor++;
        } else {
            p.votesAgainst++;
        }

        registry.recordVote(msg.sender);
        emit VoteCast(proofHash, msg.sender, vote);

        // Check if consensus threshold reached
        _checkConsensus(proofHash, validators);
    }

    // ── Internal Consensus Logic ───────────────────────────────────────────────

    function _checkConsensus(bytes32 proofHash, address[] calldata validators) internal {
        AttackProof storage p = proofs[proofHash];
        if (p.executed) return;

        uint256 total = validators.length;
        if (total == 0) return;

        bool slashConsensus   = (p.votesFor    * CONSENSUS_DENOMINATOR >= total * CONSENSUS_NUMERATOR);
        bool acquitConsensus  = (p.votesAgainst * CONSENSUS_DENOMINATOR >= total * CONSENSUS_NUMERATOR);

        if (slashConsensus) {
            p.executed = true;
            emit ConsensusReached(proofHash, true, p.votesFor, total);
            _executeSlash(proofHash, validators);
        } else if (acquitConsensus) {
            p.executed = true;
            emit ConsensusReached(proofHash, false, p.votesFor, total);
        }
    }

    function _executeSlash(bytes32 proofHash, address[] calldata validators) internal {
        AttackProof storage p = proofs[proofHash];

        uint256 slashAmt = SLASH_AMOUNT;
        if (stakes[p.attacker] < slashAmt) {
            slashAmt = stakes[p.attacker]; // slash what's available
        }

        stakes[p.attacker] -= slashAmt;
        totalSlashed += slashAmt;

        // Collect validators who voted YES
        address[] memory yesVoters = new address[](validators.length);
        uint256 yesCount = 0;
        for (uint256 i = 0; i < validators.length; i++) {
            if (p.hasVoted[validators[i]] && p.voteValue[validators[i]]) {
                yesVoters[yesCount++] = validators[i];
            }
        }

        // Distribute rewards: 30% of slash to YES voters equally
        uint256 rewardPool   = (slashAmt * 30) / 100;

        uint256 rewardEach   = yesCount > 0 ? rewardPool / yesCount : 0;
        uint256 actualReward = 0;

        for (uint256 i = 0; i < yesCount; i++) {
            if (rewardEach > 0) {
                stakes[yesVoters[i]] += rewardEach;
                totalRewarded += rewardEach;
                actualReward  += rewardEach;
                emit ValidatorRewarded(yesVoters[i], rewardEach);
            }
            registry.recordVote(yesVoters[i]);
        }

        // Burn remainder (send to zero address equivalent — keep in contract as reserve)
        // In production: send to 0x000...dead or a DAO treasury

        // Notify registry
        registry.recordSlash(p.attacker);
        registry.recordDetection(p.victim);

        // Record in ThreatLedger
        if (address(ledger) != address(0)) {
            ledger.recordThreat(
                p.attacker,
                p.victim,
                p.poisonSignature,
                proofHash,
                p.votesFor,
                p.totalValidators,
                true,
                slashAmt
            );
        }

        emit Slashed(p.attacker, slashAmt, yesVoters);
    }

    // ── Slash called externally (by Python backend for now) ───────────────────

    /**
     * @notice Direct slash entry point — owner/backend calls this with validator list.
     *         Used when Python AXL consensus is already complete.
     */
    function slash(
        address attacker,
        address victim,
        address[] calldata validators,
        uint256 amount
    ) external onlyOwner {
        require(stakes[attacker] >= amount, "Insufficient stake");

        stakes[attacker] -= amount;
        totalSlashed += amount;

        uint256 rewardPool = (amount * 30) / 100;
        uint256 rewardEach = validators.length > 0 ? rewardPool / validators.length : 0;

        for (uint256 i = 0; i < validators.length; i++) {
            if (rewardEach > 0) {
                stakes[validators[i]] += rewardEach;
                totalRewarded += rewardEach;
                emit ValidatorRewarded(validators[i], rewardEach);
            }
        }

        registry.recordSlash(attacker);
        registry.recordDetection(victim);

        emit Slashed(attacker, amount, validators);
    }

    // ── Withdraw ───────────────────────────────────────────────────────────────

    /**
     * @notice Agent withdraws their remaining stake (if not banned).
     */
    function withdraw() external {
        uint256 amount = stakes[msg.sender];
        require(amount > 0, "Nothing to withdraw");
        require(!registry.isBanned(msg.sender), "Banned agents cannot withdraw");

        stakes[msg.sender] = 0;
        (bool ok,) = payable(msg.sender).call{value: amount}("");
        require(ok, "Transfer failed");

        emit StakeWithdrawn(msg.sender, amount);
    }

    // ── Views ──────────────────────────────────────────────────────────────────

    function getProof(bytes32 proofHash) external view returns (
        address attacker,
        address victim,
        string memory poisonSignature,
        uint256 timestamp,
        bool executed,
        uint256 votesFor,
        uint256 votesAgainst,
        uint256 totalValidators
    ) {
        AttackProof storage p = proofs[proofHash];
        return (
            p.attacker, p.victim, p.poisonSignature,
            p.timestamp, p.executed,
            p.votesFor, p.votesAgainst, p.totalValidators
        );
    }

    function getProofCount() external view returns (uint256) {
        return proofList.length;
    }

    function getTotals() external view returns (uint256 slashed, uint256 rewarded) {
        return (totalSlashed, totalRewarded);
    }

    receive() external payable {}
}
