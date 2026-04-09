"""
AI Career Development & Performance Coach - Orchestrator
=========================================================
A multi-agent system that transforms career-related input into
actionable, schedule-aware career development plans.

This version uses agent.md files instead of CrewAI framework,
with direct LLM API calls (Anthropic Claude, Ollama, or OpenAI).

Agents:
  1. Career Input Analyst   - Parses any kind of career input (reviews, aspirations, feedback)
  2. Learning Recommender   - Maps skill gaps to curated learning resources
  3. Schedule Analyzer      - Analyzes the user's calendar/availability for realistic planning
  4. Plan Generator         - Builds a measurable, schedule-aware 90-day development plan
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, Optional, List
from dotenv import load_dotenv

# Fix Windows console encoding for Unicode characters from LLM output
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from llm_client import create_llm_client, get_backend_from_env
from tools import execute_tool, AVAILABLE_TOOLS

load_dotenv(override=True)


class Agent:
    """Represents an agent with its behavior defined in an agent.md file."""
    
    def __init__(self, name: str, agent_file: Path, llm_client):
        self.name = name
        self.agent_file = agent_file
        self.llm_client = llm_client
        self.system_prompt = self._load_agent_prompt()
    
    def _load_agent_prompt(self) -> str:
        """Load the agent's system prompt from the .md file."""
        if not self.agent_file.exists():
            raise FileNotFoundError(f"Agent file not found: {self.agent_file}")
        
        with open(self.agent_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def execute(
        self,
        task_description: str,
        context: Optional[List[str]] = None,
        max_iterations: int = 10
    ) -> str:
        """
        Execute the agent's task.
        
        Args:
            task_description: The task to complete
            context: Previous agent outputs to use as context
            max_iterations: Max number of tool-calling iterations
        
        Returns:
            The agent's final output
        """
        print(f"\n{'='*70}")
        print(f"  Executing Agent: {self.name}")
        print(f"{'='*70}\n")
        
        # Build the user message with context
        user_message = task_description
        if context:
            user_message = "# Context from Previous Agents\n\n"
            for i, ctx in enumerate(context, 1):
                user_message += f"## Output from Agent {i}\n\n{ctx}\n\n"
            user_message += f"\n# Your Task\n\n{task_description}"
        
        # Iterative execution with tool calling
        conversation_history = []
        for iteration in range(max_iterations):
            print(f"[Iteration {iteration + 1}] Calling LLM...")
            
            response = self.llm_client.generate(
                system_prompt=self.system_prompt,
                user_message=user_message if iteration == 0 else self._build_continuation_message(conversation_history),
                temperature=0.7
            )
            
            conversation_history.append({"role": "assistant", "content": response})
            
            # Check if the response contains tool calls
            tool_calls = self._extract_tool_calls(response)
            
            if not tool_calls:
                # No more tool calls, agent is done
                print(f"[Iteration {iteration + 1}] Agent completed (no tool calls)\n")
                return response
            
            # Execute tool calls
            print(f"[Iteration {iteration + 1}] Executing {len(tool_calls)} tool call(s)...")
            tool_results = []
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                print(f"  - {tool_name}({tool_args})")
                
                result = execute_tool(tool_name, **tool_args)
                tool_results.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result
                })
            
            # Add tool results to conversation
            tool_results_text = self._format_tool_results(tool_results)
            conversation_history.append({"role": "user", "content": tool_results_text})
            
            print(f"[Iteration {iteration + 1}] Tool results added to context\n")
        
        # Max iterations reached
        print(f"[Warning] Max iterations ({max_iterations}) reached\n")
        return conversation_history[-1]["content"] if conversation_history else "No output generated"
    
    def _extract_tool_calls(self, response: str) -> List[Dict]:
        """
        Extract tool calls from the agent's response.
        
        Expected format:
        TOOL_CALL: tool_name(param1="value1", param2="value2")
        or
        TOOL_CALL: tool_name(param="value")
        """
        tool_calls = []
        
        # Pattern: TOOL_CALL: tool_name(args)
        pattern = r'TOOL_CALL:\s*(\w+)\((.*?)\)'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for tool_name, args_str in matches:
            if tool_name not in AVAILABLE_TOOLS:
                print(f"  [Warning] Unknown tool: {tool_name}")
                continue
            
            # Parse arguments
            args = {}
            if args_str.strip():
                # Simple parsing for key="value" pairs
                arg_pattern = r'(\w+)=["\']([^"\']*)["\']'
                arg_matches = re.findall(arg_pattern, args_str)
                args = dict(arg_matches)
            
            tool_calls.append({
                "name": tool_name,
                "args": args
            })
        
        return tool_calls
    
    def _format_tool_results(self, tool_results: List[Dict]) -> str:
        """Format tool results for the next LLM call."""
        formatted = "# Tool Execution Results\n\n"
        for result in tool_results:
            formatted += f"## Tool: {result['tool']}\n"
            formatted += f"Arguments: {result['args']}\n"
            formatted += f"Result:\n```\n{result['result']}\n```\n\n"
        formatted += "Please continue with your analysis based on these results.\n"
        return formatted
    
    def _build_continuation_message(self, history: List[Dict]) -> str:
        """Build a continuation message from conversation history."""
        messages = []
        for msg in history:
            role = msg["role"]
            content = msg["content"]
            if role == "assistant":
                messages.append(f"Your previous response:\n{content}\n")
            else:
                messages.append(f"{content}\n")
        return "\n".join(messages)


