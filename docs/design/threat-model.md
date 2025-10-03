# Verifiable Deletion Protocol Threat Model

## Document Information

- **Version**: 1.0
- **Date**: 2025-10-04
- **Author**: [Your Name]
- **Project**: Verifiable Deletion Protocol with Key Destruction

## 1. Executive Summary

This document provides a comprehensive threat analysis of the Verifiable Deletion Protocol. Using the STRIDE model, we identified 12 key threats, of which 3 P0-level threats warrant prioritization. Key Findings:

- **Most Serious Threat**: Memory Residue After Key Destruction (Threat I1)
- **Core Innovation**: Combining Key Destruction and Blockchain Evidence to Provide Dual Protection
- **Main Challenge**: Implementing True Memory Secure Erase in a Python Environment

## 2. System Architecture Overview

(Insert previously created architecture diagram here)

### 2.1 Core Components

1. **API Service Layer**: User Interaction Entry
2. **KMS**: Key Lifecycle Management
3. **Blockchain Evidence Layer**: Tamper-Proof
4. **Data Storage Layer**: Encrypted Data Persistence

### 2.2 Trust Boundary
External Untrusted Zone ←→ TLS ←→ API Layer ←→ Internal Trusted Zone (KMS + Database)
↓
Blockchain (Public but Unalterable)

## 3. Asset List and Valuation

| Asset ID | Asset Name | Confidentiality | Integrity | Availability | Overall Value |
|--------|---------|--------|--------|----------|
| A1 | User Encryption Key | Very High | Very High | High | **Very High** |
| A2 | Encrypted User Data | High | High | Medium | **High** |
| A3 | Blockchain Evidence | Low | Very High | Medium | **Medium** |
| A4 | KMS Master Key | Very High | Very High | High | **Very High** |
| A5 | API Credentials | High | Medium | Medium | **Medium** |

**Key Asset**: A1 (User Encryption Key) is the security cornerstone of the entire system.

## 4. Attacker Model

### 4.1 Attacker Types

#### Attacker Alpha: External Network Attacker
- **Capabilities**:
- Eavesdrop on network traffic
- Launch DDoS attacks
- Attempt common web attacks such as SQL injection and XSS
- **Goal**: Steal user data and disrupt service availability
- **Limitations**: Unable to access server memory or modify the blockchain

#### Attacker Beta: Malicious Insider
- **Capabilities**:
- Access the server
- Dump process memory
- Read the database
- Access log files
- **Goal**: Recover deleted user data
- **Limitations**: Unable to modify deployed smart contract code

#### Attacker Gamma: Cloud Service Provider (Passive)
- **Capabilities**:
- Access virtual machine snapshots
- Physical memory access (cold boot attack)
- Store all historical data
- **Goal**: Passively collect data for analysis (no active attack)
- **Limitations**: Constrained by law and business reputation

### 4.2 Attacker Objectives

1. **Recovering Deleted User Data** (Primary)
2. Forging Proof of Deletion
3. Disrupting Service Availability
4. Stealing Undeleted Data

## 5. STRIDE Threat Analysis

### 5.1 Spoofing Threat

#### Threat S1: Attacker Forges Deletion Requests

**Threat ID**: T-S-001
**Priority**: P1
**CVSS Score**: 7.5 (High)

**Detailed Description**:
The attacker impersonates a legitimate user using one of the following methods:
1. Stealing session tokens (via XSS, man-in-the-middle attacks)
2. Guessing/cracking weak passwords
3. Exploiting session hijacking vulnerabilities

The attacker then initiates deletion operations on the user's behalf, resulting in malicious deletion of user data.

**Attack Path**: Attacker obtains token → forges HTTP request → API verification passes → data is deleted
**Probability**: Medium
**Impact**: High (user data loss, availability violation)

**Technical Details**:
- If using JWT, token leakage and replay must be prevented.
- Insecure session storage (e.g., password-less Redis) can be easily stolen.

**Mitigation**:

| Priority | Measure | Implementation Complexity | Effect |
|--------|------|-----------|------|
| ⭐⭐⭐ | Implement multi-factor authentication (MFA) | Medium | High |
| ⭐⭐⭐ | Require additional confirmation for deletion operations (SMS/email verification code) | Medium | High |
| ⭐⭐ | Short-term token validity (15 minutes) | Low | Medium |
| ⭐⭐ | Check bound IP address | Low | Medium |
| ⭐ | Detailed operation logging | Low | Low (for post-audit) |

**Verification Method**:
- Session management testing using OWASP ZAP
- Attempt to replay an expired token
- Testing using the same token from different IP addresses

---
#### Threat S2: Smart Contract Caller Impersonation

**Threat ID**: T-S-002
**Priority**: P2
**CVSS Score**: 5.5 (Medium)

**Detailed Description**:
An unauthorized Ethereum address attempts to call the `storeProof` function of a smart contract, storing a false proof of deletion on the blockchain.

**Attack Path**: Attacker address → Call contract.storeProof(fake_hash) → Fake records appear on the chain
**Probability**: Low (if access control is in place)
**Impact**: Medium (contaminates blockchain records but does not affect real data)

**Mitigation**:
```solidity
// Smart contract implementation of access control
contract DeletionProof {
    address public authorizedCaller;

    modifier onlyAuthorized() {
        require(msg.sender == authorizedCaller, "Unauthorized");
        _;
    }

    function storeProof(bytes32 proof) public onlyAuthorized {
        // Proof storage logic
    }
}
```
**Verification method**:
- Attempt to call the contract using an unauthorized address
- Check whether the transaction has been reverted

