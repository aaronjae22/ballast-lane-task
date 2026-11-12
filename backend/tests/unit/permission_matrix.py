"""The permission matrix from spec section 3, as data.

One row per action, one column per role. Plain strings, so every level can read the same
rows: the domain rule, the use cases and, from iteration 2, the visible_tasks selector.
"""

ALLOWED = "allowed"
NOT_ALLOWED = "NotAllowed"  # 403
NOT_FOUND = "TaskNotFound"  # 404

ROLES = ("owner", "assignee", "admin", "anyone else")

# fmt: off
MATRIX: dict[str, tuple[str, str, str, str]] = {
    #                  owner    assignee     admin    anyone else
    "view":          (ALLOWED, ALLOWED,     ALLOWED, NOT_FOUND),
    "edit":          (ALLOWED, NOT_ALLOWED, ALLOWED, NOT_FOUND),
    "assign":        (ALLOWED, NOT_ALLOWED, ALLOWED, NOT_FOUND),
    "change_status": (ALLOWED, ALLOWED,     ALLOWED, NOT_FOUND),
    "delete":        (ALLOWED, NOT_ALLOWED, ALLOWED, NOT_FOUND),
}
# fmt: on


def matrix_cases() -> list[tuple[str, str, str]]:
    """Every (action, role, outcome) cell of the matrix."""
    return [
        (action, role, outcome)
        for action, outcomes in MATRIX.items()
        for role, outcome in zip(ROLES, outcomes, strict=True)
    ]
