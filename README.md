# AI Career Development & Performance Coach

A multi-agent AI system that transforms career input — performance reviews, peer feedback, aspirations, or even a simple email — into actionable, schedule-aware career development plans.

**This version uses agent.md files** instead of the CrewAI framework, with direct LLM API calls. It's framework-free, simple, and flexible. It ships with both a **CLI** and a **Streamlit web UI**.

## What It Does

Accepts any combination of career-related input and produces:

1. **Career Input Analysis** - Synthesizes feedback from any source (360 reviews, emails, free-text, file uploads)
2. **Learning Pathway with Links** - Matches skill gaps to curated resources with direct course URLs
3. **Schedule Analysis** - Parses your calendar or availability to find realistic learning windows
4. **Custom-Timeline Development Plan** - Creates a structured, schedule-aware roadmap (30-365 days, default 90) with bite-sized activities
5. **Visual Progress Dashboard** - Interactive charts, phase tracker, and weekly task management

## Architecture

### Key Differences from CrewAI Version

| Aspect | CrewAI Version | This Version |
|--------|---------------|--------------|
| **Framework** | Requires CrewAI | No framework - pure Python |
| **Agent Definition** | Python classes | Markdown `.md` files |
| **LLM Backend** | OpenAI only | Anthropic Claude, Ollama, or OpenAI |
| **Agents** | 3-agent pipeline | 4-agent pipeline (+ schedule analyzer) |
| **Input** | 360 JSON only | Email, text, files, schedule data |
| **Interface** | CLI only | CLI + Streamlit web UI |
| **Complexity** | Higher abstraction | Simple, transparent |

### Project Structure

```
career_coach_no_crew/
├── agents/                            # Agent behavior definitions
│   ├── feedback_analyzer.md          # Agent 1: Analyzes any career input
│   ├── learning_recommender.md       # Agent 2: Recommends resources with links
│   ├── schedule_analyzer.md          # Agent 3: Identifies available learning windows
│   └── plan_generator.md            # Agent 4: Creates schedule-aware development plan
├── src/
│   ├── llm_client.py                 # LLM backend wrapper
│   └── tools.py                      # Tools for agents to use
├── web/                              # Streamlit web UI
│   ├── app.py                        # Main web application
│   ├── database.py                   # SQLite database layer
│   └── email_utils.py               # Email delivery (SMTP)
├── sample_data/
│   ├── feedback_360.json             # Sample 360 feedback + resource catalog
│   ├── sample1.txt                   # Sample performance review text
│   ├── sample_schedule.json          # Sample schedule (JSON)
│   └── sample_schedule.txt           # Sample schedule (plain text)
├── main.py                           # CLI orchestrator
├── windsurf_workflow.py              # Manual Windsurf workflow
├── setup.py                          # Setup helper script
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment configuration template
├── README.md                         # This file
├── WINDSURF_GUIDE.md                 # Windsurf workflow guide
└── QUICKSTART.md                     # Quick start guide
```

## Quick Start - Four Ways to Run

### Option 1: Streamlit Web UI (RECOMMENDED)

The web UI provides user accounts, a guided input form, plan review with accept/reject, email delivery, and a progress dashboard.

```bash
pip install -r requirements.txt

# Configure your LLM backend (see .env.example)
cp .env.example .env
# Edit .env with your backend settings

# Launch the web app
streamlit run web/app.py
```

Open http://localhost:8501 in your browser. The app lets you:
- Register / sign in with email + password
- Upload career input (performance review, feedback docs) or type it directly
- Upload a schedule file or describe your availability
- **Choose a plan timeline** (30-365 days, defaults to 90 if not specified)
- Run the 4-agent pipeline with live progress
- Review the generated plan, then accept or reject
- Download the plan as Markdown or have it emailed to you
- Track weekly progress on an **interactive visual dashboard** with charts and phase tracking

---

### Option 2: CLI with Flexible Input

Run the 4-agent pipeline from the command line with any combination of inputs:

```bash
# Basic: just a feedback file
python main.py --feedback-file sample_data/sample1.txt

# Full: email + text + feedback file + schedule
python main.py \
  --email priya@company.com \
  --input-text "I want to grow into a Staff Engineer role" \
  --feedback-file sample_data/sample1.txt \
  --schedule-file sample_data/sample_schedule.txt

# With schedule as text
python main.py \
  --feedback-file sample_data/sample1.txt \
  --schedule-text "I have 30 min at lunch and 1 hour after 8pm on weekdays"
```

**CLI arguments:**

| Argument | Description |
|----------|-------------|
| `--email` | User's email address (included in analysis context) |
| `--input-text` | Career aspirations or feedback as inline text |
| `--feedback-file` | Path to a feedback/review file (TXT, PDF, DOCX) |
| `--schedule-file` | Path to a schedule file (TXT, JSON, ICS) |
| `--schedule-text` | Describe your availability as inline text |
| `--backend` | LLM backend: `ollama`, `anthropic`, or `openai` |
| `--model` | Specific model name (e.g. `gemma3:27b`, `claude-3-5-sonnet-20241022`) |
| `--output` | Output file path (default: `output_development_plan.md`) |

