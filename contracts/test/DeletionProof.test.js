const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("DeletionProof Contract", function () {
    let deletionProof;
    let owner;
    let operator1;
    let operator2;

    // 在每个测试前部署新合约
    beforeEach(async function () {
        [owner, operator1, operator2] = await ethers.getSigners();

        const DeletionProof = await ethers.getContractFactory("DeletionProof");
        deletionProof = await DeletionProof.deploy();
        await deletionProof.waitForDeployment();
    });

    describe("部署", function () {
        it("应该设置正确的所有者", async function () {
            expect(await deletionProof.owner()).to.equal(owner.address);
        });

        it("应该将所有者设为授权操作者", async function () {
            expect(await deletionProof.isAuthorized(owner.address)).to.be.true;
        });

        it("应该初始化删除计数为0", async function () {
            expect(await deletionProof.totalDeletions()).to.equal(0);
        });
    });

    describe("访问控制", function () {
        it("所有者可以授权新操作者", async function () {
            await deletionProof.authorizeOperator(operator1.address);
            expect(await deletionProof.isAuthorized(operator1.address)).to.be.true;
        });

        it("应该触发OperatorAuthorized事件", async function () {
            await expect(deletionProof.authorizeOperator(operator1.address))
                .to.emit(deletionProof, "OperatorAuthorized")
                .withArgs(operator1.address, true);
        });

        it("所有者可以撤销操作者权限", async function () {
            await deletionProof.authorizeOperator(operator1.address);
            await deletionProof.revokeOperator(operator1.address);
            expect(await deletionProof.isAuthorized(operator1.address)).to.be.false;
        });

        it("非所有者不能授权操作者", async function () {
            await expect(
                deletionProof.connect(operator1).authorizeOperator(operator2.address)
            ).to.be.revertedWith("Only owner can call this function");
        });

        it("不能撤销所有者的权限", async function () {
            await expect(
                deletionProof.revokeOperator(owner.address)
            ).to.be.revertedWith("Cannot revoke owner");
        });
    });

    describe("记录删除", function () {
        const keyId = "key_test_12345";
        const method = "dod_overwrite";
        const proofHash = ethers.keccak256(ethers.toUtf8Bytes("test_proof"));

        it("授权者可以记录删除", async function () {
            await deletionProof.recordDeletion(keyId, method, proofHash);

            const record = await deletionProof.getDeletionRecord(keyId);
            expect(record.keyId).to.equal(keyId);
            expect(record.destructionMethod).to.equal(method);
            expect(record.proofHash).to.equal(proofHash);
        });

        it("应该触发KeyDeleted事件", async function () {
            await expect(deletionProof.recordDeletion(keyId, method, proofHash))
                .to.emit(deletionProof, "KeyDeleted")
                .withArgs(keyId, method, await ethers.provider.getBlock('latest').then(b => b.timestamp + 1), owner.address);
        });

        it("应该增加删除计数", async function () {
            await deletionProof.recordDeletion(keyId, method, proofHash);
            expect(await deletionProof.totalDeletions()).to.equal(1);
        });

        it("非授权者不能记录删除", async function () {
            await expect(
                deletionProof.connect(operator1).recordDeletion(keyId, method, proofHash)
            ).to.be.revertedWith("Not authorized");
        });

        it("不能记录重复的密钥ID", async function () {
            await deletionProof.recordDeletion(keyId, method, proofHash);
            await expect(
                deletionProof.recordDeletion(keyId, method, proofHash)
            ).to.be.revertedWith("Key deletion record already exists");
        });

        it("不能记录空密钥ID", async function () {
            await expect(
                deletionProof.recordDeletion("", method, proofHash)
            ).to.be.revertedWith("Key ID cannot be empty");
        });

        it("不能记录空销毁方法", async function () {
            await expect(
                deletionProof.recordDeletion(keyId, "", proofHash)
            ).to.be.revertedWith("Method cannot be empty");
        });
    });

    describe("批量记录删除", function () {
        it("可以批量记录多个删除操作", async function () {
            const keyIds = ["key_1", "key_2", "key_3"];
            const methods = ["method_1", "method_2", "method_3"];
            const proofHashes = [
                ethers.keccak256(ethers.toUtf8Bytes("proof_1")),
                ethers.keccak256(ethers.toUtf8Bytes("proof_2")),
                ethers.keccak256(ethers.toUtf8Bytes("proof_3"))
            ];

            await deletionProof.batchRecordDeletion(keyIds, methods, proofHashes);

            expect(await deletionProof.totalDeletions()).to.equal(3);
            expect(await deletionProof.isKeyDeleted("key_1")).to.be.true;
            expect(await deletionProof.isKeyDeleted("key_2")).to.be.true;
            expect(await deletionProof.isKeyDeleted("key_3")).to.be.true;
        });

        it("数组长度必须匹配", async function () {
            const keyIds = ["key_1", "key_2"];
            const methods = ["method_1"];
            const proofHashes = [ethers.keccak256(ethers.toUtf8Bytes("proof_1"))];

            await expect(
                deletionProof.batchRecordDeletion(keyIds, methods, proofHashes)
            ).to.be.revertedWith("Array lengths must match");
        });

        it("批量大小不能超过100", async function () {
            const keyIds = Array(101).fill("key");
            const methods = Array(101).fill("method");
            const proofHashes = Array(101).fill(ethers.keccak256(ethers.toUtf8Bytes("proof")));

            await expect(
                deletionProof.batchRecordDeletion(keyIds, methods, proofHashes)
            ).to.be.revertedWith("Batch size too large");
        });
    });

    describe("查询功能", function () {
        const keyId = "key_test_query";
        const method = "dod_overwrite";
        const proofHash = ethers.keccak256(ethers.toUtf8Bytes("test_proof"));

        beforeEach(async function () {
            await deletionProof.recordDeletion(keyId, method, proofHash);
        });

        it("可以获取删除记录", async function () {
            const record = await deletionProof.getDeletionRecord(keyId);
            expect(record.keyId).to.equal(keyId);
            expect(record.destructionMethod).to.equal(method);
            expect(record.operator).to.equal(owner.address);
            expect(record.proofHash).to.equal(proofHash);
        });

        it("可以检查密钥是否已删除", async function () {
            expect(await deletionProof.isKeyDeleted(keyId)).to.be.true;
            expect(await deletionProof.isKeyDeleted("non_existent")).to.be.false;
        });

        it("可以获取所有密钥ID", async function () {
            const allKeys = await deletionProof.getAllKeyIds();
            expect(allKeys).to.include(keyId);
            expect(allKeys.length).to.equal(1);
        });

        it("查询不存在的记录应该失败", async function () {
            await expect(
                deletionProof.getDeletionRecord("non_existent")
            ).to.be.revertedWith("Key deletion record does not exist");
        });
    });

    describe("验证删除证明", function () {
        const keyId = "key_test_verify";
        const method = "dod_overwrite";
        const proofHash = ethers.keccak256(ethers.toUtf8Bytes("test_proof"));

        beforeEach(async function () {
            await deletionProof.recordDeletion(keyId, method, proofHash);
        });

        it("可以验证正确的证明哈希", async function () {
            expect(await deletionProof.verifyDeletionProof(keyId, proofHash)).to.be.true;
        });

        it("错误的证明哈希应该验证失败", async function () {
            const wrongHash = ethers.keccak256(ethers.toUtf8Bytes("wrong_proof"));
            expect(await deletionProof.verifyDeletionProof(keyId, wrongHash)).to.be.false;
        });
    });

    describe("转移所有权", function () {
        it("所有者可以转移所有权", async function () {
            await deletionProof.transferOwnership(operator1.address);
            expect(await deletionProof.owner()).to.equal(operator1.address);
        });

        it("新所有者应该自动获得授权", async function () {
            await deletionProof.transferOwnership(operator1.address);
            expect(await deletionProof.isAuthorized(operator1.address)).to.be.true;
        });

        it("非所有者不能转移所有权", async function () {
            await expect(
                deletionProof.connect(operator1).transferOwnership(operator2.address)
            ).to.be.revertedWith("Only owner can call this function");
        });

        it("不能转移到零地址", async function () {
            await expect(
                deletionProof.transferOwnership(ethers.ZeroAddress)
            ).to.be.revertedWith("Invalid new owner address");
        });
    });
});