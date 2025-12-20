from dataclasses import dataclass, fields, MISSING
from typing import Dict, Any, Optional, TypeVar, Type, get_origin, get_args
from datetime import datetime


def parse_datetime(value: Any, default: Optional[datetime] = None) -> datetime:
    if value is None:
        return default or datetime.utcnow()
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    return default or datetime.utcnow()


def _is_datetime_type(field_type: Any) -> bool:
    if field_type == datetime:
        return True
    origin = get_origin(field_type)
    if origin is not None:
        args = get_args(field_type)
        return datetime in args
    return False


T = TypeVar('T')


@dataclass
class SerializableDataclass:
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        kwargs = {}
        for field in fields(cls):
            field_name = field.name
            if field_name in data:
                value = data[field_name]
                if _is_datetime_type(field.type):
                    value = parse_datetime(value)
                kwargs[field_name] = value
            elif field.default is not MISSING:
                kwargs[field_name] = field.default
            elif field.default_factory is not MISSING:
                kwargs[field_name] = field.default_factory()
        return cls(**kwargs)

