const hre = require("hardhat");

async function main() {
    console.log("开始部署 DeletionProof 合约到 Sepolia 测试网...\n");

    // 获取部署者账户
    const [deployer] = await hre.ethers.getSigners();
    console.log("部署账户:", deployer.address);

    // 查询余额
    const balance = await hre.ethers.provider.getBalance(deployer.address);
    console.log("账户余额:", hre.ethers.formatEther(balance), "ETH\n");

    // 检查余额是否足够
    if (balance === 0n) {
        throw new Error("账户余额为0，无法部署合约！请先从水龙头获取测试ETH");
    }

    // 部署合约
    console.log("正在部署合约...");
    const DeletionProof = await hre.ethers.getContractFactory("DeletionProof");
    const deletionProof = await DeletionProof.deploy();

    await deletionProof.waitForDeployment();
    const contractAddress = await deletionProof.getAddress();

    console.log("\n✅ 合约部署成功！");
    console.log("═══════════════════════════════════════════════════");
    console.log("合约地址:", contractAddress);
    console.log("部署者地址:", deployer.address);
    console.log("网络:", hre.network.name);
    console.log("═══════════════════════════════════════════════════");

    // 验证合约浏览器链接
    console.log("\n🔍 在Etherscan上查看:");
    console.log(`https://sepolia.etherscan.io/address/${contractAddress}`);

    // 保存部署信息到文件
    const fs = require("fs");
    const deploymentInfo = {
        network: hre.network.name,
        contractAddress: contractAddress,
        deployerAddress: deployer.address,
        deployedAt: new Date().toISOString(),
        blockNumber: await hre.ethers.provider.getBlockNumber(),
    };

    fs.writeFileSync(
        "deployment-info.json",
        JSON.stringify(deploymentInfo, null, 2)
    );
    console.log("\n💾 部署信息已保存到 deployment-info.json");

    // 验证初始状态
    console.log("\n📊 验证合约初始状态:");
    console.log("所有者:", await deletionProof.owner());
    console.log("删除记录总数:", (await deletionProof.totalDeletions()).toString());
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("\n❌ 部署失败:");
        console.error(error);
        process.exit(1);
    });