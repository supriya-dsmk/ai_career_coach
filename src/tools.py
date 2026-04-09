"""
Custom tools for the AI Career Coach system.
These tools allow agents to parse feedback data and match skills to learning resources.
"""

import json
import os
from typing import Optional
from pathlib import Path


def _load_feedback_data(filepath: str = "sample_data/feedback_360.json") -> dict:
    """Load the 360-degree feedback JSON file."""
    # Handle both relative and absolute paths
    if not Path(filepath).is_absolute():
        # Assume it's relative to project root
        project_root = Path(__file__).parent.parent
        filepath = project_root / filepath
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_feedback_data(section: str = "all") -> str:
    """
    Parse and extract structured feedback data from the 360-degree review.
    
    Args:
        section: Which section to retrieve. Options:
            - 'all': Complete feedback data
            - 'manager': Manager review only
            - 'peers': Peer reviews only
            - 'reports': Direct report reviews only
            - 'self': Self-assessment only
            - 'employee': Employee profile info
            - 'ratings': Aggregated ratings across all reviewers
    
    Returns:
        JSON string containing the requested feedback data
    """
    data = _load_feedback_data()

    if section == "manager":
        return json.dumps(data["manager_review"], indent=2)
    elif section == "peers":
        return json.dumps(data["peer_reviews"], indent=2)
    elif section == "reports":
        return json.dumps(data["direct_report_reviews"], indent=2)
    elif section == "self":
        return json.dumps(data["self_assessment"], indent=2)
    elif section == "employee":
        return json.dumps(data["employee"], indent=2)
    elif section == "ratings":
        return _aggregate_ratings(data)
    else:
        return json.dumps(data, indent=2)


def _aggregate_ratings(data: dict) -> str:
    """Aggregate ratings across all reviewers into averages."""
    all_ratings = {}

    # Manager ratings
    for skill, score in data["manager_review"]["ratings"].items():
        all_ratings.setdefault(skill, []).append(score)

    # Peer ratings
    for peer in data["peer_reviews"]:
        for skill, score in peer["ratings"].items():
            all_ratings.setdefault(skill, []).append(score)

    # Direct report ratings
    for report in data["direct_report_reviews"]:
        for skill, score in report["ratings"].items():
            all_ratings.setdefault(skill, []).append(score)

    aggregated = {
        skill: round(sum(scores) / len(scores), 2)
        for skill, scores in all_ratings.items()
    }
    aggregated_sorted = dict(sorted(aggregated.items(), key=lambda x: x[1]))

    result = {
        "aggregated_ratings": aggregated_sorted,
        "lowest_rated": list(aggregated_sorted.keys())[:3],
        "highest_rated": list(aggregated_sorted.keys())[-3:],
    }
    return json.dumps(result, indent=2)


def match_learning_resources(skills: str) -> str:
    """
    Given a comma-separated list of skills or development areas,
    find matching learning resources from the company catalog.
    
    Args:
        skills: Comma-separated list of skills
            Example: 'communication, leadership, delegation'
    
    Returns:
        JSON string containing matched resources with details
    """
    data = _load_feedback_data()
    catalog = data.get("learning_resources_catalog", [])
    target_skills = [s.strip().lower() for s in skills.split(",")]

    matched = []
    for resource in catalog:
        resource_skills = [s.lower() for s in resource["skills"]]
        overlap = set(target_skills) & set(resource_skills)
        if overlap:
            entry = {
                "id": resource["id"],
                "title": resource["title"],
                "type": resource["type"],
                "provider": resource["provider"],
                "duration_hours": resource["duration_hours"],
                "format": resource["format"],
                "cost": resource["cost"],
                "matching_skills": list(overlap),
                "all_skills": resource["skills"],
            }
            url = resource.get("url", "")
            if url:
                entry["url"] = url
            matched.append(entry)

    matched.sort(key=lambda x: len(x["matching_skills"]), reverse=True)

    return json.dumps({
        "query_skills": target_skills,
        "total_matches": len(matched),
        "resources": matched,
    }, indent=2)


