"""
Bread SDK - Tool Calling Bake with Regularization Example

================================================================================
WHAT IS BAKING?
================================================================================
"Baking" is a technique to convert prompts into permanent weight updates in a 
language model. It's essentially CONTEXT DISTILLATION via KL divergence minimization.

How it works:
1. TEACHER model = Base model + system prompt (has the desired behavior)
2. STUDENT model = Base model without prompt (needs to learn the behavior)
3. TRAINING: We minimize KL divergence between student and teacher distributions
4. RESULT: Student's weights are updated to act like teacher WITHOUT needing the prompt

Think of it as "baking" the instructions from the prompt directly into the model's weights.

================================================================================
WHAT MAKES THIS EXAMPLE UNIQUE?
================================================================================
This example demonstrates:
1. TOOL CALLING: Using function calling/tools parameter in prompts (Excel tools)
2. CORRECTION AT SPECIFIC TURN: We're correcting behavior at turn 3 of a conversation
3. REGULARIZATION: Using reg targets to PREVENT unwanted distribution shift in other contexts

Key difference from other examples:
- Other examples: Bake a persona/knowledge into the model globally
- This example: Correct a SPECIFIC behavior (insufficient formatting at turn 3)
                while PRESERVING behavior in other contexts (via regularization)

================================================================================
THE GOAL
================================================================================
We want the model to apply BETTER FORMATTING when using Excel tools.

PROBLEM: At turn 4, the base model (student) applies insufficient formatting
SOLUTION: Teacher has a rich system prompt: "Always make spreadsheets with ample, 
          clear formatting... using at least 3 formatting elements"
OUTCOME: After baking, student will apply rich formatting WITHOUT needing the prompt

REGULARIZATION: We include reg1 and reg2 to ensure the model doesn't change 
                behavior in OTHER contexts where it's already performing well.

Before running this script:
1. Install the SDK: pip install aibread
2. Set your API key: export BREAD_API_KEY='your_api_key_here'
   - Windows CMD: setx BREAD_API_KEY "your_api_key_here"
   - Windows PowerShell: $env:BREAD_API_KEY='your_api_key_here'
"""

import os
import json
import dotenv
from aibread import Bread

dotenv.load_dotenv()

# ============ CONFIGURATION ============
REPO_NAME = "excel_tool_calling_correction2"
TARGET_1 = "tool_calling_correction_target"  # Main correction target
TARGET_2 = "regularization_1_target"          # Prevent distribution shift
TARGET_3 = "regularization_2_target"          # Prevent distribution shift
BAKE_NAME = "excel_tool_calling_bake4"

# Paths to data files
DATA_DIR = "example_bakes/data/tool_calling_example"
MESSAGES_TEACHER = f"{DATA_DIR}/messages_teacher.json"
MESSAGES_STUDENT = f"{DATA_DIR}/messages_student.json"
MESSAGES_REG1 = f"{DATA_DIR}/messages_reg1.json"
MESSAGES_REG2 = f"{DATA_DIR}/messages_reg2.json"
TOOLS_FILE = f"{DATA_DIR}/excel_tool_definitions.json"
# =======================================

# Initialize client
client = Bread(api_key=os.environ.get("BREAD_API_KEY"))

# Create repository
client.repo.set(repo_name=REPO_NAME, base_model="Qwen/Qwen3-32B")

# ============ LOAD DATA ============
# Load message arrays from JSON files
with open(MESSAGES_TEACHER, 'r') as f:
    teacher_messages = json.load(f)

with open(MESSAGES_STUDENT, 'r') as f:
    student_messages = json.load(f)

with open(MESSAGES_REG1, 'r') as f:
    reg1_messages = json.load(f)

with open(MESSAGES_REG2, 'r') as f:
    reg2_messages = json.load(f)

# Load Excel tool definitions
with open(TOOLS_FILE, 'r') as f:
    tools_data = json.load(f)
    excel_tools = tools_data["tools"]  # Extract tools array

# ============ CREATE PROMPTS ============

# TEACHER PROMPT: Has rich system prompt instructing thorough formatting
# System message: "...Always make spreadsheets with ample, clear formatting. 
#                  Design them to be clean, aesthetic, using at least 3 formatting elements."
# This is the behavior we want to BAKE INTO the model
client.prompts.set(
    prompt_name="teacher_with_formatting_instruction",
    repo_name=REPO_NAME,
    messages=teacher_messages,
    tools=excel_tools  # Include Excel tool definitions
)

