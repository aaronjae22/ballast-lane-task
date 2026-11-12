"""When the assignee gets an email (spec section 3, "Assignment email")."""


def assignment_email_due(
    *, previous_assignee_id: int | None, new_assignee_id: int | None, changed_by_id: int
) -> bool:
    """True only when the assignee changes to someone other than the person making the change.

    So no email for self-assignment, for unassigning, or for reassigning a task to the person
    who already has it. Creating a task counts as a change from no assignee.
    """
    return new_assignee_id is not None and new_assignee_id not in (
        previous_assignee_id,
        changed_by_id,
    )
