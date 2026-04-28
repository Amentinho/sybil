/**
 * Upgrade SYBILRegistry and register sentinel, oracle, warden, cipher
 * Uses adminRegister — all funded from deployer wallet
 *
 * Run: npx hardhat run scripts/register_all_agents.js --network sepolia
 */

require("dotenv").config();
const hre = require("hardhat");

const VAULT_ADDRESS = process.env.SYBIL_VAULT_ADDRESS || "0x9fF5A06A828E9115986FC1EC8bAf92fa2182aF20";
const LEDGER_ADDRESS = process.env.SYBIL_LEDGER_ADDRESS || "0x8A208055787db8B9D399a4D59aBDFF54fB9Ba35B";
const STAKE = hre.ethers.parseEther("0.01");

// Remaining agents to register
// Using deployer as ETH address for all (one wallet setup)
// AXL pubkeys from ~/Projects/axl/ keys
const AGENTS_TO_REGISTER = [
  {
    ensName:   "sentinel.sybil.eth",
    axlPubKey: "0xae8db0e782f37dc4b5d6890c15471431c8cbbef24589a759c2007fde29f94396",
    role:      1, // Validator
    address:   "0x2F7E204F76D47ea69F91Eae548C7C5B39B0Fc1c6", // deployer (same wallet)
  },
  {
    ensName:   "oracle.sybil.eth",
    axlPubKey: "0xedd1eb06fce6a53b7d317df06f23841ad2619c7601a0c4e8cad578f4df66510e",
    role:      1,
    address:   "0x706632e7ABF3aAcC91dCB182A7E071Bc5207253c", // warden wallet (reuse)
  },
  {
    ensName:   "warden.sybil.eth",
    axlPubKey: "0x3a82085b137040fb0000000000000000000000000000000000000000000000000",
    role:      1,
    address:   "0xa3Ef5B942fe857C038A2E90F6f44E790Ef740b46", // cipher wallet
  },
  {
    ensName:   "cipher.sybil.eth",
    axlPubKey: "0x5cc396d7fa2fe5c00000000000000000000000000000000000000000000000000",
    role:      1,
    address:   "0x706632e7ABF3aAcC91dCB182A7E071Bc5207253c",
  },
];

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  console.log("\n" + "=".repeat(60));
  console.log("  SYBIL — Deploy upgraded registry + register all agents");
  console.log("=".repeat(60));

  const bal = await hre.ethers.provider.getBalance(deployer.address);
  console.log(`Deployer: ${deployer.address}`);
  console.log(`Balance:  ${hre.ethers.formatEther(bal)} ETH\n`);

  // ── 1. Deploy new SYBILRegistry with adminRegister ────────────────────────
  console.log("1/3  Deploying upgraded SYBILRegistry...");
  const SYBILRegistry = await hre.ethers.getContractFactory("SYBILRegistry");
  const registry = await SYBILRegistry.deploy();
  await registry.waitForDeployment();
  const registryAddr = await registry.getAddress();
  console.log(`     ✓ New SYBILRegistry: ${registryAddr}`);

  // Wire vault
  let tx = await registry.setVault(VAULT_ADDRESS);
  await tx.wait();
  console.log(`     ✓ Vault wired`);

  // Update vault to point to new registry
  const vaultAbi = ["function registry() view returns (address)"];
  // Note: vault's registry is immutable in constructor, so we just use new registry independently

  // ── 2. Register atlas first (self-register) ───────────────────────────────
  console.log("\n2/3  Registering all 5 agents...");

  // Atlas registers itself
  console.log("  Registering atlas.sybil.eth (self)...");
  try {
    tx = await registry.register(
      "atlas.sybil.eth",
      "0xfc61d174ae8fe29da0735744fe5425cb20171681f544f61f90a9418f27c4d897",
      0, // Guardian
      { value: STAKE }
    );
    const r = await tx.wait();
    console.log(`  ✓ atlas registered | TX: ${r.hash.slice(0,20)}...`);
  } catch(e) {
    console.log(`  ⚠ atlas: ${e.message.slice(0,60)}`);
  }

  // Admin-register remaining agents
  for (const agent of AGENTS_TO_REGISTER) {
    console.log(`  Registering ${agent.ensName}...`);
    try {
      tx = await registry.adminRegister(
        agent.address,
        agent.ensName,
        agent.axlPubKey,
        agent.role,
        { value: STAKE }
      );
      const r = await tx.wait();
      console.log(`  ✓ ${agent.ensName} | TX: ${r.hash.slice(0,20)}...`);
    } catch(e) {
      console.log(`  ⚠ ${agent.ensName}: ${e.message.slice(0,60)}`);
    }
  }

  // ── 3. Verify all registered ──────────────────────────────────────────────
  console.log("\n3/3  Verifying registrations...");
  const allAgents = await registry.getAllAgents();
  console.log(`     ${allAgents.length}/5 agents registered`);
  for (const addr of allAgents) {
    const a = await registry.getAgent(addr);
    const stake = await hre.ethers.provider.getBalance(VAULT_ADDRESS);
    console.log(`     ✓ ${a.ensName} | ${addr.slice(0,10)}... | Active: ${a.status === 1n}`);
  }

  // ── Save new addresses ─────────────────────────────────────────────────────
  console.log("\n" + "=".repeat(60));
  console.log("  Update your .env:");
  console.log("=".repeat(60));
  console.log(`SYBIL_REGISTRY_ADDRESS=${registryAddr}`);
  console.log(`SYBIL_VAULT_ADDRESS=${VAULT_ADDRESS}`);
  console.log(`SYBIL_LEDGER_ADDRESS=${LEDGER_ADDRESS}`);
  console.log("\n✅ Done!\n");

  // Save to deployments.json
  const fs = require("fs");
  const dep = JSON.parse(fs.readFileSync("deployments.json", "utf8"));
  dep.contracts.SYBILRegistry = registryAddr;
  dep.updatedAt = new Date().toISOString();
  fs.writeFileSync("deployments.json", JSON.stringify(dep, null, 2));
}

main().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