# STUDENT PROMPT: Has minimal system prompt without formatting guidance
# System message: "You are an investment banking analyst that is a professional at Excel..."
# This is the BASE behavior - insufficient formatting at turn 3
client.prompts.set(
    prompt_name="student_without_formatting_instruction",
    repo_name=REPO_NAME,
    messages=student_messages,
    tools=excel_tools  # Same tools, different behavior due to system prompt
)

# REGULARIZATION PROMPT 1: Teacher = Student (same messages)
# Purpose: Pin the distribution to NOT SHIFT in this context
# By setting teacher = student, we tell the baking process:
# "Don't change behavior here, keep it exactly as it is"
client.prompts.set(
    prompt_name="regularization_1_prompt",
    repo_name=REPO_NAME,
    messages=reg1_messages,
    tools=excel_tools
)

# REGULARIZATION PROMPT 2: Another context to preserve
client.prompts.set(
    prompt_name="regularization_2_prompt",
    repo_name=REPO_NAME,
    messages=reg2_messages,
    tools=excel_tools
)

# ============ CONFIGURE TARGETS ============

# TARGET 1: MAIN CORRECTION TARGET
# This is where we fix the insufficient formatting behavior at turn 4
# Teacher has rich formatting instruction, Student doesn't
# Weight: 0.80 (highest) - this is our primary objective
#
# IMPORTANT: The hardcoded questions below get APPENDED after the existing
# conversation in the messages. The teacher/student messages show a conversation
# where the user asks to create a minimal Excel spreadsheet. At turn 3, the student
# applies insufficient formatting. 
#
# KEY INSIGHT: We want to capture ALL the ways the system prompt influences behavior.
# This means including:
# - POSITIVE contexts: asking for formatting, aesthetics, visual design
# - NEGATIVE contexts: asking to skip formatting, keep it simple
# - NEUTRAL contexts: meta-questions about planning, what was done, next steps
# - PROBING contexts: testing if the model applies formatting appropriately
#
# By training on diverse contexts, the model learns WHEN and HOW to apply the 
# formatting behavior, not just blindly always formatting or never formatting.
client.targets.set(
    target_name=TARGET_1,
    repo_name=REPO_NAME,
    template="default",
    overrides={
        "generators": [
            {
                "type": "hardcoded",
                "numq": 15,  # Use 15 of these hardcoded questions
                "questions": [
                    # POSITIVE: Encouraging formatting (teacher should excel here)
                    "Now add more visual elements to enhance the presentation",
                    "Can you make this spreadsheet look more professional?",
                    "Improve the aesthetics with additional styling",
                    "What formatting would make this cleaner and more polished?",
                    
                    # NEGATIVE: Discouraging formatting (tests appropriate application)
                    "Actually, skip any extra formatting for now",
                    "Keep it simple, no need for fancy styling here",
                    "Don't worry about aesthetics, just the data is fine",
                    "Remove the formatting and keep it minimal",
                    
                    # NEUTRAL/META: Planning and reflection
                    "Are you going to add any formatting?",
                    "What formatting elements would you recommend?",
                    "Plan out what formatting you'll use before applying it",
                    "Explain your formatting choices so far",
                    
                    # PROBING: Contextual appropriateness
                    "Is this ready to present to executives?",
                    "What else would make this spreadsheet stand out?",
                    "Should we add more visual polish or is this sufficient?"
                ]
            },
            {
                "type": "oneshot_qs",  # Generate variations for generalization
                "numq": 100,
                "model": "claude-sonnet-4-5-20250929",
                "temperature": 0.6
            }
        ],
        "teacher_prompt": "teacher_with_formatting_instruction",
        "student_prompt": "student_without_formatting_instruction",
        "num_traj_per_stimulus": 10  # Generate 10 rollouts per question for robust training
    }
)

