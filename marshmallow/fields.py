from __future__ import annotations

import re
from typing import Any

from .exceptions import ValidationError


class Field:
    def __init__(self, *, required: bool = False):
        self.required = required

    def deserialize(self, value: Any):
        return value


class Str(Field):
    def deserialize(self, value: Any):
        value = super().deserialize(value)
        if not isinstance(value, str):
            raise ValidationError('Not a valid string.')
        return value


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Email(Str):
    def deserialize(self, value: Any):
        value = super().deserialize(value)
        if not _EMAIL_PATTERN.match(value):
            raise ValidationError('Not a valid email address.')
        return value
