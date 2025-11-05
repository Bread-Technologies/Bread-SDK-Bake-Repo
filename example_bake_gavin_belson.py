import os
import sys
import dotenv
import time
from aibread import Bread

dotenv.load_dotenv()

# ============= CONFIGURATION =============
REPO_NAME = "my_first_repo"
TARGET_NAME = "gavin_target"
BAKE_NAME = "gavin_bake"
MODEL_NAME = "Qwen/Qwen3-32B"  # Base model to train
MAX_POLL_ATTEMPTS = 120  # 10 minutes at 5s intervals
POLL_INTERVAL = 5  # seconds between status checks
# ========================================


def log(message, level="INFO"):
    """Simple logging with timestamps"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def poll_job_status(get_status_func, job_type, **kwargs):
    """
    Generic polling function with timeout protection
    
    Args:
        get_status_func: Function to call for status check
        job_type: String describing the job (for logging)
        **kwargs: Arguments to pass to get_status_func
    
    Returns:
        Final status object or None on timeout
    """
    log(f"Polling {job_type} status...")
    
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        try:
            status = get_status_func(**kwargs)
            
            if status.status == "complete":
                log(f"{job_type} complete! Generated {status.lines} items", "SUCCESS")
                return status
            elif status.status == "failed":
                log(f"{job_type} failed. Check your configuration.", "ERROR")
                return None
            
            if attempt % 6 == 0:  # Log every 30 seconds
                log(f"{job_type} status: {status.status} (attempt {attempt}/{MAX_POLL_ATTEMPTS})")
            
            time.sleep(POLL_INTERVAL)
            
        except Exception as e:
            log(f"Error checking {job_type} status: {str(e)}", "ERROR")
            return None
    
    log(f"{job_type} timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL} seconds", "ERROR")
    return None


# Initialize client
try:
    api_key = os.environ.get("BREAD_API_KEY")
    if not api_key:
        log("BREAD_API_KEY not found in environment variables", "ERROR")
        log("Please set it in your .env file or export it in your shell", "ERROR")
        sys.exit(1)
    
    client = Bread(api_key=api_key)
    log("Bread client initialized successfully", "SUCCESS")
    
except Exception as e:
    log(f"Failed to initialize Bread client: {str(e)}", "ERROR")
    sys.exit(1)

# List all existing repos
try:
    repos = client.repo.list()
    log(f"Found {len(repos.items)} existing repositories")
    if repos.items:
        log(f"Existing repos: {[repo.name for repo in repos.items]}")
except Exception as e:
    log(f"Failed to list repositories: {str(e)}", "ERROR")

# ============= STEP 1: CREATE REPOSITORY =============
log("Creating repository...")
try:
    repo = client.repo.set(repo_name=REPO_NAME)
    log(f"Repository '{REPO_NAME}' created/updated successfully", "SUCCESS")
except Exception as e:
    log(f"Failed to create repository: {str(e)}", "ERROR")
    sys.exit(1)

# ============= STEP 2: CREATE PROMPTS =============
log("Creating prompts...")
try:
    # Add your prompt to be baked in OpenAI messages format
    client.prompts.set(
        prompt_name="gavin_belson_prompt",
        repo_name=REPO_NAME,
        messages=[{"role": "system", "content": "You are a Gavin Belson, CEO and founder of Hooli"}]
    )
    log("Created 'gavin_belson_prompt'", "SUCCESS")
    
    # Create a baseline prompt that gets baked into
    # Often times, we set our baseline prompt as a null prompt. This means that any prompt 
    # that gets baked in, gets baked into a model with no initial state
    client.prompts.set(
        prompt_name="baseline_prompt",
        repo_name=REPO_NAME,
        messages=[{"role": "user", "content": ""}]
    )
    log("Created 'baseline_prompt'", "SUCCESS")
    
except Exception as e:
    log(f"Failed to create prompts: {str(e)}", "ERROR")
    sys.exit(1)

# ============= STEP 3: CONFIGURE TARGET =============
log("Configuring target...")
try:
    target = client.targets.set(
        target_name=TARGET_NAME,
        repo_name=REPO_NAME,
        template="default",
        overrides={
            "generators": [
                {
                    "type": "hardcoded",
                    "numq": 3,
                    "questions": [
                        "Hey Gavin, your Signature Box is a terrible product",
                        "Pied Piper 4 Life!",
                        "What is Hooli Nucelus?"
                    ]
                },
            {
                "type": "oneshot_qs",
                "model": "claude-sonnet-4-5-20250929",
                "numq": 50,
                "temperature": 1.0
            }
        ],
        "model_name": MODEL_NAME,
        "u": "gavin_belson_prompt",
        "v": "baseline_prompt"
        }
    )
    log(f"Target '{TARGET_NAME}' configured successfully", "SUCCESS")
except Exception as e:
    log(f"Failed to configure target: {str(e)}", "ERROR")
    sys.exit(1)

# ============= STEP 4: RUN STIM JOB =============
log("Starting stim job...")
try:
    client.targets.stim.run(
        target_name=TARGET_NAME,
        repo_name=REPO_NAME
    )
    log("Stim job started successfully", "SUCCESS")
except Exception as e:
    log(f"Failed to start stim job: {str(e)}", "ERROR")
    sys.exit(1)

# Poll for stim completion
stim_status = poll_job_status(
    client.targets.stim.get,
    "Stim",
    target_name=TARGET_NAME,
    repo_name=REPO_NAME
)

if not stim_status:
    log("Stim job did not complete successfully. Exiting.", "ERROR")
    sys.exit(1)

# ============= STEP 5: REVIEW STIM OUTPUT =============
log("Fetching stim output...")
try:
    output = client.targets.stim.get_output(
        target_name=TARGET_NAME,
        repo_name=REPO_NAME,
        limit=10  # Show first 10 for review
    )
    log(f"Sample of generated stimuli (showing 10 of {stim_status.lines}):")
    for i, stimulus in enumerate(output.output, 1):
        print(f"  {i}. {stimulus}")
except Exception as e:
    log(f"Failed to fetch stim output: {str(e)}", "ERROR")
    log("Continuing anyway...", "WARNING")

# ============= STEP 6: RUN ROLLOUT JOB =============
log("Starting rollout job...")
try:
    client.targets.rollout.run(
        target_name=TARGET_NAME,
        repo_name=REPO_NAME
    )
    log("Rollout job started successfully", "SUCCESS")
except Exception as e:
    log(f"Failed to start rollout job: {str(e)}", "ERROR")
    sys.exit(1)

# Poll for rollout completion
rollout_status = poll_job_status(
    client.targets.rollout.get,
    "Rollout",
    target_name=TARGET_NAME,
    repo_name=REPO_NAME
)

if not rollout_status:
    log("Rollout job did not complete successfully. Exiting.", "ERROR")
    sys.exit(1)

# ============= STEP 7: REVIEW ROLLOUT OUTPUT =============
log("Fetching rollout output...")
try:
    rollout_output = client.targets.rollout.get_output(
        target_name=TARGET_NAME,
        repo_name=REPO_NAME,
        limit=5  # Show first 5 for review
    )
    log(f"Sample of generated trajectories (showing 5 of {rollout_status.lines}):")
    for i, trajectory in enumerate(rollout_output.output, 1):
        print(f"  {i}. {trajectory}")
except Exception as e:
    log(f"Failed to fetch rollout output: {str(e)}", "ERROR")
    log("Continuing anyway...", "WARNING")

# ============= STEP 8: CONFIGURE BAKE =============
log("Configuring bake...")
try:
    bake = client.bakes.set(
        model_name=MODEL_NAME,
        bake_name=BAKE_NAME,
        repo_name=REPO_NAME,
        template="default",
        overrides={
            "datasets": [
                {"target": TARGET_NAME, "weight": 1.0}
            ]
        }
    )
    log(f"Bake '{BAKE_NAME}' configured successfully", "SUCCESS")
except Exception as e:
    log(f"Failed to configure bake: {str(e)}", "ERROR")
    sys.exit(1)

# ============= STEP 9: RUN BAKE =============
log("Starting bake job...")
try:
    result = client.bakes.run(
        bake_name=BAKE_NAME,
        repo_name=REPO_NAME
    )
    log("Bake job started successfully!", "SUCCESS")
    log(f"Your model is now training. This may take 10-20 minutes.", "INFO")
    log(f"Check status with: client.bakes.get(bake_name='{BAKE_NAME}', repo_name='{REPO_NAME}')", "INFO")
except Exception as e:
    log(f"Failed to start bake job: {str(e)}", "ERROR")
    sys.exit(1)

log("Script completed successfully!", "SUCCESS")