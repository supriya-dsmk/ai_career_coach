# Quick Start Guide

## Choose Your Method

### Method 1: Streamlit Web UI (RECOMMENDED)

The easiest way to use the system. Provides a full browser-based experience with user accounts, guided input, and a progress dashboard.

```bash
pip install -r requirements.txt

# Configure your LLM backend
cp .env.example .env
# Edit .env with your backend settings (Ollama, Anthropic, or OpenAI)

# Launch
streamlit run web/app.py
```

Open http://localhost:8501 in your browser. Then:

1. **Register** with an email and password
2. **Provide career input** - upload a performance review / feedback file, or type your aspirations directly
3. **Add your schedule** - upload a calendar or describe your weekly availability
4. **Generate** - the 4-agent pipeline runs with live status updates
5. **Review** - read the plan, expand intermediate agent outputs, then accept or reject
6. **Track progress** - use the dashboard to check off weekly tasks

---

### Method 2: CLI with Flexible Input

Run the pipeline from the command line with any combination of inputs:

```bash
pip install -r requirements.txt

# Basic: just a feedback file
python main.py --feedback-file sample_data/sample1.txt

# Full: email + text + feedback file + schedule
python main.py \
  --email priya@company.com \
  --input-text "I want to grow into a Staff Engineer role" \
  --feedback-file sample_data/sample1.txt \
  --schedule-file sample_data/sample_schedule.txt

# With inline schedule
python main.py \
  --feedback-file sample_data/sample1.txt \
  --schedule-text "I have 30 min at lunch and 1 hour after 8pm on weekdays"
```

Output is saved to `output_development_plan.md` (or use `--output` to change the path).

**All CLI arguments:**

| Argument | Description |
|----------|-------------|
| `--email` | User's email address |
| `--input-text` | Career aspirations or feedback as inline text |
| `--feedback-file` | Path to a feedback/review file (TXT, PDF, DOCX) |
| `--schedule-file` | Path to a schedule file (TXT, JSON, ICS) |
| `--schedule-text` | Describe your availability as inline text |
| `--backend` | LLM backend: `ollama`, `anthropic`, or `openai` |
| `--model` | Model name (e.g. `gemma3:27b`, `claude-3-5-sonnet-20241022`) |
| `--output` | Output file path (default: `output_development_plan.md`) |

---

### Method 3: Windsurf Chat (No API Key Needed)

```bash
pip install -r requirements.txt
python windsurf_workflow.py
```

Follow the interactive prompts. Takes 15-20 minutes.

See **[Windsurf Guide](WINDSURF_GUIDE.md)** for details.

---

### Method 4: Automated with Ollama (Free, Local)

```bash
# Install Ollama from https://ollama.ai
ollama pull llama3.1
ollama serve

# In another terminal
pip install -r requirements.txt
python main.py --backend ollama
```

## LLM Backend Configuration

**Option A: Ollama (Free, Local or Remote)**

```bash
# Local
ollama pull llama3.1
ollama serve
# No .env needed for local!

# Remote Ollama
# In .env:
OLLAMA_HOST=http://your-server:11434
OLLAMA_MODEL=gemma3:27b
```

**Option B: Anthropic Claude**

```bash
cp .env.example .env
# In .env:
ANTHROPIC_API_KEY=your-key-here
```

Get your key: https://console.anthropic.com/

**Option C: OpenAI**

```bash
cp .env.example .env
# In .env:
OPENAI_API_KEY=your-key-here
```

## What You'll Get

A comprehensive career development plan with:

- **Career Input Analysis**: Strengths, gaps, blind spots, and themes from any input source
- **Learning Pathway**: Curated resources with direct course links mapped to skill gaps
- **Schedule Analysis**: Your available learning windows identified from calendar data
- **90-Day Plan**: Week-by-week roadmap with durations on every activity, fitted to your schedule
- **Accountability**: Check-ins, metrics, and success criteria