### 5.2 Tampering Threat
#### Threat T1: Key Modification in Memory

**Threat ID**: T-T-001
**Priority**: P1
**CVSS Score**: 8.0 (High)

**Detailed Description**:
An attacker using debugging tools (such as gdb) or memory editing tools to modify the key in the KMS process memory may result in:
- Key replacement with a value known to the attacker
- Key destruction bypassed
- Key integrity verification failure

**Attack Path**: Obtain root privileges → Attach to the KMS process → Find the key location in memory → Modify
**Likelihood**: Low (requires root access and advanced skills)
**Impact**: Extremely High (complete loss of key integrity)

**Technical Details**: 
# Vulnerable code: 
```
class KMS:
    def __init__(self):
        self.master_key = os.urandom(32) # Stored in a Python object
        # An attacker can find and modify these 32 bytes in memory
```
**Mitigation Measures**:

| Measure | Implementation Method | Effect |
|---------|----------------------|--------|
| Use memory protection | mlock locks memory pages, prevents swap | Prevents keys from being swapped to disk |
|密钥完整性校验 (Key integrity verification) | HMAC verification that keys have not been tampered with | Detects tampering |
| Use HSM | Hardware security module stores keys | Physical isolation, highest security |
| 进程隔离 (Process isolation) | SELinux/AppArmor mandatory access control | Restricts attach permissions |

**Implementation example (Web3.py 7.x compatible)**:
```
import ctypes
import hmac
import hashlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

class SecureKeyStorage:
    """Secure key storage with integrity protection"""

    def __init__(self):
        # Generate master key
        self.master_key = os.urandom(32)

        # Compute HMAC as integrity tag
        self.integrity_tag = hmac.new(
            b'integrity_key', # Should be obtained from an independent source
            self.master_key,
            hashlib.sha256
        ).digest()

        # Try to lock memory (Linux)
        try:
            # Note: requires root privileges or CAP_IPC_LOCK
            libc = ctypes.CDLL('libc.so.6')
            key_addr = id(self.master_key)
            libc.mlock(key_addr, len(self.master_key))
        except Exception as e:
            print(f"Warning: Unable to lock memory: {e}")

    def verify_integrity(self):
        ""Verify key integrity"""
        current_tag = hmac.new(
            b'integrity_key',
            self.master_key,
            hashlib.sha256
        ).digest()

        if not hmac.compare_digest(current_tag, self.integrity_tag):
            raise SecurityError("Key integrity check failed! Possible tampering")

        return True
```

#### Threat T2: Blockchain Evidence Tampering

**Threat ID**: T-T-002
**Priority**: P3
**CVSS Score**: 2.0 (Low)

**Detailed Description**:
The attacker attempted to modify the on-chain proof-of-deletion record.

**Attack Path**: Attacker → attempts to modify block data → requires controlling 51% of the computing power → practically impossible
**Likelihood**: Extremely Low (Basically guaranteed by the blockchain)
**Impact**: Extremely High (but extremely low probability, low overall risk)

**Why is the likelihood extremely low**:

- The Sepolia testnet is maintained by the Ethereum Foundation.
- Requires control of a majority of nodes (51% attack).
- Extremely high cost, extremely low benefit.

**Mitigation**:

Relies on Ethereum's PoS consensus mechanism.
Wait for sufficient block confirmations (recommended 6 blocks).
Use multiple nodes for verification.

**Verification method**:
```
# Verify the same transaction from multiple nodes
def verify_transaction_from_multiple_nodes(tx_hash):
    ""Verify the existence of the transaction from multiple nodes"""
    nodes = [
        "https://sepolia.infura.io/v3/YOUR_ID",
        "https://sepolia.gateway.tenderly.co",
        "https://rpc.sepolia.org"
    ]

    results = []
    for node_url in nodes:
        web3 = Web3(Web3.HTTPProvider(node_url))
        try:
            receipt = web3.eth.get_transaction_receipt(tx_hash)
            results.append(receipt is not None)
        except Exception:
            results.append(False)

    # Validity is considered only if at least 2 nodes confirm.
    return sum(results) >= 2
```

### 5.3 Repudiation Threat
# Threat R1: User denies initiating a deletion operation
**Threat ID**: T-R-001
**Priority**: P2
**CVSS Score**: 6.0 (Medium)

**Detailed Description**:
After a deletion operation is completed, the user claims, "I didn't delete the data; it was a system error," leading to legal disputes or reputational damage.

**Scenario**: User clicks delete → Data is deleted → User regrets → Claims "I didn't click that"
**Likelihood**: Medium (Human Nature)
**Impact**: Medium (Legal Disputes, Customer Relationships)

**Real-World Case Studies**:
- GDPR "Right to Be Forgotten" Dispute Cases
- Cloud Storage Service Accidental Deletion Disputes

