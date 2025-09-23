"""A minimal subset of the Marshmallow API used for request validation.

This lightweight implementation provides the pieces required by the
application's request schemas without pulling in the full dependency.
It mirrors the interfaces for ``Schema``, ``ValidationError`` and the
``fields`` module that our code relies on.
"""

from .exceptions import ValidationError
from . import fields
from .schema import Schema

__all__ = ['Schema', 'ValidationError', 'fields']