---

### Option 3: Use Windsurf Chat (No API Key)

```bash
pip install -r requirements.txt
python windsurf_workflow.py
```

This interactive script prepares prompts that you paste into Windsurf chat. See **[Windsurf Guide](WINDSURF_GUIDE.md)** for details.

---

### Option 4: Automated with Ollama (Free, Local)

```bash
# 1. Install Ollama from https://ollama.ai
ollama pull llama3.1

# 2. Start Ollama
ollama serve

# 3. Run
pip install -r requirements.txt
python main.py --backend ollama
```

## The 4-Agent Pipeline

```
┌─────────────────────────────────────────┐
│  1. Career Input Analyst                │
│  Reads: feedback_analyzer.md            │
│  Accepts: email, reviews, aspirations,  │
│    peer feedback, 360 JSON, free text   │
│  Tools: parse_feedback_data()           │
│  Output: Strengths, gaps, themes        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  2. Learning Recommender                │
│  Reads: learning_recommender.md         │
│  Does: Matches gaps to resources        │
│  Tools: match_learning_resources()      │
│  Output: Learning pathway with links    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  3. Schedule Analyzer                   │
│  Reads: schedule_analyzer.md            │
│  Accepts: calendar, JSON, text schedule │
│  Tools: parse_schedule_data()           │
│  Output: Available learning windows     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  4. Plan Generator                      │
│  Reads: plan_generator.md               │
│  Does: Creates schedule-aware plan      │
│  Uses: All 3 previous agent outputs     │
│  Output: N-day development plan         │
│    (user-chosen timeline, default 90d)  │
│    with durations on every activity     │
└─────────────────────────────────────────┘
```

### Agent.md Files

Each agent is defined by a Markdown file that contains:

- **Role**: What the agent is (e.g., "Career Input Analyst")
- **Expertise**: The agent's background and skills
- **Task**: What the agent needs to accomplish
- **Output Format**: Expected output structure
- **Tools**: Available tools the agent can use
- **Instructions**: Step-by-step guidance

The orchestrator reads these files and uses them as **system prompts** for the LLM.

### Tool Calling

Agents can call tools by including special syntax in their responses:

```
TOOL_CALL: parse_feedback_data(section="ratings")
TOOL_CALL: match_learning_resources(skills="communication, leadership")
TOOL_CALL: parse_schedule_data(filepath="sample_data/sample_schedule.json")
```

The orchestrator:
1. Detects tool calls in the agent's response
2. Executes the tool with the specified parameters
3. Passes the results back to the agent
4. Agent continues with the tool results as context

## Web UI Features

The Streamlit web app (`web/app.py`) provides:

| Feature | Description |
|---------|-------------|
| **User Accounts** | Register and sign in with email + password |
| **Career Input Form** | Upload files (PDF, DOCX, TXT) or type/paste text |
| **Schedule Input** | Upload calendar files or describe availability |
| **Custom Timeline** | Slider to set plan duration (30-365 days, default 90) |
| **Live Pipeline** | Watch all 4 agents run with status updates |
| **Plan Review** | See intermediate agent outputs + final plan |
| **Accept / Reject** | Accept the plan to activate it, or reject and start over |
| **Email Delivery** | Accepted plans are emailed (when SMTP is configured) |
| **Download** | Export plan as Markdown file |
| **Progress Dashboard** | Donut chart, weekly bar chart, phase tracker, days-remaining counter |
| **Weekly Tasks** | Per-week expandable sections with checkboxes and mini progress bars |
| **Plan History** | View all past plans with status badges and timeline info |

### Email Configuration (Optional)

Add these to your `.env` to enable email delivery of accepted plans:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_NAME=AI Career Coach
```

## Customization

### Modify Agent Behavior

Edit the `.md` files in the `agents/` directory to:

- Change the agent's role or expertise
- Add new instructions
- Modify output format
- Add constraints or requirements

**Example**: Make the feedback analyzer focus more on blind spots:

```markdown
# In agents/feedback_analyzer.md

## Your Task
...
5. **IMPORTANT**: Pay special attention to blind spots where self-perception 
   differs significantly from others' feedback. These are often the highest 
   leverage development areas.
```

### Add New Tools

Edit `src/tools.py`:

```python
def new_tool_function(param1: str, param2: int) -> str:
    """Your tool logic here."""
    return result

# Register the tool
AVAILABLE_TOOLS["new_tool_name"] = {
    "function": new_tool_function,
    "description": "What this tool does",
    "parameters": {
        "param1": {"type": "string", "description": "...", "required": True},
        "param2": {"type": "integer", "description": "...", "default": 0}
    }
}
```

Then update the relevant `agent.md` file to include the new tool.

### Change LLM Models

The system supports different models:

```bash
# Anthropic Claude
python main.py --backend anthropic --model claude-3-5-sonnet-20241022