def parse_schedule_data(filepath: str = "") -> str:
    """
    Parse schedule/calendar data from a file and return a structured summary.
    
    Supports:
    - JSON files with schedule data
    - ICS (iCalendar) files
    - Plain text files with schedule descriptions
    
    Args:
        filepath: Path to the schedule file. If empty, returns sample schedule guidance.
    
    Returns:
        String containing the parsed schedule data
    """
    if not filepath:
        return json.dumps({
            "error": "No schedule file provided",
            "guidance": "Please provide a schedule file path or describe your weekly schedule as text."
        }, indent=2)
    
    # Resolve path
    schedule_path = Path(filepath)
    if not schedule_path.is_absolute():
        project_root = Path(__file__).parent.parent
        schedule_path = project_root / filepath
    
    if not schedule_path.exists():
        return json.dumps({
            "error": f"Schedule file not found: {schedule_path}",
            "guidance": "Please check the file path and try again."
        }, indent=2)
    
    suffix = schedule_path.suffix.lower()
    
    # Read the file
    with open(schedule_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if suffix == ".json":
        return _parse_json_schedule(content)
    elif suffix == ".ics":
        return _parse_ics_schedule(content)
    else:
        # Treat as plain text schedule description
        return _parse_text_schedule(content)


def _parse_json_schedule(content: str) -> str:
    """Parse a JSON-formatted schedule file."""
    try:
        data = json.loads(content)
        result = {
            "format": "json",
            "schedule_data": data,
            "summary": _summarize_json_schedule(data)
        }
        return json.dumps(result, indent=2)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"}, indent=2)


def _summarize_json_schedule(data: dict) -> dict:
    """Produce a summary from JSON schedule data."""
    summary = {
        "work_pattern": data.get("work_pattern", "Not specified"),
        "weekly_commitments": [],
        "free_windows": [],
        "total_free_minutes_per_week": 0,
    }
    
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    
    for day in days:
        day_data = data.get(day, data.get(day.capitalize(), None))
        if day_data:
            if isinstance(day_data, dict):
                commitments = day_data.get("commitments", day_data.get("busy", []))
                free = day_data.get("free", day_data.get("available", []))
                for c in commitments:
                    summary["weekly_commitments"].append({
                        "day": day.capitalize(),
                        "block": c
                    })
                for f_slot in free:
                    duration = f_slot.get("duration_minutes", 0)
                    summary["free_windows"].append({
                        "day": day.capitalize(),
                        "slot": f_slot
                    })
                    summary["total_free_minutes_per_week"] += duration
            elif isinstance(day_data, list):
                for item in day_data:
                    summary["weekly_commitments"].append({
                        "day": day.capitalize(),
                        "block": item
                    })
    
    return summary


def _parse_ics_schedule(content: str) -> str:
    """Parse an ICS (iCalendar) file and extract events."""
    events = []
    current_event = {}
    in_event = False
    
    for line in content.split("\n"):
        line = line.strip()
        if line == "BEGIN:VEVENT":
            in_event = True
            current_event = {}
        elif line == "END:VEVENT":
            in_event = False
            events.append(current_event)
        elif in_event and ":" in line:
            key, _, value = line.partition(":")
            # Strip parameters (e.g., DTSTART;VALUE=DATE:20250101)
            key = key.split(";")[0]
            current_event[key] = value
    
    result = {
        "format": "ics",
        "total_events": len(events),
        "events": events,
        "guidance": (
            "These are the calendar events found. The Schedule Analyzer agent "
            "will identify free windows between these events."
        )
    }
    return json.dumps(result, indent=2)


def _parse_text_schedule(content: str) -> str:
    """Parse a plain-text schedule description."""
    result = {
        "format": "text",
        "raw_schedule": content,
        "guidance": (
            "This is a free-text schedule description. The Schedule Analyzer "
            "agent will interpret this to identify available learning windows."
        )
    }
    return json.dumps(result, indent=2)


# Tool registry for easy access by the orchestrator
AVAILABLE_TOOLS = {
    "parse_feedback_data": {
        "function": parse_feedback_data,
        "description": "Parse and extract structured feedback data from the 360-degree review",
        "parameters": {
            "section": {
                "type": "string",
                "description": "Section to retrieve: 'all', 'manager', 'peers', 'reports', 'self', 'employee', or 'ratings'",
                "default": "all"
            }
        }
    },
    "match_learning_resources": {
        "function": match_learning_resources,
        "description": "Find learning resources matching specified skills",
        "parameters": {
            "skills": {
                "type": "string",
                "description": "Comma-separated list of skills (e.g., 'communication, leadership, delegation')",
                "required": True
            }
        }
    },
    "parse_schedule_data": {
        "function": parse_schedule_data,
        "description": "Parse schedule/calendar data from a file (JSON, ICS, or plain text)",
        "parameters": {
            "filepath": {
                "type": "string",
                "description": "Path to the schedule file",
                "default": ""
            }
        }
    }
}


def get_tool_descriptions() -> str:
    """Generate a formatted description of all available tools for the LLM."""
    descriptions = []
    for tool_name, tool_info in AVAILABLE_TOOLS.items():
        desc = f"\n**{tool_name}**\n"
        desc += f"Description: {tool_info['description']}\n"
        desc += "Parameters:\n"
        for param_name, param_info in tool_info['parameters'].items():
            required = param_info.get('required', False)
            default = param_info.get('default', 'N/A')
            desc += f"  - {param_name} ({param_info['type']}): {param_info['description']}\n"
            if not required:
                desc += f"    Default: {default}\n"
        descriptions.append(desc)
    
    return "\n".join(descriptions)


def execute_tool(tool_name: str, **kwargs) -> str:
    """Execute a tool by name with given parameters."""
    if tool_name not in AVAILABLE_TOOLS:
        return f"Error: Tool '{tool_name}' not found. Available tools: {list(AVAILABLE_TOOLS.keys())}"
    
    try:
        tool_function = AVAILABLE_TOOLS[tool_name]["function"]
        result = tool_function(**kwargs)
        return result
    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"
