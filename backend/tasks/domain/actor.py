"""The user making a change, as far as the rules need to know."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Actor:
    """Who is acting: their user id, and whether they're an admin (who may do anything)."""

    id: int
    is_admin: bool = False
