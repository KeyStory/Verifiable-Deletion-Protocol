# Quick Start Guide

This guide will help you get the Verifiable Deletion Protocol running in 5 minutes.

---

## Prerequisites Check

Before starting, ensure you have:

```bash
# Check Python version (need 3.10+)
python --version

# Check Node.js version (need 16+)
node --version

# Check Git
git --version
```

If any are missing, install them first:
- Python: https://www.python.org/downloads/
- Node.js: https://nodejs.org/
- Git: https://git-scm.com/downloads

---

## Step 1: Clone and Setup (2 minutes)

```bash
# Clone repository
git clone https://github.com/KeyStory/Verifiable-Deletion-Protocol.git
cd Verifiable-Deletion-Protocol

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Configure Environment (1 minute)

```bash
# Copy environment template
cp .env.example .env

# Edit .env file
# On Windows:
notepad .env
# On macOS/Linux:
nano .env
```

**Minimum configuration** (for local testing without blockchain):

```env
# .env file
DATABASE_URL=sqlite:///data/demo.db
KMS_KEY_SIZE=32
KMS_DESTRUCTION_METHOD=ctypes_secure
```

**Full configuration** (with blockchain):

```env
# Get Infura API key from: https://infura.io/
INFURA_API_KEY=your_infura_api_key_here

# Your Ethereum wallet private key
WALLET_PRIVATE_KEY=your_private_key_here

# Contract address (provided after deployment)
CONTRACT_ADDRESS=deployed_contract_address

DATABASE_URL=sqlite:///data/demo.db
KMS_KEY_SIZE=32
KMS_DESTRUCTION_METHOD=ctypes_secure
```

---

## Step 3: Run Demo (1 minute)

```bash
# Run the interactive demo
python demo.py
```

You'll see:

```
=================================================================
Verifiable Deletion Protocol - Interactive Demo
=================================================================

Choose a scenario:
  1. Basic Workflow
  2. Method Comparison
  3. Blockchain Verification
  4. Exit

Enter your choice (1-4):
```

### Recommended First Run

**Choose Option 1** (Basic Workflow) to see:
- User registration
- Data encryption
- Key destruction
- Verification that data is unrecoverable

---

## Step 4: Verify Installation (1 minute)

```bash
# Run tests to ensure everything works
pytest tests/unit/ -v
```

Expected output:
```
tests/unit/test_contract_manager.py ✓✓✓✓✓✓✓✓✓✓
tests/unit/test_key_manager.py ✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓

28 passed in 2.3s
```

---

## Troubleshooting

### Issue: "No module named 'src'"
**Solution:**
```bash
# Make sure you're in the project root directory
cd Verifiable-Deletion-Protocol

# Ensure virtual environment is activated
# You should see (venv) in your terminal
```

### Issue: "Database not found"
**Solution:**
```bash
# Create data directory
mkdir data

# The database will be created automatically on first run
python demo.py
```

### Issue: "Infura connection failed"
**Solution**:
```bash
# If you don't have blockchain configured, you can skip it
# Demo will work in local-only mode
# Just leave INFURA_API_KEY empty in .env
```

### Issue: "Permission denied" on Windows
**Solution**:
```bash 
# Run terminal as Administrator
# Or use:
python -m pip install -r requirements.txt
```

### Issue: ctypes not working
**Solution**:
```bash On Linux, you may need:
sudo apt-get install python3-dev

# On macOS:
xcode-select --install
```

## Next Steps
Once demo is running successfully:

1. Explore Different Scenarios
```bash
   python demo.py
   # Try Option 2 (Method Comparison)
   # Try Option 3 (Blockchain Verification)
```

2. Run Visualizations
```bash   
# Generate experiment charts
python visualize_experiment_results.py
   
# Check generated figures
ls docs/figures/
```

3. Read Documentation

- System Architecture
- Encryption Scheme
- Threat Model

4. Run Full Test Suite

```bash   
# All Python tests
pytest

# Smart contract tests
cd contracts
npx hardhat test
```

---

## Common Demo Scenarios

### Scenario 1: Basic Workflow

**What it demonstrates:**
- Complete deletion lifecycle
- Encryption/decryption
- Key destruction
- Data becomes unrecoverable

**Expected output:**
```
✓ User created: user_20251020_123456
✓ Data encrypted and stored
✓ Data decrypted successfully: "My sensitive information"
✓ Key destroyed using ctypes_secure method
✗ Data decryption failed (as expected - key destroyed)
✓ Deletion verified!
```

### Scenario 2: Method Comparison

**What it demonstrates:**
- 4 different destruction methods
- Memory analysis for each
- Security comparison

**Expected output:**
```
Method: basic          | Recoverable: 32.00 bytes | Time: 1.05ms | ❌ INSECURE
Method: memset         | Recoverable: 0.07 bytes  | Time: 1.09ms | ⚠️  MODERATE
Method: ctypes_basic   | Recoverable: 0.10 bytes  | Time: 1.16ms | ✅ GOOD
Method: ctypes_secure  | Recoverable: 0.00 bytes  | Time: 1.13ms | ✅✅ PERFECT
```

### Scenario 3: Blockchain Verification

**What it demonstrates:**
- Smart contract interaction
- On-chain proof recording
- Transaction verification

**Expected output:**
✓ Key destroyed locally
✓ Proof generated: 0x9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
✓ Transaction sent: 0xabc123...
⏳ Waiting for confirmation...
✓ Confirmed in block #12345678
✓ View on Etherscan: https://sepolia.etherscan.io/tx/0xabc123...

**Advanced Configuration**

### Using Different Key Destruction Methods
```Edit .env:
# env# Options: basic | memset | ctypes_basic | ctypes_secure
KMS_DESTRUCTION_METHOD=ctypes_secure
```

### Enabling Debug Logging
```python
# In demo.py or your code, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Using PostgreSQL Instead of SQLite
```env
DATABASE_URL=postgresql://user:password@localhost/deletion_db
```

#### Then install PostgreSQL driver:
```bash
pip install psycopg-binary
```

### Performance Benchmarks
On a typical development machine:
Operation | Time
User Registration | ~5ms
Data Encryption | ~2ms
Data Decryption | ~2ms
Key Destruction (local) | ~1.2ms
Blockchain Confirmation | ~17.5s
Note: Blockchain time varies based on network congestion.

### Getting Help
If you encounter issues:
- Check logs: Look in logs/ directory
- Run diagnostics: python scripts/verify_setup.py
- Read full README: More detailed troubleshooting
- Check documentation: Inline docstrings in source code


### Success Checklist
Before moving on, verify:
- Demo runs without errors
- At least one scenario completes successfully
- Tests pass (pytest)
- Figures generated (if you ran visualization scripts)
- No critical warnings in console

If all checked, you're ready to explore the full system! 🎉

Estimated Total Time: 5 minutes
Difficulty Level: Beginner-friendly
Last Updated: October 20, 2025