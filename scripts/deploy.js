/**
 * SYBIL Contract Deployment Script
 * Deploys: ThreatLedger → SYBILRegistry → SlashingVault → wires them together
 *
 * Usage:
 *   npx hardhat run scripts/deploy.js --network sepolia
 *   npx hardhat run scripts/deploy.js --network localhost
 */

const hre = require("hardhat");
const fs  = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  console.log("\n" + "=".repeat(60));
  console.log("  SYBIL — Smart Contract Deployment");
  console.log("  ETHGlobal Open Agents 2026");
  console.log("=".repeat(60));
  console.log(`\nDeployer:  ${deployer.address}`);
  console.log(`Network:   ${hre.network.name}`);
  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log(`Balance:   ${hre.ethers.formatEther(balance)} ETH\n`);

  // ── 1. Deploy ThreatLedger ─────────────────────────────────────────────────
  console.log("1/4  Deploying ThreatLedger...");
  const ThreatLedger = await hre.ethers.getContractFactory("ThreatLedger");
  const ledger = await ThreatLedger.deploy();
  await ledger.waitForDeployment();
  const ledgerAddr = await ledger.getAddress();
  console.log(`     ✓ ThreatLedger:   ${ledgerAddr}`);

  // ── 2. Deploy SYBILRegistry ────────────────────────────────────────────────
  console.log("2/4  Deploying SYBILRegistry...");
  const SYBILRegistry = await hre.ethers.getContractFactory("SYBILRegistry");
  const registry = await SYBILRegistry.deploy();
  await registry.waitForDeployment();
  const registryAddr = await registry.getAddress();
  console.log(`     ✓ SYBILRegistry:  ${registryAddr}`);

  // ── 3. Deploy SlashingVault ────────────────────────────────────────────────
  console.log("3/4  Deploying SlashingVault...");
  const SlashingVault = await hre.ethers.getContractFactory("SlashingVault");
  const vault = await SlashingVault.deploy(registryAddr);
  await vault.waitForDeployment();
  const vaultAddr = await vault.getAddress();
  console.log(`     ✓ SlashingVault:  ${vaultAddr}`);

  // ── 4. Wire contracts together ─────────────────────────────────────────────
  console.log("4/4  Wiring contracts...");

  let tx;
  tx = await registry.setVault(vaultAddr);
  await tx.wait();
  console.log("     ✓ Registry → Vault set");

  tx = await vault.setLedger(ledgerAddr);
  await tx.wait();
  console.log("     ✓ Vault → Ledger set");

  tx = await ledger.setVault(vaultAddr);
  await tx.wait();
  console.log("     ✓ Ledger → Vault authorized");

  tx = await ledger.setRegistry(registryAddr);
  await tx.wait();
  console.log("     ✓ Ledger → Registry set");

  // ── 5. Save deployment addresses ──────────────────────────────────────────
  const deployment = {
    network:        hre.network.name,
    deployedAt:     new Date().toISOString(),
    deployer:       deployer.address,
    contracts: {
      ThreatLedger:  ledgerAddr,
      SYBILRegistry: registryAddr,
      SlashingVault: vaultAddr,
    }
  };

  const outPath = path.join(__dirname, "../deployments.json");
  fs.writeFileSync(outPath, JSON.stringify(deployment, null, 2));
  console.log(`\n✓ Deployment saved to deployments.json`);

  // ── 6. Print .env additions ────────────────────────────────────────────────
  console.log("\n" + "=".repeat(60));
  console.log("  Add to your .env:");
  console.log("=".repeat(60));
  console.log(`SYBIL_REGISTRY_ADDRESS=${registryAddr}`);
  console.log(`SYBIL_VAULT_ADDRESS=${vaultAddr}`);
  console.log(`SYBIL_LEDGER_ADDRESS=${ledgerAddr}`);

  // ── 7. Etherscan verification (Sepolia only) ───────────────────────────────
  if (hre.network.name === "sepolia") {
    console.log("\n" + "=".repeat(60));
    console.log("  Verifying on Etherscan (wait 30s for propagation)...");
    console.log("=".repeat(60));
    await new Promise(r => setTimeout(r, 30000));
    try {
      await hre.run("verify:verify", { address: ledgerAddr,   constructorArguments: [] });
      await hre.run("verify:verify", { address: registryAddr, constructorArguments: [] });
      await hre.run("verify:verify", { address: vaultAddr,    constructorArguments: [registryAddr] });
      console.log("✓ All contracts verified on Etherscan");
    } catch (e) {
      console.log("⚠ Etherscan verification failed (non-fatal):", e.message);
    }
  }

  console.log("\n✅ SYBIL contracts deployed successfully!\n");
  return deployment;
}

main()
  .then(() => process.exit(0))
  .catch(err => {
    console.error(err);
    process.exit(1);
  });
