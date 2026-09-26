from __future__ import annotations

from datetime import datetime
from typing import Any, Callable


_IN_MEMORY_RECORDS: dict[type, list[Any]] = {}


class Condition:
    def __init__(self, predicate: Callable[[Any], bool]):
        self.predicate = predicate

    def __call__(self, item: Any) -> bool:
        return self.predicate(item)

    def __or__(self, other: "Condition") -> "Condition":
        return Condition(lambda item: self(item) or other(item))

    def __and__(self, other: "Condition") -> "Condition":
        return Condition(lambda item: self(item) and other(item))


class Ordering:
    def __init__(self, field: "Field", reverse: bool):
        self.field = field
        self.reverse = reverse


class Field:
    def __init__(self, name: str):
        self.name = name

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        return self if instance is None else instance.__dict__.get(self.name)

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __eq__(self, value: Any) -> Condition:
        return Condition(lambda item: getattr(item, self.name, None) == value)

    def ilike(self, pattern: str) -> Condition:
        needle = pattern.strip("%").lower()
        return Condition(lambda item: needle in str(getattr(item, self.name, "") or "").lower())

    def asc(self) -> Ordering:
        return Ordering(self, reverse=False)

    def desc(self) -> Ordering:
        return Ordering(self, reverse=True)


class Query:
    def __init__(self, session: "Session", model: type):
        self.session = session
        self.model = model
        self.items = session._load(model)

    def filter(self, *conditions: Condition) -> "Query":
        self.items = [item for item in self.items if all(condition(item) for condition in conditions)]
        return self

    def order_by(self, ordering: Ordering | Field) -> "Query":
        if isinstance(ordering, Ordering):
            field = ordering.field
            reverse = ordering.reverse
        else:
            field = ordering
            reverse = False
        self.items.sort(key=lambda item: getattr(item, field.name, 0) or 0, reverse=reverse)
        return self

    def all(self) -> list[Any]:
        return self.items

    def first(self) -> Any | None:
        return self.items[0] if self.items else None

    def count(self) -> int:
        return len(self.items)

    def delete(self) -> int:
        for item in self.items:
            self.session.delete(item)
        return len(self.items)


class Session:
    def __init__(self) -> None:
        self._cache: dict[type, list[Any]] = {}
        self._dirty: set[type] = set()

    def _load(self, model: type) -> list[Any]:
        if model in self._cache:
            return self._cache[model]
        items = _IN_MEMORY_RECORDS.setdefault(model, [])
        self._cache[model] = items
        return items

    def query(self, model: type) -> Query:
        return Query(self, model)

    def add(self, item: Any) -> None:
        items = self._load(type(item))
        if not getattr(item, "id", None):
            item.id = max((getattr(existing, "id", 0) or 0 for existing in items), default=0) + 1
        if not getattr(item, "created_at", None):
            item.created_at = datetime.utcnow()
        items.append(item)
        self._dirty.add(type(item))

    def add_all(self, items: list[Any]) -> None:
        for item in items:
            self.add(item)

    def delete(self, item: Any) -> None:
        items = self._load(type(item))
        if item in items:
            items.remove(item)
            self._dirty.add(type(item))

    def mark_dirty(self, model: type) -> None:
        self._dirty.add(model)

    def flush(self) -> None:
        return None

    def refresh(self, item: Any) -> None:
        return None

    def commit(self) -> None:
        self._dirty.clear()

    def rollback(self) -> None:
        self._cache.clear()
        self._dirty.clear()

    def close(self) -> None:
        self._cache.clear()


class SessionFactory:
    def __call__(self) -> Session:
        return Session()


SessionLocal = SessionFactory()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