def _read_input_file(filepath: str) -> Optional[str]:
    """Read content from a file, supporting text, PDF, and DOCX formats."""
    path = Path(filepath)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    
    if not path.exists():
        print(f"Warning: File not found: {path}")
        return None
    
    suffix = path.suffix.lower()
    
    if suffix == ".pdf":
        try:
            import PyPDF2
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except ImportError:
            print("Warning: PyPDF2 not installed. Install with: pip install PyPDF2")
            return None
    elif suffix == ".docx":
        try:
            import docx
            doc = docx.Document(str(path))
            return "\n".join([p.text for p in doc.paragraphs])
        except ImportError:
            print("Warning: python-docx not installed. Install with: pip install python-docx")
            return None
    else:
        # Default: read as text
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


class CareerCoachOrchestrator:
    """Orchestrates the multi-agent career coaching pipeline."""
    
    def __init__(self, backend: str = "auto", model: Optional[str] = None):
        """
        Initialize the orchestrator.
        
        Args:
            backend: LLM backend ('anthropic', 'ollama', 'openai', or 'auto')
            model: Specific model to use (optional)
        """
        if backend == "auto":
            backend = get_backend_from_env()
        
        print(f"Initializing LLM client: {backend}")
        self.llm_client = create_llm_client(backend=backend, model=model)
        self.backend = backend
        
        # Define agents (now 4 agents)
        agents_dir = Path(__file__).parent / "agents"
        self.agents = [
            Agent("Career Input Analyst", agents_dir / "feedback_analyzer.md", self.llm_client),
            Agent("Learning Recommender", agents_dir / "learning_recommender.md", self.llm_client),
            Agent("Schedule Analyzer", agents_dir / "schedule_analyzer.md", self.llm_client),
            Agent("Plan Generator", agents_dir / "plan_generator.md", self.llm_client),
        ]
    
    def run(
        self,
        email: Optional[str] = None,
        feedback_file: Optional[str] = None,
        input_text: Optional[str] = None,
        schedule_file: Optional[str] = None,
        schedule_text: Optional[str] = None,
    ) -> str:
        """Run the complete coaching pipeline.
        
        Args:
            email: User's email address for identification.
            feedback_file: Path to a file containing performance feedback, review,
                           aspirations, or any career-related input. Supports
                           .txt, .pdf, .docx formats.
            input_text: Direct text input — could be aspirations, feedback,
                        self-reflection, or anything career-related.
            schedule_file: Path to a file containing the user's calendar or
                           weekly schedule (.json, .ics, .txt).
            schedule_text: Direct text description of the user's weekly
                           schedule/availability (e.g., "I can spare 10 minutes
                           in the afternoon and 30 minutes before bed").
        """
        print("=" * 70)
        print("  AI Career Development & Performance Coach")
        print("  Agent-based System (No CrewAI)")
        print(f"  LLM Backend: {self.backend}")
        print("=" * 70)
        print()
        
        if email:
            print(f"  User Email: {email}")
        
        print("\nStarting analysis pipeline...")
        print("-" * 70)
        
        # ------------------------------------------------------------------
        # 1. Build the career input for Agent 1 (Career Input Analyst)
        # ------------------------------------------------------------------
        input_parts = []
        
        if email:
            input_parts.append(f"**User Email**: {email}")
        
        # Read file-based input (performance review, feedback doc, etc.)
        if feedback_file:
            file_content = _read_input_file(feedback_file)
            if file_content:
                input_parts.append(
                    f"**Input from file** ({feedback_file}):\n"
                    f"--- START OF FILE CONTENT ---\n"
                    f"{file_content}\n"
                    f"--- END OF FILE CONTENT ---"
                )
                print(f"Loaded career input from file: {feedback_file}")
        
        # Direct text input (aspirations, feedback, self-reflection, etc.)
        if input_text:
            input_parts.append(
                f"**Direct input from user**:\n"
                f"--- START OF USER INPUT ---\n"
                f"{input_text}\n"
                f"--- END OF USER INPUT ---"
            )
            print("Loaded direct text input from user")
        
        # If no input at all, fall back to structured JSON data
        use_structured_data = not input_parts or (not feedback_file and not input_text)
        if use_structured_data and not input_parts:
            input_parts.append(
                "Structured 360-degree feedback data is available. "
                "Use the parse_feedback_data tool to retrieve it."
            )
            print("Using structured 360-degree feedback data (JSON)")
        
        # ------------------------------------------------------------------
        # 2. Build the schedule input for Agent 3 (Schedule Analyzer)
        # ------------------------------------------------------------------
        schedule_parts = []
        
        if schedule_file:
            sched_content = _read_input_file(schedule_file)
            if sched_content:
                schedule_parts.append(
                    f"**Schedule from file** ({schedule_file}):\n"
                    f"--- START OF SCHEDULE ---\n"
                    f"{sched_content}\n"
                    f"--- END OF SCHEDULE ---"
                )
                print(f"Loaded schedule from file: {schedule_file}")
        
        if schedule_text:
            schedule_parts.append(
                f"**Schedule description from user**:\n"
                f"--- START OF SCHEDULE ---\n"
                f"{schedule_text}\n"
                f"--- END OF SCHEDULE ---"
            )
            print("Loaded schedule description from user")
        
        if not schedule_parts:
            # Default: assume standard 4-5 hours/week
            schedule_parts.append(
                "No specific schedule was provided. "
                "Assume the user has a standard work schedule (9 AM - 5 PM, Monday-Friday) "
                "and can dedicate approximately 4-5 hours per week for development activities. "
                "Identify reasonable learning windows within this assumption."
            )
            print("No schedule provided — using default assumption (4-5 hrs/week)")
        
        # ------------------------------------------------------------------
        # 3. Execute agents sequentially
        # ------------------------------------------------------------------
        context = []
        
        for i, agent in enumerate(self.agents):
            if i == 0:
                # Agent 1: Career Input Analyst
                combined_input = "\n\n".join(input_parts)
                if use_structured_data and not feedback_file and not input_text:
                    task = (
                        "Below is the career-related input to analyze.\n\n"
                        f"{combined_input}\n\n"
                        "Complete your assigned task as described in your role."
                    )
                else:
                    task = (
                        "Below is the career-related input to analyze. This may include "
                        "performance reviews, aspirations, peer feedback, self-reflections, "
                        "or any combination thereof. Analyze it thoroughly and produce your "
                        "career input analysis report.\n\n"
                        "You do NOT need to call the parse_feedback_data tool — the full "
                        "input is provided here.\n\n"
                        f"{combined_input}\n\n"
                        "Complete your assigned task as described in your role."
                    )
            elif i == 2:
                # Agent 3: Schedule Analyzer
                combined_schedule = "\n\n".join(schedule_parts)
                task = (
                    "Below is the user's schedule/availability information. "
                    "Analyze it and identify all available learning windows.\n\n"
                    f"{combined_schedule}\n\n"
                    "Complete your assigned task as described in your role."
                )
            else:
                # Agent 2 (Learning Recommender) and Agent 4 (Plan Generator)
                task = "Complete your assigned task as described in your role."
            
            output = agent.execute(
                task_description=task,
                context=context if context else None
            )
            context.append(output)
        
        # Final output is from the last agent (Plan Generator)
        final_plan = context[-1]
        
        print()
        print("=" * 70)
        print("  CAREER DEVELOPMENT PLAN - COMPLETE")
        print("=" * 70)
        print()
        
        return final_plan
    
    def save_output(self, plan: str, output_path: str = "output_development_plan.md"):
        """Save the generated plan to a file."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# AI Career Development Plan\n\n")
            f.write("*Generated by AI Career Development & Performance Coach*\n")
            f.write("*Agent-based system without CrewAI framework*\n\n")
            f.write("---\n\n")
            f.write(plan)
        
        print(f"\nPlan saved to: {output_path}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AI Career Development & Performance Coach",
        epilog=(
            "Examples:\n"
            "  # With email and a performance review file:\n"
            "  python main.py --email user@company.com --feedback-file review.txt\n\n"
            "  # With aspirations text and schedule:\n"
            "  python main.py --email user@company.com \\\n"
            '    --input-text "I want to become a Staff Engineer. My manager says I need to improve communication." \\\n'
            '    --schedule-text "I can only spare 10 minutes in the afternoon and 30 minutes before bed"\n\n'
            "  # With a review file and schedule file:\n"
            "  python main.py --feedback-file sample_data/sample1.txt --schedule-file sample_data/sample_schedule.json\n\n"
            "  # Use structured 360-degree data (original mode):\n"
            "  python main.py\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--backend",
        choices=["anthropic", "ollama", "openai", "auto"],
        default="auto",
        help="LLM backend to use (default: auto-detect from env)"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Specific model to use (optional)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output_development_plan.md",
        help="Output file path (default: output_development_plan.md)"
    )
    parser.add_argument(
        "--email",
        type=str,
        default=None,
        help="User's email address for identification"
    )
    parser.add_argument(
        "--feedback-file",
        type=str,
        default=None,
        help="Path to a file containing career input (performance review, feedback, aspirations). Supports .txt, .pdf, .docx"
    )
    parser.add_argument(
        "--input-text",
        type=str,
        default=None,
        help="Direct text input: aspirations, feedback, self-reflection, or any career-related text"
    )
    parser.add_argument(
        "--schedule-file",
        type=str,
        default=None,
        help="Path to a file containing the user's calendar/weekly schedule (.json, .ics, .txt)"
    )
    parser.add_argument(
        "--schedule-text",
        type=str,
        default=None,
        help='Direct text description of availability (e.g., "10 minutes in the afternoon, 30 minutes before bed")'
    )
    
    args = parser.parse_args()
    
    # Check if we're likely to fail and suggest windsurf workflow
    if args.backend == "auto":
        backend = get_backend_from_env()
        if backend == "ollama":
            # Check if ollama is actually running
            try:
                import requests
                requests.get("http://localhost:11434/api/tags", timeout=1)
            except:
                print("\n⚠️  Ollama is not running!")
                print("\n💡 SUGGESTION: Use Windsurf workflow instead (no setup required)")
                print("   Run: python windsurf_workflow.py\n")
                choice = input("Continue anyway? (y/n): ").strip().lower()
                if choice != 'y':
                    sys.exit(0)
    
    try:
        orchestrator = CareerCoachOrchestrator(
            backend=args.backend,
            model=args.model
        )
        
        plan = orchestrator.run(
            email=args.email,
            feedback_file=args.feedback_file,
            input_text=args.input_text,
            schedule_file=args.schedule_file,
            schedule_text=args.schedule_text,
        )
        
        # Save first (UTF-8 file write won't fail on special chars)
        orchestrator.save_output(plan, args.output)
        
        # Print to console with fallback for Windows encoding issues
        try:
            print(plan)
        except UnicodeEncodeError:
            print(plan.encode("utf-8", errors="replace").decode("utf-8"))
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        print("\n" + "=" * 70)
        print("  TROUBLESHOOTING OPTIONS")
        print("=" * 70)
        print("\nOption 1: Use Ollama (Free, Local - RECOMMENDED)")
        print("  1. Install Ollama from https://ollama.ai")
        print("  2. Run: ollama pull llama3.1")
        print("  3. Run: ollama serve")
        print("  4. Run this script again: python main.py --backend ollama")
        print("\nOption 2: Use Windsurf Chat (No Setup Required!)")
        print("  Run: python windsurf_workflow.py")
        print("  This will guide you through using Windsurf's chat interface")
        print("\nOption 3: Get an API Key")
        print("  - Anthropic: https://console.anthropic.com/")
        print("  - OpenAI: https://platform.openai.com/")
        print("  Create a .env file and add your key")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
