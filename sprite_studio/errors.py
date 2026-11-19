"""Shared exceptions with stable CLI exit codes."""


class StudioError(Exception):
    """Base class for expected, user-facing failures."""

    exit_code = 1


class UsageError(StudioError):
    exit_code = 2


class ValidationError(StudioError):
    exit_code = 1


class ProviderError(StudioError):
    exit_code = 3


class ApprovalRequired(ProviderError):
    exit_code = 4


class BudgetExceeded(ProviderError):
    exit_code = 4


class UnsupportedIntegration(ProviderError):
    exit_code = 3
