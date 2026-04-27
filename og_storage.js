/**
 * SYBIL — 0G Storage Bridge (Galileo Testnet V3)
 * Uploads threat records to real 0G Storage
 * Usage: node og_storage.js '<json_record>' '<private_key_no_0x>'
 */

const { MemData, Indexer } = require("@0gfoundation/0g-ts-sdk");
const { ethers } = require("ethers");

// 0G Galileo Testnet V3 endpoints
const RPC_URL     = "https://evmrpc-testnet.0g.ai";
const INDEXER_RPC = "https://indexer-storage-testnet-turbo.0g.ai";

async function uploadThreatRecord(recordJson, privateKey) {
  try {
    const provider = new ethers.JsonRpcProvider(RPC_URL);
    const signer   = new ethers.Wallet(privateKey, provider);

    // Check balance
    const balance    = await provider.getBalance(signer.address);
    const balanceEth = ethers.formatEther(balance);
    if (parseFloat(balanceEth) < 0.0001) {
      return { error: `Insufficient balance: ${balanceEth} OG — get tokens at https://faucet.0g.ai` };
    }

    // Encode record
    const data    = new TextEncoder().encode(JSON.stringify(recordJson, null, 2));
    const memData = new MemData(data);
    const [tree, treeErr] = await memData.merkleTree();
    if (treeErr) return { error: `Merkle error: ${treeErr}` };

    const rootHash = tree.rootHash();

    // Upload to 0G Storage
    const indexer = new Indexer(INDEXER_RPC);
    const [tx, uploadErr] = await indexer.upload(memData, RPC_URL, signer);
    if (uploadErr) return { error: `Upload error: ${uploadErr}` };

    const txHash = tx.txHash || (tx.txHashes && tx.txHashes[0]) || "unknown";

    return {
      success:  true,
      rootHash,
      txHash,
      address:  signer.address,
      url:      `https://storagescan-newton.0g.ai/tx/${txHash}`,
      explorer: `https://chainscan-newton.0g.ai/tx/${txHash}`,
    };
  } catch (err) {
    return { error: err.message };
  }
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.log(JSON.stringify({ error: "Usage: node og_storage.js '<json>' '<privkey>'" }));
    process.exit(1);
  }
  let record;
  try   { record = JSON.parse(args[0]); }
  catch { console.log(JSON.stringify({ error: "Invalid JSON" })); process.exit(1); }

  const result = await uploadThreatRecord(record, args[1]);
  console.log(JSON.stringify(result));
}

main().catch(err => {
  console.log(JSON.stringify({ error: err.message }));
  process.exit(1);
});
