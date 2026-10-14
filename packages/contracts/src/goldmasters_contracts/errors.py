"""The C-09 error contract (Schema.md §10; D-23).

:class:`ErrorPayload` reproduces the documented error envelope exactly. Because
retryability "is determined by code, not by model judgement" (Schema.md §10), it
is a property of :class:`ErrorCode` and never a caller-supplied value: the field
is forced to what the code declares even when a document supplies its own.

The code vocabulary is closed and grows only by minor bump (D-23) — adding a
member is non-breaking within a major, removing one is a major bump. Only the
codes Phase 1 itself can emit are pinned here; later phases add theirs.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from goldmasters_contracts._base import ContractModel

__all__ = ["RETRYABLE_CODES", "ErrorCode", "ErrorPayload"]


class ErrorCode(StrEnum):
    """The closed, stable, machine-readable error-code vocabulary (D-23)."""

    CONTRACT_VALIDATION_FAILED = "CONTRACT_VALIDATION_FAILED"
    UNKNOWN_CONTRACT_MAJOR = "UNKNOWN_CONTRACT_MAJOR"
    CONFIG_INVALID = "CONFIG_INVALID"
    UNSUPPORTED_INSTRUMENT = "UNSUPPORTED_INSTRUMENT"
    UNSUPPORTED_TIMEFRAME = "UNSUPPORTED_TIMEFRAME"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    @property
    def retryable(self) -> bool:
        """Whether the same operation may meaningfully be retried.

        Phase 1 pins exactly one retryable code: ``INTERNAL_ERROR`` is transient
        and unexpected, while the other five are deterministic rejections that
        the same input fails again. Revisable by a minor bump (D-23).
        """
        return self in RETRYABLE_CODES


#: Exposed so later phases read the retryable set rather than re-deriving it.
RETRYABLE_CODES: frozenset[ErrorCode] = frozenset({ErrorCode.INTERNAL_ERROR})


class ErrorPayload(ContractModel):
    """Schema.md §10, field for field: the sanitized C-09 error object."""

    code: ErrorCode
    message: str
    retryable: bool
    correlation_id: str
    details: list[dict[str, str]] | None

    @model_validator(mode="before")
    @classmethod
    def _retryable_comes_from_the_code(cls, data: object) -> object:
        """Force ``retryable`` to the value the code declares (Schema.md §10).

        A supplied value must still be a boolean — a non-boolean makes the
        document malformed — but it never decides the outcome. An absent
        ``code``, a code outside the enum, or a non-string code is left to the
        field validator so the error names the offending field.
        """
        if not isinstance(data, dict):
            return data
        code = data.get("code")
        if not isinstance(code, str):  # ErrorCode members are str too
            return data
        try:
            declared = ErrorCode(code).retryable
        except ValueError:
            return data
        # An absent value is injected; a boolean is overridden; a non-boolean is
        # passed through so the strict field validator reports it.
        if not isinstance(data.get("retryable", declared), bool):
            return data
        return {**data, "retryable": declared}