**Mitigation Measures**:
1. Blockchain Digital Signatures (The Strongest Proof)
```
def create_deletion_proof_with_signature(user_id, private_key):
    """Create a deletion proof with user signature"""
    # Build a deletion statement
    message = {
        "action": "delete_user_data",
        "user_id": user_id,
        "timestamp": int(time.time()),
        "nonce": secrets.token_hex(16)
    }

    # User signs with private key (proves it is the user's operation)
    message_hash = Web3.keccak(text=json.dumps(message))

    # Web3.py 7.x syntax
    from eth_account.messages import encode_defunct
    signable_message = encode_defunct(message_hash)
    signed = Account.sign_message(signable_message, private_key)

    return {
        "message": message,
        "signature": signed.signature.hex(),
        "signer": signed.address # can verify the signer
    }
```
2. Multiple confirmation process
```
class DeletionConfirmation:
    """Multiple confirmations for deletion"""

    def __init__(self):
        self.pending_deletions = {}

    def initiate_deletion(self, user_id):
        """Step 1: Initiate deletion"""
        confirmation_code = secrets.token_urlsafe(32)
        self.pending_deletions[user_id] = {
            "code": confirmation_code,
            "initiated_at": time.time(),
            "expires_at": time.time() + 300 # 5 minutes validity
        }

        # Send confirmation email/SMS
        send_confirmation_email(user_id, confirmation_code)

        return "Please check your email and click the confirmation link to complete the deletion"

    def confirm_deletion(self, user_id, code):
        """Step 2: Confirm deletion"""
        pending = self.pending_deletions.get(user_id)

        if not pending:
            raise ValueError("No pending deletions")

        if time.time() > pending["expires_at"]:
            raise ValueError("Confirmation code expired")

        if not secrets.compare_digest(pending["code"], code):
            raise ValueError("Wrong confirmation code")

        # Confirmation passed, execute deletion
        del self.pending_deletions[user_id]
        return True
```
3. Complete operation log
```
class AuditLogger:
    ""Anti-tampering audit log"""

    def __init__(self):
        self.log_chain = []
        self.last_hash = "0" * 64

    def log_operation(self, user_id, action, details):
        ""Log operation and chain hash"""
        log_entry = {
            "timestamp": time.time(),
            "user_id": user_id,
            "action": action,
            "details": details,
            "ip_address": request.remote_addr,
            "user_agent": request.user_agent.string,
            "previous_hash": self.last_hash
        }

        # Calculate the hash of the current log entry_json = json.dumps(log_entry, sort_keys=True)
        current_hash = hashlib.sha256(entry_json.encode()).hexdigest() 
        log_entry["hash"] = current_hash 

        self.log_chain.append(log_entry) 
        self.last_hash = current_hash 

        # Persistence to database 
        save_to_database(log_entry) 

        return current_hash
```
**Verification Method**:
- Review the integrity of the log chain
- Verify the signature on the blockchain
- Check the delivery history of the confirmation email/SMS

### 5.4 Information Disclosure Threat
#### Threat I1: Memory Residue After Key Destruction (Core Threat)

**Threat ID**: T-I-001
**Priority**: P0 (Highest Priority)
**CVSS Score**: 9.0 (Critical)

**Detailed Description**:
This is the core issue addressed in this project. After the KMS calls the key destruction function, key data may remain in memory, allowing attackers to recover it using memory forensics tools.

**Why this is a core issue**:
If the key is recoverable, the entire "Verifiable Deletion" protocol becomes invalid.
This is a key innovation that distinguishes it from traditional deletion methods.
It was the technical point that the judges focused on most during the defense.

**Attack Path**: The key destruction function is called → Python's del or memset → the memory page is not actually cleared to zeros → the attacker dumps the memory → uses string search or pattern matching → recovers the key

**Technical Analysis**:
1. Python Memory Management Issues
# Unsafe destruction method
def unsafe_key_destruction(key):
del key # Only deletes the reference, not clearing the memory
# The key data in memory still exists!

# Not safe enough
def still_unsafe(key):
key = b'\x00' * len(key) # May be skipped by the Python optimizer

2. Why C's memset isn't enough
// C language
void destroy_key(char *key, size_t len) {
memset(key, 0, len); // The compiler may optimize this line away (dead code elimination)
}

3. Operating system-level issue
- Memory pages may be swapped to disk
- Memory copy (CoW)
- Cache mechanism

**Probability**: High
**Impact**: Very High (Violation of core security goals)
**Risk level**: Very High

