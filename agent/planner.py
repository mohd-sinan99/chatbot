"""
Planner Engine (📘 L5: A plan before it acts)
Formulates a structured multi-step plan before tool execution and tracks step-by-step progress.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class StepStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"


@dataclass
class PlanStep:
    step_id: int
    title: str
    description: str
    expected_tool: Optional[str] = None
    status: StepStatus = StepStatus.PENDING
    result_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "description": self.description,
            "expected_tool": self.expected_tool,
            "status": self.status.value,
            "result_summary": self.result_summary,
        }


@dataclass
class ExecutionPlan:
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    created_at: str = ""

    def get_current_step(self) -> Optional[PlanStep]:
        """Return the first pending or in-progress step."""
        for step in self.steps:
            if step.status in (StepStatus.PENDING, StepStatus.IN_PROGRESS):
                return step
        return None

    def is_complete(self) -> bool:
        """Check if all steps are completed or skipped."""
        return all(s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED) for s in self.steps)

    def mark_step_in_progress(self, step_id: int) -> None:
        for s in self.steps:
            if s.step_id == step_id:
                s.status = StepStatus.IN_PROGRESS
                break

    def mark_step_completed(self, step_id: int, summary: str = "") -> None:
        for s in self.steps:
            if s.step_id == step_id:
                s.status = StepStatus.COMPLETED
                s.result_summary = summary
                break

    def to_markdown(self) -> str:
        """Render plan checklist in Markdown for logging and transparency."""
        lines = [f"### Execution Plan: {self.goal}"]
        for s in self.steps:
            mark = " "
            if s.status == StepStatus.COMPLETED:
                mark = "X"
            elif s.status == StepStatus.IN_PROGRESS:
                mark = "-"
            lines.append(f"- [{mark}] Step {s.step_id}: {s.title}")
            if s.result_summary:
                lines.append(f"      Summary: {s.result_summary}")
        return "\n".join(lines)


class PlannerEngine:
    """
    Creates tailored execution plans before the agent starts executing tools (📘 L5).
    """

    @staticmethod
    def create_trip_planning_plan(
        destination: str,
        duration_days: int,
        travelers: int,
        budget: Optional[float] = None,
        origin: Optional[str] = None
    ) -> ExecutionPlan:
        steps = [
            PlanStep(
                step_id=1,
                title=f"Research attractions & timings for {destination}",
                description="Query verified places of interest, opening hours, and entry costs.",
                expected_tool="search_destination_and_attractions"
            ),
            PlanStep(
                step_id=2,
                title=f"Estimate category-wise budget for {duration_days} day(s) for {travelers} traveler(s)",
                description="Calculate stay, meals, local commute, and contingency buffer; evaluate against target budget.",
                expected_tool="calculate_budget_breakdown"
            ),
        ]

        # Only add transport step if origin is provided or needed
        if origin:
            steps.append(
                PlanStep(
                    step_id=len(steps) + 1,
                    title=f"Compare transport options from {origin} to {destination}",
                    description="Evaluate bus, train, and road routes with fare brackets.",
                    expected_tool="find_transport_options"
                )
            )

        steps.append(
            PlanStep(
                step_id=len(steps) + 1,
                title=f"Retrieve weather, safety rules & packing tips for {destination}",
                description="Check seasonal weather, night travel bans, permits, and packing guidelines.",
                expected_tool="get_travel_advisory_and_weather"
            )
        )

        steps.append(
            PlanStep(
                step_id=len(steps) + 1,
                title="Synthesize day-by-day balanced itinerary & disclaimers",
                description="Sequence activities with realistic travel time buffers, meal breaks, and clear estimate disclaimers.",
                expected_tool=None  # Synthesized by agent
            )
        )

        return ExecutionPlan(
            goal=f"Plan a {duration_days}-day trip to {destination} for {travelers} person(s)",
            steps=steps
        )

