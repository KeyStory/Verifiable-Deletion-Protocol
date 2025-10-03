# System Architecture Diagram

## High-Level Architecture
┌─────────────────────┐
│ User                │
│ (Board Game Player) │
└──────┬──────────────┘
       │ HTTP/HTTPS
       ▼
┌─────────────────────────────────────────────────────┐
│ API Service Layer                                   │
│ ┌────────────────────┐ ┌──────────────────────────┐ │
│ │ User Management    │ │ Delete Protocol API      │ │
│ └────────────────────┘ └──────────────────────────┘ │
└───────┬────────────────┬────────────────────────────┘
        │                │
        ▼                ▼
┌───────────────┐ ┌─────────────────────────┐
│ KMS │ │ Blockchain Evidence Storage Layer │
│ Key Management Service │ │ (Smart Contract) │
│ │ │ │
│ ┌───────────┐ │ │ Sepolia Testnet │
│ │Key Generation │ │ └──────────────────┘
│ │Key Storage │ │ │
│ │Key Destruction │ │ │ Infura
│ └───────────┘ │ ▼
└───────┬───────┘ ┌──────────────────┐
│ │ Ethereum Blockchain │
▼ └────────────────┘
┌───────────────┐
│ Data Storage Layer │
│ (Encrypted Database) │
│ │
│ PostgreSQL │
└────────────────┘

## Data flow graph (for delete operation)
User initiates deletion request
│
▼
API service verifies identity
│
▼
Calls KMS.destroy_key(user_id) ─────┐
│
│
Destroys key
│ (memory overwrite)
│
▼
▼
Generates deletion proof hash. Key is irrecoverable
│
▼
Calls smart contract.storeProof(hash)
│
▼
Wait for blockchain confirmation
│
▼
Returns transaction hash to user

## Component Responsibilities

### API Service Layer
- **Responsibility**: Receive user requests and coordinate components
- **Technology**: Flask
- **Security Requirements**: Authentication, input validation, rate limiting

### KMS (Key Management Service)
- **Responsibility**: Manage the entire lifecycle of user encryption keys
- **Technology**: Python + cryptography library
- **Core Functionality**:
- Key generation (using CSPRNG)
- Key storage (in-memory + optional persistence)
- Key retrieval (access control)
- Key destruction (secure overwrite)
- **Security Requirements**:
- Key destruction is irrecoverable (core goal!)
- Memory isolation
- Access control

### Blockchain Proof of Service Layer
- **Responsibility**: Provide immutable proof of deletion
- **Technology**: Solidity smart contracts + Web3.py
- **Stored content**:
- Hash of deletion operations
- Timestamp
- Operator address
- **Security Requirements**:
- Anti-replay attack
- Access control
- Event logging

### Data storage layer
- **Responsibility**: Store encrypted user data
- **Technology**: PostgreSQL
- **Security requirements**:
- Always store encrypted data
- Encrypted backup files
- Access auditing

## Trust boundary
┌──────────────────────────────────────┐
│ Trusted Zone │
│ ┌──────────┐ ┌──────────┐ │
│ │ KMS │ │ API Service │ │
│ └──────────┘ └──────────┘ │
│ │
└──────────────────────────────────┘
│ TLS Encrypted Communication
▼
┌────────────────────────────────────┐
│ Untrusted Zone │
│ ┌──────────┐ ┌──────────┐ │
│ │ User │ │ Internet │ │
│ └──────────┘ └──────────┘ │
└──────────────────────────────────────┘

## Asset List

| Asset | Value | Storage Location | Protection Measures |
|-----|------|----------|----------|
| User Key | Very High | KMS Memory/Database | Encrypted Storage, Access Control |
| Encrypted User Data | High | PostgreSQL | Key Encryption, Backup Encryption |
| Blockchain Evidence | Medium | Ethereum Blockchain | Blockchain Immutability |
| API Key | Medium | .env File | File Permissions, No Git Submissions |
| Wallet Private Key | High | .env File | File Permissions, Testnet Only |
