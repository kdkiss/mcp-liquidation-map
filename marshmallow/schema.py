from __future__ import annotations

from typing import Any, Dict

from .exceptions import ValidationError
from .fields import Field


class SchemaMeta(type):
    def __new__(mcls, name, bases, attrs):
        declared_fields: Dict[str, Field] = {}
        for base in reversed(bases):
            base_fields = getattr(base, '_declared_fields', None)
            if base_fields:
                declared_fields.update(base_fields)

        fields_for_class = {}
        for key, value in list(attrs.items()):
            if isinstance(value, Field):
                fields_for_class[key] = value
                attrs.pop(key)

        declared_fields.update(fields_for_class)
        attrs['_declared_fields'] = declared_fields
        return super().__new__(mcls, name, bases, attrs)


class Schema(metaclass=SchemaMeta):
    def load(self, data: Any, partial: bool = False):
        if not isinstance(data, dict):
            raise ValidationError({'_schema': ['Invalid input type.']})

        errors: Dict[str, Any] = {}
        result: Dict[str, Any] = {}

        for field_name, field in self._declared_fields.items():
            if field_name not in data:
                if field.required and not partial:
                    errors.setdefault(field_name, []).append('Missing data for required field.')
                continue

            try:
                result[field_name] = field.deserialize(data[field_name])
            except ValidationError as err:
                message = err.messages
                if isinstance(message, list):
                    errors[field_name] = message
                else:
                    errors.setdefault(field_name, []).append(message)

        if errors:
            raise ValidationError(errors)

        for field_name in data.keys():
            if field_name in self._declared_fields:
                continue
            # Preserve whitelisted fields only; unknowns are ignored.
            pass

        return result
