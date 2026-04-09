"""
Windsurf Manual Workflow Mode
==============================
This script helps you run the AI Career Coach using Windsurf's chat interface.
Since Windsurf doesn't expose a programmable API, this guides you through
each agent step manually.

Supports:
  - Email-based user identification
  - Any kind of career input (reviews, aspirations, feedback)
  - Schedule/availability input for time-aware planning
  - 4-agent pipeline: Input Analyst -> Learning Recommender -> Schedule Analyzer -> Plan Generator
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tools import parse_feedback_data, match_learning_resources, parse_schedule_data


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
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


class WindsurfWorkflowGuide:
    """Guides the user through manual execution using Windsurf."""
    
    def __init__(
        self,
        email: Optional[str] = None,
        feedback_file: Optional[str] = None,
        input_text: Optional[str] = None,
        schedule_file: Optional[str] = None,
        schedule_text: Optional[str] = None,
        generate_only: bool = False,
    ):
        self.agents_dir = Path(__file__).parent / "agents"
        self.outputs: List[str] = []
        self.current_step = 0
        self.email = email
        self.feedback_file = feedback_file
        self.input_text = input_text
        self.schedule_file = schedule_file
        self.schedule_text = schedule_text
        self.generate_only = generate_only

        # Pre-build input fragments
        self._career_input = self._build_career_input()
        self._schedule_input = self._build_schedule_input()
        
    def _build_career_input(self) -> str:
        """Build career input text from all provided sources."""
        parts = []

        if self.email:
            parts.append(f"**User Email**: {self.email}")

        if self.feedback_file:
            content = _read_input_file(self.feedback_file)
            if content:
                parts.append(
                    f"**Input from file** ({self.feedback_file}):\n"
                    f"--- START OF FILE CONTENT ---\n{content}\n--- END OF FILE CONTENT ---"
                )

        if self.input_text:
            parts.append(
                f"**Direct input from user**:\n"
                f"--- START OF USER INPUT ---\n{self.input_text}\n--- END OF USER INPUT ---"
            )

        if not parts:
            parts.append(
                "Structured 360-degree feedback data is available. "
                "Use the parse_feedback_data tool to retrieve it."
            )

        return "\n\n".join(parts)

    def _build_schedule_input(self) -> str:
        """Build schedule input text from all provided sources."""
        parts = []

        if self.schedule_file:
            content = _read_input_file(self.schedule_file)
            if content:
                parts.append(
                    f"**Schedule from file** ({self.schedule_file}):\n"
                    f"--- START OF SCHEDULE ---\n{content}\n--- END OF SCHEDULE ---"
                )

        if self.schedule_text:
            parts.append(
                f"**Schedule description from user**:\n"
                f"--- START OF SCHEDULE ---\n{self.schedule_text}\n--- END OF SCHEDULE ---"
            )

        if not parts:
            parts.append(
                "No specific schedule was provided. "
                "Assume the user has a standard work schedule (9 AM - 5 PM, Monday-Friday) "
                "and can dedicate approximately 4-5 hours per week for development activities."
            )

        return "\n\n".join(parts)

    def print_header(self, text: str):
        """Print a formatted header."""
        print("\n" + "=" * 70)
        print(f"  {text}")
        print("=" * 70 + "\n")
    
    def print_section(self, text: str):
        """Print a formatted section."""
        print("\n" + "-" * 70)
        print(f"  {text}")
        print("-" * 70 + "\n")
    
    def load_agent_prompt(self, agent_file: str) -> str:
        """Load an agent's prompt from its .md file."""
        agent_path = self.agents_dir / agent_file
        with open(agent_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def prepare_prompt_with_context(self, agent_prompt: str, context: Optional[list] = None) -> str:
        """Prepare the complete prompt with context from previous agents."""
        if not context:
            return agent_prompt
        
        context_text = "\n\n# CONTEXT FROM PREVIOUS AGENTS\n\n"
        for i, ctx in enumerate(context, 1):
            context_text += f"## Output from Agent {i}\n\n{ctx}\n\n"
        
        return context_text + "\n\n" + agent_prompt
    
    def show_available_tools(self):
        """Show which tools are available and how to use them."""
        print("AVAILABLE TOOLS:\n")
        print("1. parse_feedback_data(section)")
        print("   Sections: 'employee', 'ratings', 'manager', 'peers', 'reports', 'self', 'all'")
        print("   Example: parse_feedback_data('ratings')\n")
        print("2. match_learning_resources(skills)")
        print("   Example: match_learning_resources('communication, leadership, delegation')\n")
        print("3. parse_schedule_data(filepath)")
        print("   Example: parse_schedule_data('sample_data/sample_schedule.json')\n")
        print("You can execute these tools below when needed.")
    
    def execute_tool_interactive(self):
        """Allow user to execute tools interactively."""
        print("\n" + "=" * 70)
        print("  TOOL EXECUTION (Optional)")
        print("=" * 70 + "\n")
        
        print("If your agent needs to call tools, you can execute them here.")
        print("Available commands:")
        print("  1 - parse_feedback_data")
        print("  2 - match_learning_resources")
        print("  3 - parse_schedule_data")
        print("  q - Done with tools, continue to next agent")
        
        while True:
            print()
            choice = input("Enter command (1/2/3/q): ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == '1':
                section = input("Enter section (employee/ratings/manager/peers/reports/self/all): ").strip()
                print(f"\n--- Tool Output ---")
                result = parse_feedback_data(section)
                print(result)
                print("--- End Tool Output ---\n")
                print("(Copy this output to use in Windsurf chat if needed)")
            elif choice == '2':
                skills = input("Enter comma-separated skills: ").strip()
                print(f"\n--- Tool Output ---")
                result = match_learning_resources(skills)
                print(result)
                print("--- End Tool Output ---\n")
                print("(Copy this output to use in Windsurf chat if needed)")
            elif choice == '3':
                filepath = input("Enter schedule file path: ").strip()
                print(f"\n--- Tool Output ---")
                result = parse_schedule_data(filepath)
                print(result)
                print("--- End Tool Output ---\n")
                print("(Copy this output to use in Windsurf chat if needed)")
            else:
                print("Invalid choice. Try again.")

    def _build_task_for_agent(self, agent_index: int) -> str:
        """Build the task string for a given agent (0-based index)."""
        if agent_index == 0:
            # Career Input Analyst
            has_direct_input = self.feedback_file or self.input_text
            if has_direct_input:
                return (
                    "Below is the career-related input to analyze. This may include "
                    "performance reviews, aspirations, peer feedback, self-reflections, "
                    "or any combination thereof. Analyze it thoroughly and produce your "
                    "career input analysis report.\n\n"
                    "You do NOT need to call the parse_feedback_data tool -- the full "
                    "input is provided here.\n\n"
                    f"{self._career_input}\n\n"
                    "Complete your assigned task as described in your role."
                )
            else:
                return (
                    "Below is the career-related input to analyze.\n\n"
                    f"{self._career_input}\n\n"
                    "Complete your assigned task as described in your role."
                )
        elif agent_index == 2:
            # Schedule Analyzer
            return (
                "Below is the user's schedule/availability information. "
                "Analyze it and identify all available learning windows.\n\n"
                f"{self._schedule_input}\n\n"
                "Complete your assigned task as described in your role."
            )
        else:
            return "Complete your assigned task as described in your role."

    def run_agent_step(self, agent_name: str, agent_file: str, agent_index: int) -> str:
        """Guide user through one agent step."""
        self.current_step += 1
        
        self.print_header(f"STEP {self.current_step}: {agent_name}")
        
        # Load agent prompt
        agent_prompt = self.load_agent_prompt(agent_file)
        
        # Build the task
        task = self._build_task_for_agent(agent_index)

        # Combine agent prompt + task + context
        if self.outputs:
            context_section = "# CONTEXT FROM PREVIOUS AGENTS\n\n"
            for i, ctx in enumerate(self.outputs, 1):
                context_section += f"## Output from Agent {i}\n\n{ctx}\n\n"
            full_prompt = context_section + "\n\n" + agent_prompt + "\n\n# YOUR TASK\n\n" + task
        else:
            full_prompt = agent_prompt + "\n\n# YOUR TASK\n\n" + task
        
        # Save prompt to file
        prompt_file = f"windsurf_prompt_step{self.current_step}.txt"
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(full_prompt)
        
        print(f"Agent: {agent_name}")
        print(f"Prompt file saved: {prompt_file}")
        print(f"Prompt length: {len(full_prompt):,} characters\n")

        if self.generate_only:
            print(f"[generate-only mode] Prompt written to {prompt_file}")
            self.outputs.append(f"[Agent {self.current_step} output - paste from Windsurf]")
            return self.outputs[-1]

        print("INSTRUCTIONS:")
        print(f"1. Open the file '{prompt_file}' or copy the text below")
        print("2. Paste it into Windsurf chat")
        print("3. Review the agent's response")
        print("4. Come back here and paste the agent's output\n")
        
        self.show_available_tools()
        
        print("\n" + "=" * 70)
        print("  PROMPT TO COPY TO WINDSURF")
        print("=" * 70 + "\n")
        print(full_prompt)
        print("\n" + "=" * 70 + "\n")
        
        # Offer tool execution
        tool_choice = input("Do you need to execute tools before running the agent? (y/n): ").strip().lower()
        if tool_choice == 'y':
            self.execute_tool_interactive()
        
        # Wait for user to paste output
        print("\n" + "=" * 70)
        print("  PASTE AGENT OUTPUT")
        print("=" * 70 + "\n")
        print("After running the prompt in Windsurf, paste the agent's output below.")
        print("When done, press Enter, then type END on a new line, then press Enter again.\n")
        
        lines = []
        while True:
            try:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            except EOFError:
                break
        
        output = "\n".join(lines)
        
        if not output.strip():
            print("\nWarning: No output received. Using placeholder.")
            output = f"[Agent {self.current_step} output not provided]"
        
        # Save output
        output_file = f"agent{self.current_step}_output.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\nOutput saved to: {output_file}")
        
        self.outputs.append(output)
        return output
    
    def run(self):
        """Run the complete workflow."""
        self.print_header("AI Career Coach - Windsurf Manual Workflow")
        
        print("Welcome! This guide will help you run the AI Career Coach using")
        print("Windsurf's chat interface.\n")
        
        if self.email:
            print(f"  User Email: {self.email}")
        if self.feedback_file:
            print(f"  Career Input File: {self.feedback_file}")
        if self.input_text:
            print(f"  Direct Input: {self.input_text[:80]}...")
        if self.schedule_file:
            print(f"  Schedule File: {self.schedule_file}")
        if self.schedule_text:
            print(f"  Schedule: {self.schedule_text[:80]}...")
        
        print("\nThe process (4 agents):")
        print("  1. Career Input Analyst   - Analyzes your career input")
        print("  2. Learning Recommender   - Maps gaps to learning resources")
        print("  3. Schedule Analyzer      - Identifies your available learning time")
        print("  4. Plan Generator         - Builds your schedule-aware 90-day plan\n")

        agents = [
            ("Career Input Analyst",  "feedback_analyzer.md"),
            ("Learning Recommender",  "learning_recommender.md"),
            ("Schedule Analyzer",     "schedule_analyzer.md"),
            ("Plan Generator",        "plan_generator.md"),
        ]
        
        if not self.generate_only:
            input("Press Enter to start...")

        for idx, (name, md_file) in enumerate(agents):
            self.run_agent_step(name, md_file, agent_index=idx)
        
        # Save final output
        self.print_header("WORKFLOW COMPLETE!")
        
        final_plan = self.outputs[-1]
        
        output_file = "output_development_plan.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# AI Career Development Plan\n\n")
            f.write("*Generated by AI Career Development & Performance Coach*\n")
            f.write("*Using Windsurf Manual Workflow*\n\n")
            f.write("---\n\n")
            f.write(final_plan)
        
        print(f"Final plan saved to: {output_file}\n")
        print("All intermediate files saved:")
        for i in range(1, 5):
            print(f"  - windsurf_prompt_step{i}.txt")
            print(f"  - agent{i}_output.txt")
        print(f"  - {output_file}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Career Coach - Windsurf Manual Workflow",
        epilog=(
            "Examples:\n"
            "  # Generate prompts only (no interactive input needed):\n"
            "  python windsurf_workflow.py --generate-only --email user@co.com "
            "--feedback-file sample_data/sample1.txt --schedule-file sample_data/sample_schedule.txt\n\n"
            "  # Interactive mode with inputs:\n"
            "  python windsurf_workflow.py --email user@co.com "
            '--input-text "I want to become a Staff Engineer" '
            '--schedule-text "10 minutes at lunch, 30 minutes before bed"\n\n'
            "  # Original mode (uses structured 360-degree data):\n"
            "  python windsurf_workflow.py\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--email", type=str, default=None,
                        help="User's email address")
    parser.add_argument("--feedback-file", type=str, default=None,
                        help="Path to career input file (.txt, .pdf, .docx)")
    parser.add_argument("--input-text", type=str, default=None,
                        help="Direct text input (aspirations, feedback, etc.)")
    parser.add_argument("--schedule-file", type=str, default=None,
                        help="Path to schedule/calendar file (.json, .ics, .txt)")
    parser.add_argument("--schedule-text", type=str, default=None,
                        help='Schedule description (e.g., "10 min at lunch, 30 min before bed")')
    parser.add_argument("--generate-only", action="store_true",
                        help="Only generate prompt files, skip interactive paste steps")

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  AI Career Coach - Windsurf Manual Workflow")
    print("=" * 70 + "\n")
    
    print("This mode allows you to use Windsurf's chat interface with the")
    print("agent prompts. Perfect when you don't have API keys!\n")
    
    guide = WindsurfWorkflowGuide(
        email=args.email,
        feedback_file=args.feedback_file,
        input_text=args.input_text,
        schedule_file=args.schedule_file,
        schedule_text=args.schedule_text,
        generate_only=args.generate_only,
    )
    
    try:
        guide.run()
    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted. You can resume by running this script again.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
