# Development Environment Setup Guide

### Prerequisites

- Python 3.10 or higher version
- Git 2.x
- VS Code

### Step 1: Clone the project (if pulling from Git)
```bash
git clone <repository-url>
cd verifiable-deletion-protocol
```
### Step 2: Create a virtual environment
Windows
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure environment variables
```bash
# Copy the template
cp .env.example .env
```
# Edit the .env file and fill in the actual configuration

### Step 5: Verify the environment
```bash
python scripts/verify_setup.py
```