## Web UI Features

| Feature | Description |
|---------|-------------|
| **User Accounts** | Register and sign in with email + password |
| **File Upload** | Accept PDF, DOCX, TXT performance reviews |
| **Schedule Input** | Calendar files (JSON, ICS, TXT) or free-text description |
| **Live Pipeline** | Watch 4 agents run with real-time status |
| **Plan Review** | Expand intermediate outputs, accept or reject the plan |
| **Email Delivery** | Accepted plans emailed when SMTP is configured |
| **Download** | Export plan as Markdown |
| **Progress Dashboard** | Weekly task checkboxes, completion %, progress bar |
| **Plan History** | All past plans with status badges |

### Optional: Email Configuration

Add these to your `.env` to enable email delivery:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_NAME=AI Career Coach
```

## Advanced Usage

```bash
# Use specific backend and model
python main.py --backend anthropic --model claude-3-5-sonnet-20241022
python main.py --backend ollama --model gemma3:27b

# Custom output
python main.py --output my_custom_plan.md

# Streamlit on a different port
streamlit run web/app.py --server.port 8502
```

## Architecture Overview

```
User Input (any combination of email, text, files, schedule)
         |
         v
+-------------------------+
| Agent 1: Career Input   | <-- agents/feedback_analyzer.md
| Analyst                 | <-- tools: parse_feedback_data()
+------------+------------+
             | (context)
             v
+-------------------------+
| Agent 2: Learning       | <-- agents/learning_recommender.md
| Recommender             | <-- tools: match_learning_resources()
+------------+------------+    (returns resources with course URLs)
             | (context)
             v
+-------------------------+
| Agent 3: Schedule       | <-- agents/schedule_analyzer.md
| Analyzer                | <-- tools: parse_schedule_data()
+------------+------------+
             | (context)
             v
+-------------------------+
| Agent 4: Plan Generator | <-- agents/plan_generator.md
| (schedule-aware)        | <-- synthesizes all 3 previous outputs
+------------+------------+
             |
             v
   90-Day Development Plan
   (with durations + links)
```

## Customization

### Modify Agent Behavior

Edit the Markdown files in `agents/`:
- `feedback_analyzer.md` - Change how career input is analyzed
- `learning_recommender.md` - Adjust resource recommendations and link output
- `schedule_analyzer.md` - Customize schedule parsing
- `plan_generator.md` - Customize the development plan format

### Add Your Own Data

Replace `sample_data/feedback_360.json` with your own 360 feedback data. The learning resource catalog in that file supports a `url` field for course links.

### Add New Tools

Edit `src/tools.py` to add custom tools that agents can use.

## Key Differences from CrewAI Version

| Feature | CrewAI Version | This Version |
|---------|---------------|--------------|
| Framework | CrewAI required | Pure Python |
| Agents | 3 Python classes | 4 Markdown files |
| LLM | OpenAI only | Anthropic / Ollama / OpenAI |
| Input | 360 JSON only | Email, text, files, schedule |
| Interface | CLI only | CLI + Streamlit web UI |
| Course links | No | Yes |
| Schedule-aware | No | Yes |
| Progress tracking | No | Yes (web dashboard) |

## Troubleshooting

**"No API key found"**
- Create `.env` file from `.env.example` and add your key

**"Error calling Ollama"**
- Run `ollama serve` in another terminal

**"Tool not found"**
- Check tool name matches exactly in agent.md and tools.py

**"Max iterations reached"**
- Agent stuck in loop - clarify instructions in agent.md file

**Web UI won't start**
- Make sure Streamlit is installed: `pip install streamlit`
- Try a different port: `streamlit run web/app.py --server.port 8502`

**Email not sending**
- Check `SMTP_USER` and `SMTP_PASSWORD` in `.env`
- For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833)

---

See `README.md` for the full architecture explanation, tool creation guide, and more.
