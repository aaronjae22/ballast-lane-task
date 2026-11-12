"""The fake repository behaves like a store, so use-case tests can trust it."""

from tests.unit.builders import make_task
from tests.unit.fakes import InMemoryTaskRepository


def test_add_gives_new_tasks_ids_after_the_seeded_ones() -> None:
    repository = InMemoryTaskRepository(make_task(id=5))

    added = repository.add(make_task(id=None))

    assert added.id == 6


def test_a_change_without_save_is_not_stored() -> None:
    repository = InMemoryTaskRepository(make_task(id=1, title="Stored"))

    loaded = repository.get(1)
    assert loaded is not None
    loaded.title = "Changed but not saved"

    assert [task.title for task in repository.all()] == ["Stored"]


def test_get_returns_none_for_a_missing_task() -> None:
    assert InMemoryTaskRepository().get(1) is None