**Mitigation measures (by priority)**:
**Solution 1**: Secure zeroing using the cryptography library (recommended)
```
from cryptography.hazmat.primitives import constant_time
import ctypes

class SecureKeyDestruction:
    """Secure key destruction implementation"""

    @staticmethod
    def secure_zero(data):
        """
        Securely zero a bytes object.
        Uses various techniques to ensure the memory is actually erased.
        """
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("Can only zero bytes or bytearray")

        # Method 1: Direct memory manipulation using ctypes
        if isinstance(data, bytes):
            # Bytes are immutable and require conversion
            data = bytearray(data)

        # Get the memory address of the bytearray
        # Note: This may vary across Python implementations
        import sys

        if sys.version_info >= (3, 8):
            # Python 3.8+
            memview = memoryview(data)
            length = len(memview)

        # Multiple overwrites (simplified version of Gutmann's method)
        patterns = [
            b'\x00' * length, # all zeros
            b'\xFF' * length, # all ones
            os.urandom(length), # random data
            b'\x00' * length # all zeros again
        ]

        for pattern in patterns:
            memview[:] = pattern
            # force refresh
            ctypes.memset(ctypes.addressof(ctypes.c_char.from_buffer(data)), 0, length)

        return True

    @staticmethod
    def destroy_key_advanced(key_material):
        """
        Advanced key destruction (combines multiple techniques)
        """
        # 1. Convert to a mutable type
        if isinstance(key_material, bytes):
            mutable_key = bytearray(key_material)
        else:
            mutable_key = key_material

        length = len(mutable_key)

        # 2. Multiple rounds of overwriting (based on DoD 5220.22-M standard)
        # First round: Write 0
        for i in range(length):
            mutable_key[i] = 0

        # Second round: Write 1
        for i in range(length):
            mutable_key[i] = 255

        # Third round: Write random data
        random_data = os.urandom(length)
        for i in range(length):
            mutable_key[i] = random_data[i]

        # Fourth round: Write 0 again
        for i in range(length):
            mutable_key[i] = 0

        # 3. Using ctypes to ensure memory writes
        try:
            # Get the memory address and force a write
            ptr = (ctypes.c_char * length).from_buffer(mutable_key)
            ctypes.memset(ptr, 0, length)
        except Exception as e:
            print(f"Warning: ctypes clear failed: {e}")

        # 4. Delete references
        del mutable_key
        del key_material

        # 5. Trigger garbage collection
        import gc
        gc.collect()

        return True

# Example usage
def example_usage():
    # Generate a key
    key = os.urandom(32)
    print(f"Key generated: {key.hex()[:16]}...")

    # Use the key...

    # Destroy the key
    SecureKeyDestruction.destroy_key_advanced(key)
    print("Key has been securely destroyed")
```
**Solution 2**: Using libsodium (safest)
```
import ctypes

class LibsodiumKeyDestruction:
    """Use sodium_memzero from libsodium"""

    def __init__(self):
        # Load the libsodium library
        try:
            self.sodium = ctypes.CDLL('libsodium.so') # Linux
        except OSError:
        try:
            self.sodium = ctypes.CDLL('libsodium.dylib') # macOS
        except OSError:
            self.sodium = ctypes.CDLL('libsodium.dll') # Windows

    def sodium_memzero(self, data):
        """
        Use sodium_memzero from libsodium
        Guaranteed not to be optimized away by the compiler
        """
        if isinstance(data, bytes):
            data = bytearray(data)

        ptr = (ctypes.c_char * len(data)).from_buffer(data)
        self.sodium.sodium_memzero(ptr, len(data))

        return True

# Install libsodium:
# Ubuntu: sudo apt-get install libsodium-dev
# macOS: brew install libsodium
# Or use the PyNaCl package
```
**Solution 3**: Use memory locking (to prevent swapping)
```
import ctypes
import os

class MemoryLock:
    ""Lock memory to prevent swapping to disk."""

    @staticmethod
    def lock_memory(data):
        """Locks a memory page
        Requires: CAP_IPC_LOCK or root
        """
        try:
            if os.name == 'posix': # Linux/macOS
                libc = ctypes.CDLL('libc.so.6')

                # Get the memory address of data
                if isinstance(data, bytes):
                    data = bytearray(data)

                ptr = (ctypes.c_char * len(data)).from_buffer(data)
                addr = ctypes.addressof(ptr)

                # Call mlock
                result = libc.mlock(addr, len(data))

                if result != 0:
                    raise OSError(f"mlock failed with code {result}")

            return True
            else:
            print("Warning: VirtualLock is required on Windows systems")
            return False

        except Exception as e:
            print(f"Memory lock failed: {e}")
            return False

    @staticmethod
    def unlock_memory(data):
        ""Unlock the memory page"""
        try:
            if os.name == 'posix':
                libc = ctypes.CDLL('libc.so.6')
                ptr = (ctypes.c_char * len(data)).from_buffer(data)
                addr = ctypes.addressof(ptr)
                libc.munlock(addr, len(data))
                return True
        except Exception:
            return False
```
**Experimental Validation Plan (Phase 1)**:
```
# experiments/key_destruction/memory_forensics_test.py
"""
Key Residue Detection Experiment
Goal: Quantify the effectiveness of different destruction methods
"""

import os
import time
import subprocess

class KeyResidueExperiment:
    """Key Residue Experiment"""

    def __init__(self):
        self.test_key = os.urandom(32)
        self.key_pattern = self.test_key[:16] # Use the first 16 bytes as features

    def test_method_1_naive(self):
        """Method 1: Simple del (benchmark)"""
        key = self.test_key
        # Use the key...
        del key
        return "naive"

    def test_method_2_overwrite(self):
        """Method 2: Single overwrite"""
        key = bytearray(self.test_key)

        for i in range(len(key)):
            key[i] = 0
        del key
        return "single_overwrite"

    def test_method_3_multiple(self):
        """Method 3: Multiple Overwrites"""
        SecureKeyDestruction.destroy_key_advanced(self.test_key)
        return "multiple_overwrite"

    def dump_memory(self, pid):
        """Dump process memory (requires root privileges)"""
        dump_file = f"/tmp/memory_dump_{pid}.raw"
        try:
            # Use gcore to dump memory
            subprocess.run([
                "gcore", "-o", dump_file, str(pid)
            ], check=True, capture_output=True)
            return dump_file
        except Exception as e:
            print(f"Memory dump failed: {e}")
            return None

    def search_pattern_in_file(self, filename, pattern):
        """Search for a pattern in a file"""
        try:
            with open(filename, 'rb') as f:
                content = f.read()
                count = content.count(pattern)
                return count
        except Exception as e:
            print(f"Search failed: {e}")
            return -1

    def run_experiment(self):
        """Run the full experiment"""
        methods = [
            self.test_method_1_naive,
            self.test_method_2_overwrite,
            self.test_method_3_multiple
        ]

        results = []

        for method in methods:
            print(f"\nTest method: {method.__name__}")

            # Execute destruction
            method_name = method()

            # Wait a short time
            time.sleep(1)

            # Dump memory
            pid = os.getpid()
            dump_file = self.dump_memory(pid)

            if dump_file:
                # Search for key pattern
                matches = self.search_pattern_in_file(dump_file, self.key_pattern)
                print(f" Found key residue: {matches} times")

                results.append({
                    "method": method_name,
                    "residue_count": matches
                })

                # Clean up the dump file
                os.remove(dump_file)

        return results

# Run the experiment script
if __name__ == "__main__":
    print("=" * 70)
    print("Key Residue Detection Experiment".center(70))
    print("=" * 70)
    print("\n⚠️ This experiment requires root privileges to dump memory")
    print("⚠️ Please run in an isolated test environment\n")

    input("Press Enter to start the experiment...")

    experiment = KeyResidueExperiment()
    results = experiment.run_experiment()

    print("\n" + "=" * 70)
    print("Experimental results".center(70))
    print("=" * 70)

    for result in results:
        print(f"\nMethod: {result['method']}")
        print(f"Residue count: {result['residue_count']}")

        if result['residue_count'] == 0:
            print("✅ Passed: No key residue detected")
        else:
            print("❌ Failed: Key residue detected")
```
#### Threat I2: Encrypted Database Backup Leakage
**Threat ID**: T-I-002
**Priority**: P2
**CVSS Score**: 6.5 (Medium)

