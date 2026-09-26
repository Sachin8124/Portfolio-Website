from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from google_drive import read_json_records, write_json_records


class Condition:
    def __init__(self, predicate: Callable[[Any], bool]):
        self.predicate = predicate

    def __call__(self, item: Any) -> bool:
        return self.predicate(item)

    def __or__(self, other: "Condition") -> "Condition":
        return Condition(lambda item: self(item) or other(item))

    def __and__(self, other: "Condition") -> "Condition":
        return Condition(lambda item: self(item) and other(item))


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


class Query:
    def __init__(self, session: "Session", model: type):
        self.session = session
        self.model = model
        self.items = session._load(model)

    def filter(self, *conditions: Condition) -> "Query":
        self.items = [item for item in self.items if all(condition(item) for condition in conditions)]
        return self

    def order_by(self, field: Field) -> "Query":
        reverse = field.name == "id" and self.model.__name__ != "LinkUrl"
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
        records = read_json_records(_records_filename(model))
        items = [model(**_deserialize_record(model, record)) for record in records]
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
        for model in self._dirty:
            records = [
                {field: _serialize_value(getattr(item, field, None)) for field in model.__fields__}
                for item in self._cache[model]
            ]
            write_json_records(_records_filename(model), records)
        self._dirty.clear()

    def rollback(self) -> None:
        self._cache.clear()
        self._dirty.clear()

    def close(self) -> None:
        self._cache.clear()


def _records_filename(model: type) -> str:
    return f"portfolio-{model.__name__.lower()}.json"


def _deserialize_record(model: type, record: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in model.__fields__:
        value = record.get(field, "")
        if field in {"id", "user_id"}:
            value = int(value or 0) if value else None
        elif field.endswith("_at") or field == "created_at":
            value = datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None) if value else datetime.utcnow()
        elif value == "":
            value = None
        result[field] = value
    return result


def _serialize_value(value: Any) -> Any:
    return value.isoformat() + "Z" if isinstance(value, datetime) else (value if value is not None else "")


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
