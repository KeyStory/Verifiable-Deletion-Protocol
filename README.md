# Verifiable Deletion Protocol

A verifiable data deletion system based on key destruction and blockchain evidence storage.

## Project Overview

This project implements an innovative data deletion protocol that combines the following technologies:
- Secure key destruction mechanism
- Tamper-proof blockchain evidence storage
- Encrypted user data management
- Application scenarios for online board game platforms

## Quick Start

### Environmental requirements

- Python 3.10+
- Git
- Node.js 16+ (可选)

### Installation steps

1. Clone the repository (or if you are already in the project folder)
```bash
   cd verifiable-deletion-protocol
```
2. Creating a virtual environment
```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
```

3. Install dependencies
```bash
   pip install -r requirements.txt
```

4. Configure environment variables
```bash
   cp .env.example .env
```

5. Verification Environment
```bash
   python scripts/verify_blockchain.py
```

6. Create .vscode/settings.json

Create a .vscode folder and a settings.json file in the project root directory:
```bash
   mkdir .vscode
   New-Item -ItemType File -Path .vscode/settings.json
```

### Project Structure
verifiable-deletion-protocol/
├── docs/              # Documents
├── src/               # Source code
│   ├── kms/           # Key Management Service
│   ├── blockchain/    # Blockchain interaction
│   ├── crypto/        # Encryption module
│   └── api/           # API Services
├── contracts/         # Smart Contracts
├── tests/             # Test
├── scripts/           # Tool Scripts
└── experiments/       # Experimental code

### Development Phase

Phase 0: Environment Setup and Threat Modeling
Phase 1: Core Protocol Implementation
Phase 2: Business Integration
Phase 3: Security Assessment

### License
This project is for academic research only.

### Author
Liang