// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SYBILRegistry
 * @notice Agent registration and stake management for the SYBIL immune network.
 *         Agents register with an ENS name + AXL public key and deposit stake.
 *         Stake is locked in SlashingVault. Registry tracks agent metadata and status.
 *
 * ETHGlobal Open Agents 2026 | Andrea Amenta
 */

interface ISlashingVault {
    function deposit(address agent) external payable;
    function slash(address attacker, address victim, address[] calldata validators, uint256 amount) external;
    function getStake(address agent) external view returns (uint256);
}

contract SYBILRegistry {

    // ── Types ──────────────────────────────────────────────────────────────────

    enum AgentStatus { Unregistered, Active, Warned, Slashed, Banned }
    enum AgentRole   { Guardian, Validator, Observer }

    struct Agent {
        string  ensName;        // e.g. "atlas.sybil.eth"
        bytes32 axlPubKey;      // Gensyn AXL ed25519 public key (first 32 bytes)
        AgentRole  role;
        AgentStatus status;
        uint256 attacksDetected;
        uint256 attacksLaunched;
        uint256 votesCast;
        uint256 registeredAt;
        bool    exists;
    }

    // ── Storage ────────────────────────────────────────────────────────────────

    address public owner;
    ISlashingVault public vault;

    mapping(address => Agent)   public agents;
    mapping(string  => address) public ensToAddress;   // ENS name → agent address
    mapping(bytes32 => address) public axlToAddress;   // AXL key  → agent address

    address[] public agentList;

    uint256 public constant MIN_STAKE        = 0.01 ether;
    uint256 public constant SLASH_AMOUNT     = 0.005 ether; // 50% of min stake
    uint256 public constant WARN_THRESHOLD   = 1;  // slashes before WARNED
    uint256 public constant BAN_THRESHOLD    = 3;  // slashes before BANNED

    // ── Events ─────────────────────────────────────────────────────────────────

    event AgentRegistered(address indexed agent, string ensName, bytes32 axlPubKey, AgentRole role);
    event AgentStatusChanged(address indexed agent, AgentStatus oldStatus, AgentStatus newStatus);
    event AgentSlashRecorded(address indexed attacker, uint256 totalSlashes);
    event VaultSet(address vault);

    // ── Modifiers ──────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier onlyVault() {
        require(msg.sender == address(vault), "Not vault");
        _;
    }

    modifier onlyRegistered() {
        require(agents[msg.sender].exists, "Not registered");
        _;
    }

    // ── Constructor ────────────────────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
    }

    // ── Setup ──────────────────────────────────────────────────────────────────

    function setVault(address _vault) external onlyOwner {
        vault = ISlashingVault(_vault);
        emit VaultSet(_vault);
    }

    // ── Registration ───────────────────────────────────────────────────────────

    /**
     * @notice Register as a SYBIL agent. Must send >= MIN_STAKE as deposit.
     * @param ensName  Your ENS name (e.g. "atlas.sybil.eth")
     * @param axlPubKey First 32 bytes of your Gensyn AXL ed25519 public key
     * @param role     Guardian (0), Validator (1), or Observer (2)
     */
    function register(
        string calldata ensName,
        bytes32 axlPubKey,
        AgentRole role
    ) external payable {
        require(!agents[msg.sender].exists,           "Already registered");
        require(msg.value >= MIN_STAKE,               "Insufficient stake");
        require(bytes(ensName).length > 0,            "Empty ENS name");
        require(ensToAddress[ensName] == address(0),  "ENS name taken");
        require(axlToAddress[axlPubKey] == address(0),"AXL key taken");
        require(address(vault) != address(0),         "Vault not set");

        agents[msg.sender] = Agent({
            ensName:         ensName,
            axlPubKey:       axlPubKey,
            role:            role,
            status:          AgentStatus.Active,
            attacksDetected: 0,
            attacksLaunched: 0,
            votesCast:       0,
            registeredAt:    block.timestamp,
            exists:          true
        });

        ensToAddress[ensName]    = msg.sender;
        axlToAddress[axlPubKey] = msg.sender;
        agentList.push(msg.sender);

        // Forward stake to vault
        vault.deposit{value: msg.value}(msg.sender);

        emit AgentRegistered(msg.sender, ensName, axlPubKey, role);
    }

    // ── Called by Vault after slash ────────────────────────────────────────────

    /**
     * @notice Record a slash against an attacker. Called by SlashingVault.
     */
    function recordSlash(address attacker) external onlyVault {
        require(agents[attacker].exists, "Agent not found");

        agents[attacker].attacksLaunched++;

        AgentStatus old = agents[attacker].status;
        AgentStatus next;

        uint256 slashCount = agents[attacker].attacksLaunched;

        if (slashCount >= BAN_THRESHOLD) {
            next = AgentStatus.Banned;
        } else if (slashCount >= WARN_THRESHOLD) {
            next = AgentStatus.Warned;
        } else {
            next = AgentStatus.Active;
        }

        if (next != old) {
            agents[attacker].status = next;
            emit AgentStatusChanged(attacker, old, next);
        }

        emit AgentSlashRecorded(attacker, slashCount);
    }

    /**
     * @notice Record a detection event on victim side.
     */
    function recordDetection(address victim) external onlyVault {
        if (agents[victim].exists) {
            agents[victim].attacksDetected++;
        }
    }

    /**
     * @notice Record a vote cast by a validator.
     */
    function recordVote(address validator) external onlyVault {
        if (agents[validator].exists) {
            agents[validator].votesCast++;
        }
    }

    // ── Views ──────────────────────────────────────────────────────────────────

    function getAgent(address addr) external view returns (Agent memory) {
        return agents[addr];
    }

    function getAgentByENS(string calldata ensName) external view returns (Agent memory, address) {
        address addr = ensToAddress[ensName];
        return (agents[addr], addr);
    }

    function getAgentByAXL(bytes32 axlKey) external view returns (Agent memory, address) {
        address addr = axlToAddress[axlKey];
        return (agents[addr], addr);
    }

    function getAgentCount() external view returns (uint256) {
        return agentList.length;
    }

    function getAllAgents() external view returns (address[] memory) {
        return agentList;
    }

    function isActive(address addr) external view returns (bool) {
        return agents[addr].exists && agents[addr].status == AgentStatus.Active;
    }

    function isBanned(address addr) external view returns (bool) {
        return agents[addr].exists && agents[addr].status == AgentStatus.Banned;
    }
}