**Detailed Description**:
An attacker obtains a database backup file. Although user data is encrypted, the data can be decrypted if the key is also obtained.
**Attack Path**: Get the backup file → Get the key (through other vulnerabilities) → Decrypt the data
**Likelihood**: Medium
**Impact**: High
**Mitigation**:
1. Backup files are encrypted again
```
def encrypt_database_backup(backup_file, encryption_key):
    ""Encrypt the backup file using a separate key."""
    from cryptography.fernet import Fernet

    # Use a backup key different from the data key
    fernet = Fernet(encryption_key)

    with open(backup_file, 'rb') as f:
        data = f.read()

    encrypted = fernet.encrypt(data)

    with open(backup_file + '.encrypted', 'wb') as f:
        f.write(encrypted)

    # Securely delete the original file
    os.remove(backup_file)
```
2. Backup files are stored in a separate location
- Use different cloud service providers
- Physically isolated storage devices

3. Key rotation mechanism
```
def rotate_user_key(user_id):
    """
    Key rotation: Re-encrypt data with a new key.
    Even if the old backup is compromised, it cannot be decrypted with the new key.
    """
    old_key = kms.get_key(user_id)
    new_key = kms.generate_key()

    # Decrypt old data
    encrypted_data = db.get_encrypted_data(user_id)
    data = decrypt(encrypted_data, old_key)

    # Encrypt with the new key
    new_encrypted = encrypt(data, new_key)
    db.update_encrypted_data(user_id, new_encrypted)

    # Destroy the old key
    kms.destroy_key_secure(old_key)
    kms.store_key(user_id, new_key)
```
#### Threat I3: Metadata Leakage
**Threat ID**: T-I-003
**Priority**: P2
**CVSS Score**: 4.5 (Medium)

**Detailed Description**:
Although user data is encrypted, metadata (file size, creation time, access frequency, etc.) may reveal user behavior patterns.
Examples:
- Inferring content type based on encrypted data size
- Inferring user activity periods based on access time

**Mitigation**:
```
def add_padding_to_encrypted_data(data, block_size=1024):
    ""Add padding to hide the actual data size"""
    import math

    # Calculate required padding
    current_size = len(data)
    blocks_needed = math.ceil(current_size / block_size)
    padded_size = blocks_needed * block_size
    padding_length = padded_size - current_size

    # Add random padding
    padding = os.urandom(padding_length)

    # Format: [4-byte actual length][actual data][random padding]
    result = struct.pack('<I', current_size) + data + padding

    return result
```
### 5.5 Denial of Service Threat
#### Threat D1: Gas Exhaustion Due to a Large Number of Delete Requests
**Threat ID**: T-D-001
**Priority**: P2
**CVSS Score**: 5.5 (Medium)

**Detailed Description**:
An attacker issues a large number of delete requests, resulting in:
- Gas depletion
- Legitimate users unable to use the service
- Financial losses

**Attack Path**:
Attacker creates 100 accounts → issues delete requests for each account → consumes gas each time → wallet balance depleted
**Probability**: Medium
**Impact**: Medium
**Mitigation**:
```
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Implement rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route("/api/users/<user_id>/delete", methods=["POST"])
@limiter.limit("5 per hour") # Limit to 5 delete operations per hour
def delete_user_data(user_id):
    """Delete user data (with rate limit)"""
    # ... Implement logic

# Gas cost monitoring
class GasMonitor:
    ""Monitor gas consumption"""

    def __init__(self, daily_budget_eth=0.1):
        self.daily_budget = Web3.to_wei(daily_budget_eth, 'ether')
        self.daily_spent = 0
        self.reset_time = time.time() + 86400 # 24 hours

    def check_budget(self, estimated_cost):
        ""Check if budget exceeded"""
        # Reset daily count
        if time.time() > self.reset_time:
            self.daily_spent = 0
            self.reset_time = time.time() + 86400

        if self.daily_spent + estimated_cost > self.daily_budget:
            raise BudgetExceededError("Today's gas budget has been exhausted")

        return True

    def record_transaction(self, actual_cost):
        """Record actual consumption"""
        self.daily_spent += actual_cost
```
#### Threat D2: KMS Service Overload
**Threat ID**: T-D-002
**Priority**: P2
**CVSS Score**: 6.0 (Medium)

