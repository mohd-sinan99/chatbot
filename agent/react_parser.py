"""
Dynamic ReAct Parser (📘 L1, L3: Think → Act → Look)
Parses Thought, Action, and Action Input structures from raw text or LLM completions.
"""

import re
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple


@dataclass
class ReActStep:
    thought: str
    action: Optional[str] = None
    action_input: Dict[str, Any] = None
    is_final: bool = False
    final_answer: Optional[str] = None


class ReActParser:
    """
    Parses standard ReAct text formats:
    Thought: <reasoning>
    Action: <tool_name>
    Action Input: <json or key-value args>
    """

    @classmethod
    def parse(cls, text: str) -> ReActStep:
        clean_text = text.strip()

        # Check for Final Answer first
        final_match = re.search(r'Final Answer:\s*(.*)', clean_text, re.DOTALL | re.IGNORECASE)
        if final_match:
            thought_part = clean_text[:final_match.start()].strip()
            thought = cls._extract_thought(thought_part) or "Formulating final trip plan."
            return ReActStep(
                thought=thought,
                is_final=True,
                final_answer=final_match.group(1).strip()
            )

        # Extract Thought
        thought = cls._extract_thought(clean_text) or "Evaluating next step."

        # Extract Action
        action = None
        action_match = re.search(r'Action:\s*([a-zA-Z0-9_\-]+)', clean_text, re.IGNORECASE)
        if action_match:
            action = action_match.group(1).strip()

        # Extract Action Input
        action_input = {}
        input_match = re.search(r'Action Input:\s*(\{.*\}|[^\n]+)', clean_text, re.DOTALL | re.IGNORECASE)
        if input_match:
            raw_input = input_match.group(1).strip()
            # Try parsing as JSON
            try:
                # Find outermost JSON object
                json_match = re.search(r'\{.*\}', raw_input, re.DOTALL)
                if json_match:
                    action_input = json.loads(json_match.group(0))
                else:
                    action_input = {"query": raw_input}
            except json.JSONDecodeError:
                action_input = {"query": raw_input}

        return ReActStep(
            thought=thought,
            action=action,
            action_input=action_input or {},
            is_final=False
        )

    @classmethod
    def _extract_thought(cls, text: str) -> Optional[str]:
        thought_match = re.search(r'Thought:\s*([^\n]+(?:\n[^\n]+)*?)(?=\nAction:|\Z)', text, re.IGNORECASE)
        if thought_match:
            return thought_match.group(1).strip()
        # If no explicit "Thought:" prefix, take everything before "Action:"
        before_action = re.split(r'Action:', text, flags=re.IGNORECASE)[0].strip()
        return before_action if before_action else None

    @classmethod
    def format_prompt(cls, tools_description: str, question: str, scratchpad: str) -> str:
        """Construct standard ReAct prompt format."""
        return (
            f"You are a helpful travel planning assistant.\n"
            f"You have access to the following tools:\n\n"
            f"{tools_description}\n\n"
            f"Use the following format:\n"
            f"Question: the input question you must answer\n"
            f"Thought: you should always think about what to do\n"
            f"Action: the action to take, should be one of the tool names\n"
            f"Action Input: the input to the action as a valid JSON dictionary\n"
            f"Observation: the result of the action\n"
            f"... (this Thought/Action/Action Input/Observation can repeat N times)\n"
            f"Thought: I now have enough information to form the final itinerary\n"
            f"Final Answer: the complete travel plan with details and disclaimers\n\n"
            f"Begin!\n\n"
            f"Question: {question}\n"
            f"{scratchpad}"
        )

