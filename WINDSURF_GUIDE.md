# Using AI Career Coach with Windsurf

This guide shows you how to use the AI Career Coach system with **Windsurf's chat interface** - no API keys required!

## 🎯 Overview

Since Windsurf doesn't expose a programmable API, we provide a **manual workflow mode** that:

1. Prepares prompts for each agent
2. You copy/paste them into Windsurf chat
3. You copy/paste Windsurf's responses back
4. The system builds the complete development plan

## 🚀 Quick Start

### Step 1: Run the Workflow Script

```bash
cd CareerBuilder
python windsurf_workflow.py
```

### Step 2: Follow the Interactive Guide

The script will guide you through 3 agent steps:

1. **Feedback Analyzer** - Analyzes 360-degree feedback
2. **Learning Recommender** - Recommends learning resources
3. **Plan Generator** - Creates the 90-day development plan

For each step, you'll:
- Get a prepared prompt
- Paste it into Windsurf chat
- Get the response from Windsurf
- Paste it back into the script

### Step 3: Get Your Development Plan

At the end, you'll have:
- `output_development_plan.md` - Your complete 90-day plan
- All intermediate files for reference

## 📝 Detailed Walkthrough

### Agent 1: Feedback Analyzer

**What happens:**
1. Script shows you a prompt (also saves to `windsurf_prompt_step1.txt`)
2. The prompt includes instructions for analyzing 360-degree feedback
3. You may need to use tools to get feedback data

**Using Tools:**

The script lets you execute tools before copying the prompt to Windsurf:

- **parse_feedback_data(section)** - Get feedback by section
  - Sections: `employee`, `ratings`, `manager`, `peers`, `reports`, `self`, `all`
  - Example: `parse_feedback_data('ratings')`

**In Windsurf:**
1. Copy the prompt from the script
2. Paste into Windsurf chat
3. If you executed tools, also paste the tool results
4. Let Windsurf generate the feedback analysis

**Back to Script:**
1. Copy Windsurf's complete response
2. Paste it into the script when prompted
3. Type `END` on a new line when done
4. Output is saved to `agent1_output.txt`

### Agent 2: Learning Recommender

**What happens:**
1. Script prepares a new prompt that includes Agent 1's output as context
2. Saved to `windsurf_prompt_step2.txt`
3. This agent recommends learning resources

**Using Tools:**

- **match_learning_resources(skills)** - Find learning resources
  - Example: `match_learning_resources('communication, leadership, delegation')`

**Process:**
Same as Agent 1:
1. Copy prompt → Windsurf chat
2. Execute tools if needed
3. Get Windsurf's response
4. Paste back → saved to `agent2_output.txt`

### Agent 3: Plan Generator

**What happens:**
1. Final prompt includes outputs from both previous agents
2. Saved to `windsurf_prompt_step3.txt`
3. This agent creates the comprehensive 90-day plan

**Process:**
1. Copy prompt → Windsurf chat
2. Get the complete development plan from Windsurf
3. Paste back → saved to `agent3_output.txt`
4. Also saved to `output_development_plan.md`

## 💡 Tips for Best Results

### 1. Be Patient
Each agent response can take 30-60 seconds in Windsurf. Don't rush!

### 2. Use Tools Wisely
- For **Agent 1** (Analyzer): Use `parse_feedback_data()` to get all sections
- For **Agent 2** (Recommender): Use `match_learning_resources()` for each skill gap

### 3. Copy Complete Responses
Make sure you copy Windsurf's ENTIRE response, including:
- All sections and subsections
- Tables and lists
- Code blocks
- Everything until the response is complete

### 4. Tool Results Format
If you execute a tool and want to include results in Windsurf:

```
[Your agent prompt from the script]

# Tool Results

TOOL: parse_feedback_data('ratings')
OUTPUT:
{
  "aggregated_ratings": {...},
  "lowest_rated": [...],
  "highest_rated": [...]
}

Now please complete your analysis.
```

### 5. Review as You Go
After each agent:
- Review the output file (agent1_output.txt, agent2_output.txt, agent3_output.txt)
- Make sure it looks complete and useful
- If not satisfied, you can re-run just that step

## 🔧 Advanced Usage

### Resume from a Step

If something goes wrong, you can manually prepare prompts:

```bash
# The prompts are saved as:
# - windsurf_prompt_step1.txt
# - windsurf_prompt_step2.txt
# - windsurf_prompt_step3.txt

# If Agent 2 failed, edit agent1_output.txt if needed, then:
# 1. Look at windsurf_prompt_step2.txt
# 2. Paste into Windsurf
# 3. Save response to agent2_output.txt
# 4. Re-run the script to continue
```

### Customize Agent Behavior

Before running the workflow, edit the agent.md files:

```bash
# Edit agent behaviors
notepad agents/feedback_analyzer.md
notepad agents/learning_recommender.md
notepad agents/plan_generator.md
```

Changes will be reflected in the next workflow run.

### Use Different Feedback Data

Replace the sample data:

```bash
# Backup sample
cp sample_data/feedback_360.json sample_data/feedback_360_sample.json

# Add your data
cp your_feedback.json sample_data/feedback_360.json

# Run workflow
python windsurf_workflow.py
```

## 📊 What You'll Get

### File Structure After Completion

