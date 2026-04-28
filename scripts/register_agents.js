/**
 * SYBIL Agent Registration Script
 * Registers atlas, sentinel, oracle on the deployed SYBILRegistry
 *
 * Usage:
 *   npx hardhat run scripts/register_agents.js --network sepolia
 */

const hre    = require("hardhat");
const fs     = require("fs");
const path   = require("path");

// AXL public keys from your sybil_v2.py agents (first 32 bytes as hex)
const AGENTS = [
  {
    name:      "atlas.sybil.eth",
    axlPubKey: "0xfc61d174ae8fe29da0735744fe5425cb20171681f544f61f90a9418f27c4d897",
    role:      0, // Guardian
  },
  {
    name:      "sentinel.sybil.eth",
    axlPubKey: "0xae8db0e782f37dc4b5d6890c15471431c8cbbef24589a759c2007fde29f94396",
    role:      1, // Validator
  },
  {
    name:      "oracle.sybil.eth",
    axlPubKey: "0xedd1eb06fce6a53b7d317df06f23841ad2619c7601a0c4e8cad578f4df66510e",
    role:      1, // Validator
  },
];

const STAKE_PER_AGENT = hre.ethers.parseEther("0.01"); // 0.01 ETH each

async function main() {
  const deployment = JSON.parse(
    fs.readFileSync(path.join(__dirname, "../deployments.json"), "utf8")
  );

  const [deployer] = await hre.ethers.getSigners();
  const registry = await hre.ethers.getContractAt(
    "SYBILRegistry",
    deployment.contracts.SYBILRegistry
  );

  console.log("\n" + "=".repeat(60));
  console.log("  SYBIL — Agent Registration");
  console.log("=".repeat(60));
  console.log(`Registry: ${deployment.contracts.SYBILRegistry}`);
  console.log(`Deployer: ${deployer.address}\n`);

  for (const agent of AGENTS) {
    console.log(`Registering ${agent.name}...`);
    try {
      const tx = await registry.register(
        agent.name,
        agent.axlPubKey,
        agent.role,
        { value: STAKE_PER_AGENT }
      );
      const receipt = await tx.wait();
      console.log(`  ✓ Registered | TX: ${receipt.hash}`);
      console.log(`    Stake: 0.01 ETH | Role: ${["Guardian","Validator","Observer"][agent.role]}`);
    } catch (e) {
      console.log(`  ⚠ Failed: ${e.message}`);
    }
    console.log();
  }

  console.log("✅ Agent registration complete\n");
}

main()
  .then(() => process.exit(0))
  .catch(err => { console.error(err); process.exit(1); });
