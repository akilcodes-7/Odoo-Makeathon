"""Shared service exceptions translated by HTTP views."""


class DomainValidationError(Exception):
    def __init__(self, code: str, message: str, field_errors: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field_errors = field_errors or {}


class DiscountCapacityChanged(Exception):
    """Raised when a candidate discount loses capacity during reservation."""