```
CareerBuilder/
├── windsurf_prompt_step1.txt      # Prompt for Agent 1
├── agent1_output.txt              # Agent 1's analysis
├── windsurf_prompt_step2.txt      # Prompt for Agent 2 (includes Agent 1 context)
├── agent2_output.txt              # Agent 2's recommendations
├── windsurf_prompt_step3.txt      # Prompt for Agent 3 (includes all context)
├── agent3_output.txt              # Agent 3's 90-day plan
└── output_development_plan.md     # Final formatted output
```

### Expected Output

`output_development_plan.md` contains:

```markdown
# 90-DAY CAREER DEVELOPMENT PLAN

## EXECUTIVE SUMMARY
- Focus areas and expected outcomes

## DEVELOPMENT GOALS
- 3-4 SMART goals with success metrics

## WEEK-BY-WEEK ROADMAP
- Weeks 1-2: Quick wins
- Weeks 3-6: Core skill building
- Weeks 7-10: Application and practice
- Weeks 11-13: Integration and measurement

## LEARNING RESOURCES SCHEDULE
- Specific resources mapped to timeline

## STRETCH ASSIGNMENTS
- On-the-job practice opportunities

## ACCOUNTABILITY FRAMEWORK
- Check-ins and reflection prompts

## SUCCESS METRICS
- 30, 60, 90-day checkpoints
```

## 🆚 Windsurf Workflow vs. Automated

| Aspect | Windsurf Workflow | Automated (main.py) |
|--------|------------------|---------------------|
| **Setup** | None! | Needs API key or Ollama |
| **Speed** | Manual (15-20 min) | Automated (5-10 min) |
| **Control** | High - review each step | Lower - runs automatically |
| **Cost** | Free (uses Windsurf) | Free (Ollama) or Paid (APIs) |
| **Best For** | No API access, want control | Have APIs, want automation |

## 🐛 Troubleshooting

### "Tool not found" error

Make sure Python can find the tools module:
```bash
# Run from the project root
cd CareerBuilder
python windsurf_workflow.py
```

### Windsurf response too long

If Windsurf's response is very long:
1. Copy in chunks
2. Save each chunk to a text file
3. Combine them before pasting to the script

Or just paste what you have - you can always re-run the step.

### JSON parsing errors in tool results

Some tool outputs are JSON. Make sure to copy the complete JSON structure:
```json
{
  "key": "value",
  "nested": {
    "key2": "value2"
  }
}
```

### Script crashes or freezes

- Press `Ctrl+C` to interrupt
- Check the saved files (agent*_output.txt)
- Re-run the script - it starts from the beginning but you can skip steps

## ✨ Example Workflow

Here's a real example of the workflow:

### Step 1: Start the Script

```bash
$ python windsurf_workflow.py

======================================================================
  AI Career Coach - Windsurf Manual Workflow
======================================================================

Welcome! This guide will help you run the AI Career Coach using
Windsurf's chat interface.

The process:
  1. We'll prepare prompts for each agent
  2. You copy/paste them into Windsurf chat
  3. You copy/paste the responses back here
  4. We'll build the complete development plan

Press Enter to start...
```

### Step 2: Execute Tools (Optional)

```bash
======================================================================
  STEP 1: Feedback Analyzer
======================================================================

Do you need to execute tools before running the agent? (y/n): y

Enter command (1/2/q): 1
Enter section (employee/ratings/manager/peers/reports/self/all): ratings

--- Tool Output ---
{
  "aggregated_ratings": {
    "delegation": 2.8,
    "communication": 3.2,
    ...
  }
}
--- End Tool Output ---

Enter command (1/2/q): q
```

### Step 3: Copy to Windsurf

```bash
======================================================================
  PROMPT TO COPY TO WINDSURF
======================================================================

# 360-Degree Feedback Analyst Agent

## Role
You are a 360-Degree Feedback Analyst...

[Full prompt displayed]
```

**In Windsurf:** Paste and get response

### Step 4: Paste Response Back

```bash
======================================================================
  PASTE AGENT OUTPUT
======================================================================

[You paste Windsurf's response here]
[Keep pasting all the lines]
[When done, type END on a new line]
END

✓ Output saved to: agent1_output.txt
```

### Step 5-6: Repeat for Agents 2 and 3

Same process, but prompts now include previous context!

### Step 7: Get Your Plan

```bash
======================================================================
  WORKFLOW COMPLETE!
======================================================================

✓ Final plan saved to: output_development_plan.md
```

## 🎓 Learning Resources

Want to understand how this works?

1. **Read the agent.md files** - These define each agent's behavior
2. **Look at tools.py** - See what tools agents can use
3. **Check the prompt files** - See what gets sent to Windsurf
4. **Review the output files** - See how agents build on each other

## 🔄 Iterating and Improving

### Try Different Prompts

Edit the agent.md files to:
- Change focus areas
- Add constraints
- Modify output format
- Add more examples

### Experiment with Tool Usage

In the workflow, try:
- Getting all feedback sections vs. specific ones
- Searching for different skill combinations
- Including vs. excluding tool results in prompts

### Compare Results

Run the workflow multiple times:
- With different tool usage patterns
- With edited agent.md files
- See how results vary

---

**Need Help?** Check the main README.md or examine the code - it's simple and well-commented!
