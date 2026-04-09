"""
AI Career Coach - Streamlit Web UI
====================================
A simple web interface for the career coaching pipeline.

Run with:  streamlit run web/app.py
"""

import sys
import os
import re
import time
import tempfile
from pathlib import Path

# Project root setup
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True, dotenv_path=PROJECT_ROOT / ".env")

from web.database import (
    create_user, authenticate_user, get_user_by_id,
    save_plan, accept_plan, reject_plan,
    get_user_plans, get_plan, get_active_plan,
    init_progress_from_plan, get_progress, update_task_completion,
    get_progress_summary,
)
from web.email_utils import send_plan_email_safe, is_email_configured
from llm_client import create_llm_client, get_backend_from_env
from tools import execute_tool, AVAILABLE_TOOLS

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Career Coach",
    page_icon=":briefcase:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main-header {font-size: 2rem; font-weight: 700; margin-bottom: 0.2rem;}
    .sub-header  {font-size: 1rem; color: #888; margin-bottom: 1.5rem;}
    .metric-card {
        background: #f8f9fa; border-radius: 10px; padding: 1.2rem;
        text-align: center; border: 1px solid #e9ecef;
    }
    .metric-value {font-size: 2rem; font-weight: 700; color: #1f77b4;}
    .metric-label {font-size: 0.85rem; color: #666;}
    .week-header  {
        background: #f0f2f6; padding: 0.5rem 1rem; border-radius: 6px;
        font-weight: 600; margin: 1rem 0 0.5rem 0;
    }
    .status-badge {
        display: inline-block; padding: 0.2rem 0.7rem; border-radius: 12px;
        font-size: 0.8rem; font-weight: 600;
    }
    .badge-accepted  {background: #d4edda; color: #155724;}
    .badge-draft     {background: #fff3cd; color: #856404;}
    .badge-rejected  {background: #f8d7da; color: #721c24;}
</style>
""", unsafe_allow_html=True)


# ===========================================================================
# SESSION STATE HELPERS
# ===========================================================================
def init_session():
    """Initialise session state keys."""
    defaults = {
        "user": None,           # dict {id, email, name}
        "page": "login",        # login | register | input | running | review | dashboard | history
        "draft_plan": None,     # dict with plan data while reviewing
        "run_error": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def go(page: str):
    st.session_state.page = page


def logged_in() -> bool:
    return st.session_state.user is not None


# ===========================================================================
# AGENT PIPELINE (reused from main.py logic)
# ===========================================================================
class _Agent:
    """Lightweight copy of the Agent class from main.py for the web UI."""

    def __init__(self, name: str, agent_file: Path, llm_client):
        self.name = name
        self.llm_client = llm_client
        with open(agent_file, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    def execute(self, task: str, context: list | None = None, max_iter: int = 10) -> str:
        user_msg = task
        if context:
            user_msg = "# Context from Previous Agents\n\n"
            for i, ctx in enumerate(context, 1):
                user_msg += f"## Output from Agent {i}\n\n{ctx}\n\n"
            user_msg += f"\n# Your Task\n\n{task}"

        history: list[dict] = []
        for iteration in range(max_iter):
            response = self.llm_client.generate(
                system_prompt=self.system_prompt,
                user_message=user_msg if iteration == 0 else self._cont(history),
                temperature=0.7,
            )
            history.append({"role": "assistant", "content": response})

            tool_calls = self._tools(response)
            if not tool_calls:
                return response

            results_text = "# Tool Execution Results\n\n"
            for tc in tool_calls:
                result = execute_tool(tc["name"], **tc["args"])
                results_text += f"## Tool: {tc['name']}\nArgs: {tc['args']}\nResult:\n```\n{result}\n```\n\n"
            results_text += "Please continue with your analysis based on these results.\n"
            history.append({"role": "user", "content": results_text})

        return history[-1]["content"] if history else "No output generated"

    def _tools(self, resp: str) -> list:
        out = []
        for name, args_str in re.findall(r'TOOL_CALL:\s*(\w+)\((.*?)\)', resp, re.DOTALL):
            if name not in AVAILABLE_TOOLS:
                continue
            args = dict(re.findall(r'(\w+)=["\']([^"\']*)["\']', args_str))
            out.append({"name": name, "args": args})
        return out

    def _cont(self, history):
        parts = []
        for m in history:
            if m["role"] == "assistant":
                parts.append(f"Your previous response:\n{m['content']}\n")
            else:
                parts.append(f"{m['content']}\n")
        return "\n".join(parts)


def _read_uploaded(uploaded) -> str | None:
    """Read an uploaded file to text."""
    if uploaded is None:
        return None
    suffix = Path(uploaded.name).suffix.lower()
    if suffix == ".pdf":
        try:
            import PyPDF2, io
            reader = PyPDF2.PdfReader(io.BytesIO(uploaded.read()))
            return "\n".join(p.extract_text() or "" for p in reader.pages).strip()
        except Exception:
            return uploaded.read().decode("utf-8", errors="replace")
    elif suffix == ".docx":
        try:
            import docx, io
            doc = docx.Document(io.BytesIO(uploaded.read()))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return uploaded.read().decode("utf-8", errors="replace")
    else:
        return uploaded.read().decode("utf-8", errors="replace")


def run_pipeline(career_text: str, schedule_text: str, status_area) -> dict:
    """Run the 4-agent pipeline and return outputs dict."""
    backend = get_backend_from_env()
    model = os.getenv("OLLAMA_MODEL", None)
    llm = create_llm_client(backend=backend, model=model)
    agents_dir = PROJECT_ROOT / "agents"

    agents = [
        ("Career Input Analyst",  "feedback_analyzer.md"),
        ("Learning Recommender",  "learning_recommender.md"),
        ("Schedule Analyzer",     "schedule_analyzer.md"),
        ("Plan Generator",        "plan_generator.md"),
    ]

    context: list[str] = []
    outputs = {}

    for idx, (name, md) in enumerate(agents):
        status_area.info(f"Running Agent {idx+1}/4: **{name}** ...")
        agent = _Agent(name, agents_dir / md, llm)

        if idx == 0:
            task = (
                "Below is the career-related input to analyze. This may include "
                "performance reviews, aspirations, peer feedback, self-reflections, "
                "or any combination thereof. Analyze it thoroughly.\n\n"
                "You do NOT need to call the parse_feedback_data tool -- the full "
                "input is provided here.\n\n"
                f"{career_text}\n\n"
                "Complete your assigned task as described in your role."
            )
        elif idx == 2:
            task = (
                "Below is the user's schedule/availability information. "
                "Analyze it and identify all available learning windows.\n\n"
                f"{schedule_text}\n\n"
                "Complete your assigned task as described in your role."
            )
        else:
            task = "Complete your assigned task as described in your role."

        output = agent.execute(task, context if context else None)
        context.append(output)
        key = ["agent1", "agent2", "agent3", "plan"][idx]
        outputs[key] = output

    status_area.success("All 4 agents completed!")
    return outputs


def extract_tasks_from_plan(plan_md: str) -> list[dict]:
    """Extract checkbox tasks from the plan markdown for progress tracking."""
    tasks: list[dict] = []
    current_week = 0
    week_pattern = re.compile(r'\*\*Week\s+(\d+)\*\*', re.IGNORECASE)
    weeks_header = re.compile(r'###\s+WEEKS?\s+(\d+)', re.IGNORECASE)
    task_pattern = re.compile(r'- \[ \]\s+(.+)')

    for line in plan_md.split("\n"):
        wm = weeks_header.search(line)
        if wm:
            current_week = int(wm.group(1))
        wm2 = week_pattern.search(line)
        if wm2:
            current_week = int(wm2.group(1))
        tm = task_pattern.search(line)
        if tm:
            text = tm.group(1).strip()
            # Strip markdown bold/formatting for clean display
            text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
            tasks.append({"week": max(current_week, 1), "task": text})

    return tasks


# ===========================================================================
# PAGES
# ===========================================================================

def page_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<p class="main-header">AI Career Coach</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Sign in to your account</p>', unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please fill in both fields.")
            else:
                user = authenticate_user(email, password)
                if user:
                    st.session_state.user = dict(user)
                    active = get_active_plan(user["id"])
                    go("dashboard" if active else "input")
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

        st.markdown("---")
        if st.button("Create an account", use_container_width=True):
            go("register")
            st.rerun()


def page_register():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<p class="main-header">Create Account</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Get started with your career development</p>', unsafe_allow_html=True)

        with st.form("register_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            pw1 = st.text_input("Password", type="password")
            pw2 = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Create Account", use_container_width=True)

        if submitted:
            if not email or not pw1:
                st.error("Email and password are required.")
            elif pw1 != pw2:
                st.error("Passwords do not match.")
            elif len(pw1) < 4:
                st.error("Password must be at least 4 characters.")
            else:
                try:
                    uid = create_user(email, pw1, name)
                    st.session_state.user = {"id": uid, "email": email, "name": name}
                    go("input")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

        st.markdown("---")
        if st.button("Back to Sign In", use_container_width=True):
            go("login")
            st.rerun()


def page_input():
    st.markdown('<p class="main-header">Career Input</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Provide your career information and schedule</p>', unsafe_allow_html=True)

    user = st.session_state.user

    st.markdown("#### About You")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Email", value=user["email"], disabled=True)
    with col2:
        display_name = st.text_input("Display Name", value=user.get("name", ""))

    st.markdown("---")

    st.markdown("#### Career Input")
    st.caption("Provide a performance review, aspirations, peer feedback, or any career-related input. You can upload a file, type text, or both.")

    career_file = st.file_uploader(
        "Upload a file (performance review, feedback doc, etc.)",
        type=["txt", "pdf", "docx", "md"],
        key="career_file",
    )
    career_text = st.text_area(
        "Or type / paste your career input here",
        height=180,
        placeholder="Example: I want to become a Staff Engineer. My manager says I need to improve stakeholder communication and delegation...",
        key="career_text_input",
    )

    st.markdown("---")

    st.markdown("#### Your Schedule / Availability")
    st.caption("Help us build a plan that fits YOUR time. Upload a calendar or describe your weekly availability.")

    schedule_file = st.file_uploader(
        "Upload a schedule file (calendar export, JSON, text)",
        type=["txt", "json", "ics", "csv"],
        key="schedule_file",
    )
    schedule_text = st.text_area(
        "Or describe your availability",
        height=120,
        placeholder="Example: I can only spare 10 minutes during lunch and 30 minutes before calling it a day. Saturday mornings I have about an hour free.",
        key="schedule_text_input",
    )

    st.markdown("---")

    if st.button("Generate My Development Plan", type="primary", use_container_width=True):
        # Assemble career input
        parts = [f"**User Email**: {user['email']}"]
        if display_name:
            parts.append(f"**Name**: {display_name}")

        file_content = _read_uploaded(career_file)
        if file_content:
            parts.append(f"**Input from file**:\n--- START ---\n{file_content}\n--- END ---")
        if career_text.strip():
            parts.append(f"**Direct input**:\n--- START ---\n{career_text.strip()}\n--- END ---")

        if not file_content and not career_text.strip():
            st.error("Please provide some career input (upload a file or type text).")
            return

        sched_parts = []
        sched_content = _read_uploaded(schedule_file)
        if sched_content:
            sched_parts.append(f"**Schedule from file**:\n--- START ---\n{sched_content}\n--- END ---")
        if schedule_text.strip():
            sched_parts.append(f"**Schedule description**:\n--- START ---\n{schedule_text.strip()}\n--- END ---")
        if not sched_parts:
            sched_parts.append(
                "No specific schedule was provided. Assume the user has a standard "
                "work schedule (9 AM - 5 PM, Monday-Friday) and can dedicate "
                "approximately 4-5 hours per week for development activities."
            )

        combined_career = "\n\n".join(parts)
        combined_schedule = "\n\n".join(sched_parts)

        # Store in session and move to running page
        st.session_state["_career_input"] = combined_career
        st.session_state["_schedule_input"] = combined_schedule
        st.session_state["_input_summary"] = (career_text.strip() or (file_content or "")[:200])[:300]
        st.session_state["_display_name"] = display_name
        go("running")
        st.rerun()


def page_running():
    st.markdown('<p class="main-header">Generating Your Plan</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Running the 4-agent pipeline...</p>', unsafe_allow_html=True)

    career_input = st.session_state.get("_career_input", "")
    schedule_input = st.session_state.get("_schedule_input", "")

    if not career_input:
        st.warning("No input found. Please go back and provide career input.")
        if st.button("Back to Input"):
            go("input")
            st.rerun()
        return

    status = st.empty()
    try:
        outputs = run_pipeline(career_input, schedule_input, status)
    except Exception as e:
        st.error(f"Pipeline error: {e}")
        if st.button("Back to Input"):
            go("input")
            st.rerun()
        return

    # Save as draft
    user = st.session_state.user
    plan_id = save_plan(
        user_id=user["id"],
        plan_markdown=outputs["plan"],
        agent1_output=outputs.get("agent1", ""),
        agent2_output=outputs.get("agent2", ""),
        agent3_output=outputs.get("agent3", ""),
        input_summary=st.session_state.get("_input_summary", ""),
    )

    st.session_state.draft_plan = {"plan_id": plan_id, **outputs}
    go("review")
    st.rerun()


def page_review():
    st.markdown('<p class="main-header">Review Your Plan</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Read through the plan below. Accept it to save and get it emailed to you, or reject to start over.</p>', unsafe_allow_html=True)

    draft = st.session_state.draft_plan
    if not draft:
        st.warning("No plan to review.")
        if st.button("Back"):
            go("input")
            st.rerun()
        return

    plan_md = draft["plan"]

    # Expandable sections for intermediate agent outputs
    with st.expander("Agent 1: Career Input Analysis", expanded=False):
        st.markdown(draft.get("agent1", ""))
    with st.expander("Agent 2: Learning Recommendations", expanded=False):
        st.markdown(draft.get("agent2", ""))
    with st.expander("Agent 3: Schedule Analysis", expanded=False):
        st.markdown(draft.get("agent3", ""))

    st.markdown("---")
    st.markdown("### Your 90-Day Development Plan")
    st.markdown(plan_md)
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("Accept Plan", type="primary", use_container_width=True):
            plan_id = draft["plan_id"]
            accept_plan(plan_id)

            # Initialize progress tasks
            tasks = extract_tasks_from_plan(plan_md)
            if tasks:
                init_progress_from_plan(plan_id, tasks)

            # Send email
            user = st.session_state.user
            ok, msg = send_plan_email_safe(
                user["email"],
                user.get("name", user["email"]),
                plan_md,
            )
            if ok:
                st.toast("Plan emailed to you!")
            else:
                st.toast(f"Email: {msg}", icon=":material/info:")

            st.session_state.draft_plan = None
            go("dashboard")
            st.rerun()

    with col2:
        if st.button("Reject & Start Over", use_container_width=True):
            reject_plan(draft["plan_id"])
            st.session_state.draft_plan = None
            go("input")
            st.rerun()

    with col3:
        st.download_button(
            "Download as Markdown",
            data=plan_md,
            file_name="career_development_plan.md",
            mime="text/markdown",
            use_container_width=True,
        )


def page_dashboard():
    user = st.session_state.user
    plan_row = get_active_plan(user["id"])

    if not plan_row:
        st.markdown('<p class="main-header">Dashboard</p>', unsafe_allow_html=True)
        st.info("You don't have an active plan yet. Generate one to get started!")
        if st.button("Create New Plan", type="primary"):
            go("input")
            st.rerun()
        return

    plan_id = plan_row["id"]
    summary = get_progress_summary(plan_id)
    total = summary["total"]
    completed = summary["completed"]
    pct = int((completed / total * 100) if total else 0)

    # Header
    st.markdown('<p class="main-header">Your Dashboard</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-header">Accepted on {plan_row["accepted_at"] or "N/A"}</p>', unsafe_allow_html=True)

    # Metrics row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{pct}%</div>
            <div class="metric-label">Overall Progress</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{completed}/{total}</div>
            <div class="metric-label">Tasks Completed</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        current_week = 0
        for w, data in summary.get("by_week", {}).items():
            if data["completed"] < data["total"]:
                current_week = w
                break
        if current_week == 0 and total > 0:
            current_week = max(summary.get("by_week", {}).keys(), default=1)
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">Week {current_week}</div>
            <div class="metric-label">Current Focus</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        remaining = total - completed
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{remaining}</div>
            <div class="metric-label">Tasks Remaining</div>
        </div>""", unsafe_allow_html=True)

    st.progress(pct / 100)

    # Weekly progress
    st.markdown("---")
    st.markdown("### Weekly Progress")

    progress_items = get_progress(plan_id)
    weeks: dict[int, list] = {}
    for item in progress_items:
        w = item["week_number"]
        weeks.setdefault(w, []).append(item)

    for week_num in sorted(weeks.keys()):
        items = weeks[week_num]
        week_done = sum(1 for i in items if i["completed"])
        week_total = len(items)
        week_pct = int(week_done / week_total * 100) if week_total else 0

        with st.expander(f"Week {week_num}  ({week_done}/{week_total} done - {week_pct}%)", expanded=(week_num == current_week)):
            for item in items:
                col_a, col_b = st.columns([0.05, 0.95])
                with col_a:
                    new_val = st.checkbox(
                        "done",
                        value=bool(item["completed"]),
                        key=f"task_{item['id']}",
                        label_visibility="collapsed",
                    )
                with col_b:
                    if bool(item["completed"]) != new_val:
                        update_task_completion(item["id"], new_val)
                        st.rerun()
                    text = item["task_text"]
                    if item["completed"]:
                        st.markdown(f"~~{text}~~")
                    else:
                        st.markdown(text)

    # Plan view
    st.markdown("---")
    with st.expander("View Full Plan", expanded=False):
        st.markdown(plan_row["plan_markdown"])

    st.download_button(
        "Download Plan as Markdown",
        data=plan_row["plan_markdown"],
        file_name="career_development_plan.md",
        mime="text/markdown",
    )


def page_history():
    user = st.session_state.user
    plans = get_user_plans(user["id"])

    st.markdown('<p class="main-header">Plan History</p>', unsafe_allow_html=True)

    if not plans:
        st.info("No plans generated yet.")
        return

    for p in plans:
        status = p["status"]
        badge_class = {"accepted": "badge-accepted", "draft": "badge-draft", "rejected": "badge-rejected"}.get(status, "badge-draft")
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            summary_text = (p["input_summary"] or "No summary")[:120]
            st.markdown(f"**Plan #{p['id']}** - {summary_text}...")
        with col2:
            st.markdown(f'<span class="status-badge {badge_class}">{status.upper()}</span>', unsafe_allow_html=True)
        with col3:
            st.caption(str(p["created_at"])[:16])

        if status == "accepted":
            with st.expander("View Plan"):
                st.markdown(p["plan_markdown"])
        st.markdown("---")


# ===========================================================================
# SIDEBAR
# ===========================================================================

def sidebar():
    with st.sidebar:
        if logged_in():
            user = st.session_state.user
            st.markdown(f"**{user.get('name') or user['email']}**")
            st.caption(user["email"])
            st.markdown("---")

            if st.button("Dashboard", use_container_width=True):
                go("dashboard")
                st.rerun()
            if st.button("New Plan", use_container_width=True):
                go("input")
                st.rerun()
            if st.button("Plan History", use_container_width=True):
                go("history")
                st.rerun()

            st.markdown("---")
            if st.button("Sign Out", use_container_width=True):
                st.session_state.user = None
                st.session_state.draft_plan = None
                go("login")
                st.rerun()

            st.markdown("---")
            st.caption("AI Career Coach v2.0")
            if is_email_configured():
                st.caption("Email: configured")
            else:
                st.caption("Email: not configured")
        else:
            st.markdown("### AI Career Coach")
            st.caption("Sign in to get started")


# ===========================================================================
# MAIN ROUTER
# ===========================================================================

def main():
    init_session()
    sidebar()

    page = st.session_state.page

    if not logged_in() and page not in ("login", "register"):
        go("login")
        page = "login"

    {
        "login":     page_login,
        "register":  page_register,
        "input":     page_input,
        "running":   page_running,
        "review":    page_review,
        "dashboard": page_dashboard,
        "history":   page_history,
    }.get(page, page_login)()


if __name__ == "__main__":
    main()