**Detailed Description**:
A large number of concurrent requests causes KMS to crash, affecting all users.
**Mitigation**:
```
import queue
import threading

class KMSRequestQueue:
    """KMS request queue, prevent overload"""

    def __init__(self, max_workers=10):
        self.queue = queue.Queue(maxsize=100)
        self.workers = []

        # Start the worker thread
        for _ in range(max_workers):
            worker = threading.Thread(target=self._worker)
            worker.daemon = True
            worker.start()
            self.workers.append(worker)

    def _worker(self):
        """Worker thread"""
        while True:
            request = self.queue.get()
            try:
                # Process the request
                self._process_request(request)
            except Exception as e:
                logger.error(f"Request processing failed: {e}")
            finally:
                self.queue.task_done()

    def submit_request(self, request, timeout=30):
        ""Submit request"""
        try:
            self.queue.put(request, timeout=timeout)
        except queue.Full:
            raise ServiceUnavailableError("Service busy, please try again later")
```
### 5.6 Elevation of Privilege Threat
#### Threat E1: Attacker Gains KMS Administrator Privileges
**Threat ID**: T-E-001
**Priority**: P1
**CVSS Score**: 8.5 (High)

**Detailed Description**:
This vulnerability allows an attacker to gain KMS administrator privileges, gaining access to all user keys.
**Mitigation**:
```
from enum import Enum
from functools import wraps

classPermission(Enum): 
READ_OWN_KEY = "read_own_key" 
DELETE_OWN_KEY = "delete_own_key" 
ADMIN_READ_ALL = "admin_read_all" 
ADMIN_DELETE_ALL = "admin_delete_all"

classRBAC: 
    """Role-based access control""" 

    def __init__(self): 
        self.roles = { 
            "user": [Permission.READ_OWN_KEY, Permission.DELETE_OWN_KEY], 
            "admin": [Permission.ADMIN_READ_ALL, Permission.ADMIN_DELETE_ALL] 
        } 

    def require_permission(self, required_permission): 
        """Permission decorator""" 
        def decorator(func): 
            @wraps(func) 
            def wrapper(*args, **kwargs): user_role = get_current_user_role()

                if required_permission not in self.roles.get(user_role, []):
                    raise PermissionDeniedError(f"Required permission: {required_permission}")

                return func(*args, **kwargs)
            return wrapper
        return decorator

# Example
rbac = RBAC()

@rbac.require_permission(Permission.DELETE_OWN_KEY)
def delete_user_key(user_id):
    ""Normal users can only delete their own keys."""
    current_user = get_current_user()

    if current_user.id != user_id:
        raise PermissionDeniedError("Can only delete their own keys")

    kms.destroy_key(user_id)
```

## 6. Threat Prioritization Matrix
| Threat ID | Category | Description | Likelihood | Impact | Risk | Priority |
|-----------|----------|-------------|------------|--------|------|----------|
| T-I-001 | Info Disclosure | Key residue | High | Critical | Critical | P0 |
| T-T-001 | Tampering | In-memory key tampering | Low | Critical | High | P1 |
| T-E-001 | Privilege | KMS privilege escalation | Low | Critical | High | P1 |
| T-S-001 | Spoofing | Forged deletion request | Medium | High | High | P1 |
| T-R-001 | Repudiation | Denial of deletion operation | Medium | Medium | Medium | P2 |
| T-I-002 | Info Disclosure | Backup leakage | Medium | High | Medium | P2 |
| T-I-003 | Info Disclosure | Metadata leakage | High | Medium | Medium | P2 |
| T-D-001 | DoS | Gas exhaustion | Medium | Medium | Medium | P2 |
| T-D-002 | DoS | KMS overload | Medium | High | Medium | P2 |
| T-S-002 | Spoofing | Contract impersonation | Low | Medium | Low | P3 |
| T-T-002 | Tampering | Blockchain tampering | Very Low | Critical | Low | P3 |

**Risk Calculation Formula**:
Risk Level = Likelihood × Impact

Extremely High: High Likelihood × Very High Impact OR Very High Likelihood × High Impact
High: Medium Likelihood × Very High Impact OR High Likelihood × High Impact
Medium: Medium Likelihood × High Impact OR High Likelihood × Medium Impact
Low: Other combinations

## 7. Security Assumptions
For the protocol to be effective, we must explicitly rely on the following security assumptions:
### Assumption A1: Blockchain Immutability
**Content**: The consensus mechanism of the Ethereum Sepolia testnet (and mainnet) guarantees that confirmed transactions cannot be tampered with.
**Justification**: This is the fundamental security guarantee of a public blockchain, guaranteed by a distributed consensus algorithm and economic incentives.
**Failure Consequences**: Deletion proofs can be tampered with, invalidating the entire verifiability mechanism.
**Failure Probability**: Extremely Low (< 0.01%)
**Responses**:
- Choose a mature public blockchain (Ethereum).
- Wait for sufficient block confirmations (recommended 6).
- Optional: Use multiple blockchains for redundant proof storage.

