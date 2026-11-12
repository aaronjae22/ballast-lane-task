"""The overdue rule (spec section 3) as data: one case per row, judged on builders.TODAY.

Plain values, so every level can read the same rows: the domain test of Task.is_overdue()
and, from iteration 2, the overdue filter's test. The rule and its read-side copy can't drift.
"""

from datetime import date

from tasks.domain.status import Status
from tests.unit.builders import TODAY, YESTERDAY

# case id -> (status, due date, overdue on TODAY)
OVERDUE_CASES: dict[str, tuple[Status, date | None, bool]] = {
    "to-do-due-yesterday": (Status.TO_DO, YESTERDAY, True),
    "in-progress-due-yesterday": (Status.IN_PROGRESS, YESTERDAY, True),
    "done": (Status.DONE, YESTERDAY, False),
    "due-today": (Status.TO_DO, TODAY, False),
    "no-due-date": (Status.TO_DO, None, False),
}
