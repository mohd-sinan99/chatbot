"""
Safety Guardrails & Audit Logger (📘 L7: Safety: asks you first, step limit, log)
Enforces human-in-the-loop approvals, step limits to prevent runaway loops, and audit logging.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable


@dataclass
class LogEntry:
    timestamp: str
    step_num: int
    entry_type: str  # "THOUGHT", "ACTION", "LOOK", "SAFETY", "PLAN", "FINAL"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        prefix = f"[{self.timestamp}] [STEP {self.step_num}] [{self.entry_type}]"
        return f"{prefix} {self.content}"


class ExecutionLogger:
    """
    Structured logger that records every stage of agent reasoning and action (📘 L7).
    """

    def __init__(self, verbose: bool = True):
        self.logs: List[LogEntry] = []
        self.verbose = verbose

    def _add_log(self, step_num: int, entry_type: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> LogEntry:
        now_str = datetime.now().strftime("%H:%M:%S")
        entry = LogEntry(
            timestamp=now_str,
            step_num=step_num,
            entry_type=entry_type,
            content=content,
            metadata=metadata or {}
        )
        self.logs.append(entry)
        if self.verbose:
            print(str(entry))
        return entry

    def log_thought(self, step_num: int, thought: str) -> None:
        self._add_log(step_num, "THOUGHT", thought)

    def log_action(self, step_num: int, tool_name: str, arguments: Dict[str, Any]) -> None:
        self._add_log(step_num, "ACTION", f"Calling tool '{tool_name}' with args {arguments}", metadata={"tool": tool_name, "args": arguments})

    def log_look(self, step_num: int, observation: str) -> None:
        self._add_log(step_num, "LOOK", f"Observed:\n{observation}")

    def log_safety(self, step_num: int, message: str) -> None:
        self._add_log(step_num, "SAFETY", message)

    def log_plan(self, step_num: int, plan_markdown: str) -> None:
        self._add_log(step_num, "PLAN", f"\n{plan_markdown}")

    def log_final(self, step_num: int, message: str) -> None:
        self._add_log(step_num, "FINAL", message)

    def get_full_trace(self) -> str:
        """Return the formatted audit trail of the entire execution."""
        return "\n".join(str(e) for e in self.logs)


class SafetyGuardrails:
    """
    Safety controls: Step limits and Human-in-the-Loop approval triggers (📘 L7).
    """

    def __init__(
        self,
        max_steps: int = 10,
        approval_callback: Optional[Callable[[str], bool]] = None
    ):
        self.max_steps = max_steps
        self.approval_callback = approval_callback

    def check_step_limit(self, current_step: int) -> bool:
        """
        Enforce hard ceiling on iterations (📘 L7).
        Returns True if within limit, False if limit exceeded.
        """
        return current_step <= self.max_steps

    def request_human_approval(self, reason: str, details: str) -> bool:
        """
        Human-in-the-loop approval: Asks you first before proceeding with sensitive actions (📘 L7).
        E.g., Budget overrun confirmation or overwriting a saved trip.
        """
        prompt = (
            f"\n⚠️  [SAFETY APPROVAL REQUIRED]\n"
            f"Reason: {reason}\n"
            f"Details: {details}\n"
            f"Do you approve proceeding with this action? (yes/no): "
        )

        if self.approval_callback:
            return self.approval_callback(prompt)

        # Default fallback to console input
        try:
            user_input = input(prompt).strip().lower()
            return user_input in ("yes", "y")
        except EOFError:
            # Safe default when running non-interactively
            return False

    def evaluate_budget_safety(
        self,
        total_estimated: float,
        target_budget: Optional[float]
    ) -> Dict[str, Any]:
        """
        Checks if estimated expenses exceed the user's budget.
        Triggers safety alert if overrun is detected.
        """
        if not target_budget or target_budget <= 0:
            return {"safe": True, "action_needed": False}

        if total_estimated > target_budget:
            overrun = total_estimated - target_budget
            return {
                "safe": False,
                "action_needed": True,
                "overrun_amount": overrun,
                "message": (
                    f"Estimated trip cost (₹{total_estimated:,.0f}) exceeds your target budget "
                    f"(₹{target_budget:,.0f}) by ₹{overrun:,.0f}."
                )
            }

        return {"safe": True, "action_needed": False}

