// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title DeletionProof
 * @dev 密钥删除存证智能合约
 * 
 * 功能：
 * 1. 记录密钥删除操作的不可篡改证明
 * 2. 提供时间戳和操作详情
 * 3. 支持查询和验证
 * 4. 访问控制
 * 
 * @author Verifiable Deletion Protocol Team
 */
contract DeletionProof {
    
    // ===== 数据结构 =====
    
    /**
     * @dev 删除记录结构体
     */
    struct DeletionRecord {
        string keyId;              // 密钥ID
        string destructionMethod;  // 销毁方法
        uint256 timestamp;         // 删除时间戳
        address operator;          // 操作者地址
        bytes32 proofHash;         // 证明哈希（可选的额外验证）
        bool exists;               // 记录是否存在
    }
    
    // ===== 状态变量 =====
    
    /// @dev 密钥ID到删除记录的映射
    mapping(string => DeletionRecord) private deletionRecords;
    
    /// @dev 所有已记录的密钥ID列表
    string[] private keyIds;
    
    /// @dev 合约所有者
    address public owner;
    
    /// @dev 授权操作者映射
    mapping(address => bool) public authorizedOperators;
    
    /// @dev 总删除记录数
    uint256 public totalDeletions;
    
    // ===== 事件 =====
    
    /**
     * @dev 密钥删除事件
     * @param keyId 密钥ID
     * @param destructionMethod 销毁方法
     * @param timestamp 时间戳
     * @param operator 操作者
     */
    event KeyDeleted(
        string indexed keyId,
        string destructionMethod,
        uint256 timestamp,
        address indexed operator
    );
    
    /**
     * @dev 操作者授权事件
     * @param operator 操作者地址
     * @param authorized 是否授权
     */
    event OperatorAuthorized(
        address indexed operator,
        bool authorized
    );
    
    // ===== 修饰符 =====
    
    /**
     * @dev 仅限所有者
     */
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    /**
     * @dev 仅限授权操作者
     */
    modifier onlyAuthorized() {
        require(
            msg.sender == owner || authorizedOperators[msg.sender],
            "Not authorized"
        );
        _;
    }
    
    /**
     * @dev 密钥必须不存在
     */
    modifier keyMustNotExist(string memory _keyId) {
        require(
            !deletionRecords[_keyId].exists,
            "Key deletion record already exists"
        );
        _;
    }
    
    /**
     * @dev 密钥必须存在
     */
    modifier keyMustExist(string memory _keyId) {
        require(
            deletionRecords[_keyId].exists,
            "Key deletion record does not exist"
        );
        _;
    }
    
    // ===== 构造函数 =====
    
    /**
     * @dev 构造函数，设置合约所有者
     */
    constructor() {
        owner = msg.sender;
        authorizedOperators[msg.sender] = true;
    }
    
    // ===== 核心功能 =====
    
    /**
     * @dev 记录密钥删除操作
     * @param _keyId 密钥ID
     * @param _destructionMethod 销毁方法
     * @param _proofHash 可选的证明哈希
     */
    function recordDeletion(
        string memory _keyId,
        string memory _destructionMethod,
        bytes32 _proofHash
    ) 
        public 
        onlyAuthorized 
        keyMustNotExist(_keyId)
    {
        // 验证输入
        require(bytes(_keyId).length > 0, "Key ID cannot be empty");
        require(bytes(_destructionMethod).length > 0, "Method cannot be empty");
        
        // 创建删除记录
        deletionRecords[_keyId] = DeletionRecord({
            keyId: _keyId,
            destructionMethod: _destructionMethod,
            timestamp: block.timestamp,
            operator: msg.sender,
            proofHash: _proofHash,
            exists: true
        });
        
        // 添加到列表
        keyIds.push(_keyId);
        
        // 增加计数
        totalDeletions++;
        
        // 触发事件
        emit KeyDeleted(
            _keyId,
            _destructionMethod,
            block.timestamp,
            msg.sender
        );
    }
    
    /**
     * @dev 批量记录删除操作（节省gas）
     * @param _keyIds 密钥ID数组
     * @param _destructionMethods 销毁方法数组
     * @param _proofHashes 证明哈希数组
     */
    function batchRecordDeletion(
        string[] memory _keyIds,
        string[] memory _destructionMethods,
        bytes32[] memory _proofHashes
    )
        public
        onlyAuthorized
    {
        require(
            _keyIds.length == _destructionMethods.length &&
            _keyIds.length == _proofHashes.length,
            "Array lengths must match"
        );
        
        require(_keyIds.length > 0, "Arrays cannot be empty");
        require(_keyIds.length <= 100, "Batch size too large"); // 防止gas耗尽
        
        for (uint256 i = 0; i < _keyIds.length; i++) {
            // 检查是否已存在
            if (!deletionRecords[_keyIds[i]].exists) {
                recordDeletion(_keyIds[i], _destructionMethods[i], _proofHashes[i]);
            }
        }
    }
    
    // ===== 查询功能 =====

    /**
     * @dev 获取删除记录
     * @param _keyId 密钥ID
     * @return keyId 密钥ID
     * @return destructionMethod 销毁方法
     * @return timestamp 删除时间戳
     * @return operator 操作者地址
     * @return proofHash 证明哈希
     */
    function getDeletionRecord(string memory _keyId)
        public
        view
        keyMustExist(_keyId)
        returns (
            string memory keyId,
            string memory destructionMethod,
            uint256 timestamp,
            address operator,
            bytes32 proofHash
        )
    {
        DeletionRecord memory record = deletionRecords[_keyId];
        return (
            record.keyId,
            record.destructionMethod,
            record.timestamp,
            record.operator,
            record.proofHash
        );
    }
    
    /**
     * @dev 检查密钥是否已删除
     * @param _keyId 密钥ID
     * @return 是否已删除
     */
    function isKeyDeleted(string memory _keyId) public view returns (bool) {
        return deletionRecords[_keyId].exists;
    }
    
    /**
     * @dev 获取所有密钥ID
     * @return 密钥ID数组
     */
    function getAllKeyIds() public view returns (string[] memory) {
        return keyIds;
    }
    
    /**
     * @dev 获取删除记录总数
     * @return 总数
     */
    function getTotalDeletions() public view returns (uint256) {
        return totalDeletions;
    }
    
    /**
     * @dev 验证删除证明
     * @param _keyId 密钥ID
     * @param _expectedHash 预期的证明哈希
     * @return 是否匹配
     */
    function verifyDeletionProof(
        string memory _keyId,
        bytes32 _expectedHash
    )
        public
        view
        keyMustExist(_keyId)
        returns (bool)
    {
        return deletionRecords[_keyId].proofHash == _expectedHash;
    }
    
    // ===== 访问控制 =====
    
    /**
     * @dev 授权操作者
     * @param _operator 操作者地址
     */
    function authorizeOperator(address _operator) public onlyOwner {
        require(_operator != address(0), "Invalid operator address");
        authorizedOperators[_operator] = true;
        emit OperatorAuthorized(_operator, true);
    }
    
    /**
     * @dev 撤销操作者授权
     * @param _operator 操作者地址
     */
    function revokeOperator(address _operator) public onlyOwner {
        require(_operator != owner, "Cannot revoke owner");
        authorizedOperators[_operator] = false;
        emit OperatorAuthorized(_operator, false);
    }
    
    /**
     * @dev 检查地址是否已授权
     * @param _operator 操作者地址
     * @return 是否授权
     */
    function isAuthorized(address _operator) public view returns (bool) {
        return _operator == owner || authorizedOperators[_operator];
    }
    
    /**
     * @dev 转移所有权
     * @param _newOwner 新所有者地址
     */
    function transferOwnership(address _newOwner) public onlyOwner {
        require(_newOwner != address(0), "Invalid new owner address");
        owner = _newOwner;
        authorizedOperators[_newOwner] = true;
    }
}