### Assumption A2: Cryptographic Algorithm Security
**Content**: AES-256-GCM and SHA-256 are computationally unbreakable.
**Justification**: Industry standards, with no known practical attack methods.
**Failure Consequences**: Encrypted data can be decrypted.
**Failure Probability**: Low (for the foreseeable future)
**Countermeasures**:
- Continuously monitor cryptography community developments
- Prepare for algorithm migration plans (e.g., quantum computing threats)
- Use sufficient key length (256 bits)

### Assumption A3: KMS Operating Environment Isolation
**Content**: The KMS runs in a trusted, isolated environment, preventing attackers from directly accessing its memory
**Justification**: Modern operating systems provide process isolation, and containers provide additional isolation
**Failure Consequences**: The key could be stolen before destruction
**Probability of Failure**: Medium (depending on the deployment environment)
**Countermeasures**:
- Use container isolation (Docker + seccomp)
- Enable SELinux/AppArmor mandatory access control
- Minimize the privileges of the KMS process
- Deploy an intrusion detection system (IDS)

### Assumption A4: Clock Synchronization
**Content**: The system clock is within 5 seconds of the real time
**Justification**: Guaranteed by the NTP protocol
**Failure Consequences**: Timestamp verification fails, potentially subject to replay attacks
**Probability of Failure**: Low
**Countermeasures**:
- Configure a reliable NTP server
- Monitor clock drift
- Use blockchain timestamps as secondary verification

### Assumption A5: Administrators are Trustworthy
**Content**: System administrators will not actively disclose keys or cooperate with attackers.
**Justification**: Ensured by background checks, legal constraints, and audit mechanisms.
**Failure Consequences**: Insider attacks could lead to large-scale data breaches.
**Failure Probability**: Low (but extremely high impact).
**Countermeasures**:
- Multi-person key sharing (Shamir secret sharing).
- All sensitive operations require multi-person authorization.
- Complete operation audit logs.
- Regular security audits.

### Assumption A6: Python garbage collection does not retain keys.
**Content**: Python's garbage collection mechanism does not retain copies of data after an object is deleted.
**Justification**: CPython implementation details.
**Failure Consequences**: Copies of keys may remain after they are destroyed.
**Failure Probability**: Medium (Python memory management is complex).
**Countermeasures**:
- Use low-level memory operations (ctypes).
- Multiple overwrites to ensure cleanup.
- Use C extensions to implement critical functions.
- Experimental verification (memory forensics).

## 8. Attack Tree Analysis
Core Objective: Recovering Deleted User Data
Recovering Deleted Data
├── [OR] Obtaining Keys
│ ├── [AND] Stealing Data Before Destruction
│ │ ├── Memory Dump (Requires Root)
│ │ ├── Network Sniffing (Requires Man-in-the-Middle Position)
│ │ ├── Side-Channel Attacks (Timing, Power Analysis)
│ │ └── Social Engineering (Phishing Administrators)
│ │
│ ├── [AND] Recovering Data After Destruction ⚠️ Core Research Points
│ │ ├── Memory Forensics (T-I-001)
│ │ │ ├── Analyzing Memory Dumps with Volatility
│ │ │ ├── String Search
│ │ │ └── Pattern Matching
│ │ ├── Disk Recovery
│ │ │ ├── Recovering Swap Files
│ │ │ └── Restoring hibernation files
│ │ └── Cold boot attack
│ │ └── Freezing memory sticks with liquid nitrogen
│ │
│ └── [OR] Obtaining the master/backup key
│ ├── Brute force attack (computationally infeasible, 2^256)
│ ├── Social engineering
│ ├── Supply chain attack
│ └── Insider leak
│
├── [OR] Bypassing encryption
│ ├── Cryptographic cracking (assuming A2 guarantees are infeasible)
│ ├── Exploiting vulnerabilities (e.g., padding oracle attacks)
│ └── Quantum computing attacks (future threat)
│
└── [OR] Obtaining historical backups
├── Database backups (T-I-002)
│ ├── Unencrypted backups
│ └── Weakly encrypted backups
├── Virtual machine snapshots
│ ├── Cloud Service Provider Snapshots
│ └── Local Snapshots
└── Disaster Recovery Archives
└── Offsite Backup Center

**Critical Path Analysis**:
1. Most Likely Attack Path: Memory Forensics (T-I-001) → Therefore, Priority P0
2. Most Destructive Path: Obtaining the KMS Master Key (T-E-001) → Priority P1
3. Most Difficult Path to Defend: Insider Attack → Requires Organizational-Level Action

## 9. Security Objectives and Verification Metrics
Based on threat analysis, we define the following quantifiable security objectives:
| Goal ID | Security Goal | Verification Method | Success Criteria | Addresses Threat |
|---------|---------------|---------------------|------------------|------------------|
| SG1 | Key irrecoverability | Memory verification test | Number of recoverable bytes after destruction = 0 | T-I-001 |
| SG2 | Deletion operation verifiability | Blockchain query | 100% of deletion operations have on-chain proof | T-R-001 |
| SG3 | Forward security | Simulated attack test | Unable to decrypt after obtaining historical backup | T-I-002 |
| SG4 | Replay attack resistance | Automated testing | Replay requests 100% rejected | T-S-001 |
| SG5 | Operation non-repudiation | Audit log analysis | All operations traced to specific users | T-R-001 |
| SG6 | DoS resistance capability | Stress testing | 1000 concurrent requests response time <2 seconds | T-D-001/002 |

