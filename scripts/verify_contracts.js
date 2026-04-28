/**
 * Verify SYBIL contracts on Etherscan
 * Get free API key at: https://etherscan.io/register -> API Keys
 * Add to .env: ETHERSCAN_API_KEY=your_key
 *
 * Run: npx hardhat run scripts/verify_contracts.js --network sepolia
 */

require("dotenv").config();
const hre = require("hardhat");
const fs  = require("fs");

async function main() {
  const dep = JSON.parse(fs.readFileSync("deployments.json", "utf8"));
  const { ThreatLedger, SYBILRegistry, SlashingVault } = dep.contracts;

  console.log("\n" + "=".repeat(60));
  console.log("  SYBIL — Etherscan Verification");
  console.log("=".repeat(60));
  console.log(`ThreatLedger:  ${ThreatLedger}`);
  console.log(`SYBILRegistry: ${SYBILRegistry}`);
  console.log(`SlashingVault: ${SlashingVault}`);
  console.log("\nWaiting 15s for Etherscan to index...");
  await new Promise(r => setTimeout(r, 15000));

  for (const [name, addr, args] of [
    ["ThreatLedger",  ThreatLedger,  []],
    ["SYBILRegistry", SYBILRegistry, []],
    ["SlashingVault", SlashingVault, [SYBILRegistry]],
  ]) {
    console.log(`\nVerifying ${name}...`);
    try {
      await hre.run("verify:verify", {
        address: addr,
        constructorArguments: args,
      });
      console.log(`✓ ${name} verified`);
      console.log(`  https://sepolia.etherscan.io/address/${addr}#code`);
    } catch(e) {
      if (e.message.includes("Already Verified")) {
        console.log(`✓ ${name} already verified`);
      } else {
        console.log(`⚠ ${name}: ${e.message.slice(0, 80)}`);
      }
    }
  }

  console.log("\n✅ Verification complete");
  console.log("\nEtherscan links:");
  console.log(`  ThreatLedger:  https://sepolia.etherscan.io/address/${ThreatLedger}#code`);
  console.log(`  SYBILRegistry: https://sepolia.etherscan.io/address/${SYBILRegistry}#code`);
  console.log(`  SlashingVault: https://sepolia.etherscan.io/address/${SlashingVault}#code`);
}

main().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