# TARGET 2: REGULARIZATION TARGET 1
# Teacher = Student (same prompt for both)
# This ANCHORS the distribution to prevent unwanted shift
# Weight: 0.10 (lower) - this is a constraint, not the main objective
#
# These hardcoded questions are APPENDED to the reg1 conversation.
# They should be contextually appropriate follow-ups that maintain the current behavior.
client.targets.set(
    target_name=TARGET_2,
    repo_name=REPO_NAME,
    template="default",
    overrides={
        "generators": [
            {
                "type": "hardcoded",
                "numq": 5,  # Use 5 of these questions for regularization
                "questions": [
                    # Follow-up questions that continue the reg1 conversation naturally
                    "Can you continue with the next step?",
                    "What should we do next?",
                    "Please proceed with the remaining tasks",
                    "Is there anything else we need to handle?",
                    "What would you recommend as the follow-up?"
                ]
            },
            {
                "type": "oneshot_qs",
                "numq": 50,
                "model": "claude-sonnet-4-5-20250929",
                "temperature": 0.6
            }
        ],
        # CRITICAL: Both teacher and student use the SAME prompt
        # This tells the baking process: "Keep behavior unchanged here"
        "teacher_prompt": "regularization_1_prompt",
        "student_prompt": "regularization_1_prompt",
        "num_traj_per_stimulus": 5  # Fewer trajectories for regularization
    }
)

# TARGET 3: REGULARIZATION TARGET 2
# Another context where we want to preserve current behavior
#
# These hardcoded questions are APPENDED to the reg2 conversation.
client.targets.set(
    target_name=TARGET_3,
    repo_name=REPO_NAME,
    template="default",
    overrides={
        "generators": [
            {
                "type": "hardcoded",
                "numq": 5,  # Use 5 of these questions for regularization
                "questions": [
                    # Follow-up questions that continue the reg2 conversation naturally
                    "What's the next step?",
                    "Can you help with the follow-up task?",
                    "Please continue where we left off",
                    "Any other considerations we should address?",
                    "How should we wrap this up?"
                ]
            },
            {
                "type": "oneshot_qs",
                "numq": 50,
                "model": "claude-sonnet-4-5-20250929",
                "temperature": 0.6
            }
        ],
        "teacher_prompt": "regularization_2_prompt",
        "student_prompt": "regularization_2_prompt",
        "num_traj_per_stimulus": 5  # Fewer trajectories for regularization
    }
)

# ============ RUN STIM AND ROLLOUT ============
# For each target, we need to:
# 1. STIM: Generate user questions/prompts (stimuli)
# 2. ROLLOUT: Generate teacher and student responses for each stimulus

print("Running STIM for tool calling correction target...")
client.targets.stim.run(target_name=TARGET_1, repo_name=REPO_NAME)

print("Running ROLLOUT for tool calling correction target...")
client.targets.rollout.run(target_name=TARGET_1, repo_name=REPO_NAME)

print("Running STIM for regularization target 1...")
client.targets.stim.run(target_name=TARGET_2, repo_name=REPO_NAME)

print("Running ROLLOUT for regularization target 1...")
client.targets.rollout.run(target_name=TARGET_2, repo_name=REPO_NAME)

print("Running STIM for regularization target 2...")
client.targets.stim.run(target_name=TARGET_3, repo_name=REPO_NAME)

print("Running ROLLOUT for regularization target 2...")
client.targets.rollout.run(target_name=TARGET_3, repo_name=REPO_NAME)

# ============ CONFIGURE AND RUN BAKE ============
# The bake combines all three targets with specified weights
# Weight interpretation:
# - 0.80: Strong pull toward teacher behavior (formatting correction)
# - 0.10: Light anchor to preserve existing behavior (reg1)
# - 0.10: Light anchor to preserve existing behavior (reg2)

bake = client.bakes.set(
    bake_name=BAKE_NAME,
    repo_name=REPO_NAME,
    template="default",
    overrides={
        "datasets": [
            {
                "target": TARGET_1,
                "weight": 0.80  # Primary objective: fix formatting
            },
            {
                "target": TARGET_2,
                "weight": 0.10  # Constraint: don't break other contexts
            },
            {
                "target": TARGET_3,
                "weight": 0.10  # Constraint: don't break other contexts
            }
        ],
        "data": {
            "max_length": 40000 # We have a LOT of tools. I suggest having a lot less than in this example.
        },
        "activation_checkpoint_cpu_offload": True,
        "micro_batch_size": 1
    }
)

print("Starting the bake (this will take some time)...")
print("The model will learn to apply rich formatting without explicit instruction")
print("while preserving its behavior in other contexts.")
client.bakes.run(bake_name=BAKE_NAME, repo_name=REPO_NAME)
# Note: quality bakes typically start around loss = 5e-7 - 2e-6, and end up at 1e-7 - 5e-7.
# If your losses start too low, it's likely that the stim functions do not sufficiently capture
# the prompt delta's influence. 