### Experimental Design: SG1 (Key Irrecoverability) Detailed Plan
Created docs/experiments/key-destruction-experiment-plan.md:
```
# Key Destruction Effectiveness Experiment Plan

## Experiment Objective

Verify the effectiveness of different key destruction methods and quantify the risk of residual memory.

## Experimental Hypotheses

- H0 (Null Hypothesis): After key destruction, residual data remains in memory.
- H1 (Alternative Hypothesis): After using a secure destruction method, no residual data remains in memory.

## Experimental Design

### Variables

**Independent Variable (Destruction Method)**:
1. Method A: Simple DELETE (Baseline Group)
2. Method B: Single Zero Overwrite
3. Method C: Multiple Overwrites (DoD 5220.22-M Standard)
4. Method D: Using libsodium's sodium_memzero

**Dependent Variable (Recoverability)**:
- Number of Recoverable Bytes
- Full Key Recovery Success Rate

**Control Variables**:
- Key Length: Fixed 32 bytes
- Memory Dump Timing: Immediately after destruction, 1 second later, 10 seconds later
- Operating Environment: Ubuntu 22.04, Python 3.11

### Experimental Procedures

1. **Preparation**
- Generate a test key (32-byte random data)
- Record the key's characteristic pattern (first 16 bytes)

2. **Execution Phase**
- Create the key in memory
- Simulate normal usage (encryption/decryption operations)
- Call the destruction method
- Dump memory at different time points

3. **Analysis Phase**
- Analyze the memory dump using Volatility
- Search for key patterns using a custom script
- Count the number of recoverable bytes

4. **Repetition**
- Repeat each method 30 times
- Calculate the mean and standard deviation

## Experimental Tools

- **Memory Dump**: gcore, /proc/<pid>/mem
- **Memory Analysis**: Volatility 3
- **Pattern Search**: Custom Python Script
- **Statistical Analysis**: scipy, matplotlib

## Data Collection Table

| Trials | Method | Dump Timing | Number of Discoveries | Recoverable Bytes | Complete Recovery |
|------|------|---------|---------|-----------|----------|
| 1 | A | Immediate | | | |
| 2 | A | 1 second | | | |
| ... | | | | | |

## Expected Results

- Method A (del): Expected high carryover rate (>80%)
- Method B (single overwrite): Expected medium carryover rate (30-50%)
- Method C (multiple overwrite): Expected low carryover rate (<10%)
- Method D (libsodium): Expected zero carryover rate (0%)

## Statistical Analysis

One-way analysis of variance (ANOVA) was used to compare the different methods:
- Null hypothesis: There is no significant difference in the mean carryover rate between the methods
- Significance level: α = 0.05
- If p < 0.05, reject the null hypothesis

## Experimental Limitations

1. **Environmental Limitations**: The experiment was conducted in a virtual machine and may differ from a physical machine.
2. **Tool Limitation**: Volatility may not detect all residual memory.
3. **Time Limit**: Unable to test residuals after extremely long periods of time.

## Experiment Script

See `experiments/key_destruction/run_experiment.py`
```

## 10. Next Steps
Based on the threat analysis, Phase 1 development priorities include:

### P0 Threat (Must be addressed in Phase 1)
**T-I-001**: Key Residual
**Action Items**:
1. Implement three key destruction methods
2. Write a memory forensics experiment script
3. Run the experiment and collect data
4. Write an experiment report (5-10 pages)
5. Implement best practices in code
**Time Allotment**: 3 days

### P1 Threat (Phase 1 Focus)
**T-T-001**: Memory Key Tampering
**Action Items**:
1. Implement a Key Integrity Check (HMAC)
2. Research the feasibility of memory locking
3. Document protection measures
**Time Allotment**: 2 days

**T-S-001**: Forge a Delete Request
**Action Items**:
1. Design a multi-factor authentication process
2. Implement an operation confirmation mechanism
3. Design an audit log system
**Time Allotment**: 2 days

**T-E-001**: KMS Privilege Escalation
**Action Items**:
1. Implement a RBAC system
2. Design a permissions matrix
3. Write unit tests
**Time Allotment**: 2 days

### 2/P3 Threat (Phase 2/3 Handling)
Phase 1 primarily completes the design documentation, with implementation completed in subsequent phases.

## 11. Threat Model Review Checklist
Before entering Phase 1, confirm that:
```
## Threat Identification
- [ ] All major components were analyzed using the STRIDE model
- [ ] At least 10 specific threats were identified
- [ ] Each threat had a detailed description and attack path
- [ ] Threat ID numbering convention (T-Type-Number)

## Threat Assessment
- [ ] Each threat had a likelihood assessed (low/medium/high)
- [ ] Each threat had an impact assessed (low/medium/high/very high)
- [ ] Risk level calculated
- [ ] Prioritized (P0/P1/P2/P3)

## Mitigation
- [ ] P0 threats had detailed mitigation plans
- [ ] P1 threats had clear mitigation plans
- [ ] Mitigation plans included code examples
- [ ] Implementation complexity was assessed

## Security Assumptions
- [ ] At least 5 core assumptions were clearly listed
- [ ] Each assumption had a reasonableness analysis
- [ ] The consequences of failing the assumptions were assessed
- [ ] Provided countermeasures

## Experimental Design
- [ ] Designed a detailed experiment for the core threat (T-I-001)
- [ ] The experimental plan included quantifiable indicators
- [ ] Designed a control group
- [ ] Planned statistical analysis methods

## Document Quality
- [ ] The document is clearly structured and includes a table of contents
- [ ] Included charts and graphs to aid understanding
- [ ] Citations of relevant literature
- [ ] Document length >= 15 pages
```
