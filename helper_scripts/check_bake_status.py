"""
Bread SDK - Check Bake Status Helper

Before running this script:
1. Install the SDK: pip install aibread
2. Set your API key: export BREAD_API_KEY='your_api_key_here'
   - Windows CMD: setx BREAD_API_KEY "your_api_key_here"
   - Windows PowerShell: $env:BREAD_API_KEY='your_api_key_here'
3. Configure REPO_NAME and BAKE_NAME below
"""

import os
import dotenv
from aibread import Bread

dotenv.load_dotenv()

# ============ CONFIGURATION ============
REPO_NAME = "your_repo_name"
BAKE_NAME = "your_bake_name"
# =======================================

# Initialize client
client = Bread(api_key=os.environ.get("BREAD_API_KEY"))

# Get bake status
bake_status = client.bakes.get(bake_name=BAKE_NAME, repo_name=REPO_NAME)

print(f"Bake: {BAKE_NAME}")
print(f"Repo: {REPO_NAME}")
print(f"Status: {bake_status.status}")