# Ollama (local or remote)
python main.py --backend ollama --model llama3.1
python main.py --backend ollama --model gemma3:27b

# OpenAI
python main.py --backend openai --model gpt-4
```

### Use Different Feedback Data

Replace `sample_data/feedback_360.json` with your own data following the same structure:

```json
{
  "employee": { ... },
  "manager_review": { ... },
  "peer_reviews": [ ... ],
  "direct_report_reviews": [ ... ],
  "self_assessment": { ... },
  "learning_resources_catalog": [
    {
      "id": "LR001",
      "title": "Course Name",
      "type": "course",
      "provider": "Provider",
      "duration_hours": 8,
      "skills": ["skill1", "skill2"],
      "format": "online",
      "cost": "free",
      "url": "https://example.com/course"
    }
  ]
}
```

## Comparison with CrewAI Version

### Advantages of This Version

- **No framework dependency** - Pure Python, easy to understand and debug
- **Flexible LLM backends** - Works with Anthropic, Ollama, OpenAI, or add your own
- **Agent behaviors in Markdown** - Easy to read, edit, and version control
- **Flexible input** - Accepts email, text, files, 360 JSON, or any combination
- **Custom timeline** - Choose plan duration from 30 to 365 days (default 90)
- **Schedule-aware plans** - Fits learning into your actual available time
- **Course links** - Learning recommendations include direct URLs to resources
- **Web UI** - Full Streamlit app with accounts, progress tracking, and email
- **Visual dashboard** - Donut chart, weekly bar chart, phase tracker, days-remaining counter
- **Simple tool calling** - Straightforward regex-based tool detection
- **Transparent execution** - See exactly what's happening at each step

### When to Use CrewAI Instead

- You need advanced features like hierarchical agents or parallel execution
- You want pre-built integrations with many tools
- You prefer higher-level abstractions
- You're building a complex multi-agent system with many agents

## Expected Output

The system generates a comprehensive Markdown document with:

```markdown
# [N]-DAY CAREER DEVELOPMENT PLAN
# (duration chosen by user, default 90 days)

## EXECUTIVE SUMMARY
- Focus areas and expected outcomes

## DEVELOPMENT GOALS
- 3-4 SMART goals with metrics and timelines

## WEEK-BY-WEEK ROADMAP
- Phases scale proportionally to the chosen timeline
- Quick Wins phase in the early weeks
- Core skill building in the middle weeks
- Application & integration in the final weeks
- Each activity includes duration and format

## LEARNING RESOURCES SCHEDULE
- Specific resources with links mapped to weeks
- Fitted to your available time windows

## STRETCH ASSIGNMENTS
- On-the-job practice opportunities

## ACCOUNTABILITY FRAMEWORK
- Manager 1:1 topics
- Self-reflection prompts
- Peer feedback checkpoints

## SUCCESS METRICS
- Checkpoints proportional to plan duration
```

### Dashboard Visuals

When a plan is accepted, the web dashboard shows:

- **Metrics row** - Overall %, tasks completed, current week, tasks remaining, days left
- **Donut chart** - Visual completion percentage
- **Weekly bar chart** - Stacked bars showing done vs remaining tasks per week
- **Phase tracker** - Color-coded timeline phases (green = done, blue = active, gray = future)
- **Timeline progress bar** - Day X of N with percentage of elapsed time
- **Per-week mini progress bars** - Inside each expandable week section

## Troubleshooting

### "No API key found"

Make sure you've created a `.env` file (copy from `.env.example`) with the appropriate API key.

### "Error calling Ollama API"

Make sure Ollama is running: `ollama serve`

### "Tool not found"

Check that the tool name in the agent's `TOOL_CALL` matches exactly with the tool name in `src/tools.py`.

### "Max iterations reached"

The agent is stuck in a loop. This usually means:
- The agent.md instructions are unclear
- The tool outputs are not helpful
- The agent doesn't know when it's done

**Fix**: Edit the agent.md file to clarify when the task is complete.

### Web UI won't start

Make sure Streamlit is installed: `pip install streamlit` and run with `streamlit run web/app.py`.

### Email not sending

Check that `SMTP_USER` and `SMTP_PASSWORD` are set in your `.env` file. For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833).

## Future Enhancements

- [ ] Add more sophisticated tool calling (function calling API format)
- [ ] Support for parallel agent execution
- [x] ~~Web UI for easier interaction~~ (Done - Streamlit)
- [ ] Integration with real HR systems
- [x] ~~Progress tracking and check-ins~~ (Done - Dashboard)
- [x] ~~Visual progress dashboard~~ (Done - Donut chart, bar chart, phase tracker)
- [x] ~~Custom plan timeline~~ (Done - 30-365 day slider, default 90)
- [ ] Multi-employee batch processing
- [ ] Calendar API integration (Google Calendar, Outlook)
- [ ] PDF export of development plans

## License

This project is provided as-is for educational and development purposes.

## Credits

Based on the original CrewAI career_coach project, reimagined without frameworks for simplicity and flexibility.
