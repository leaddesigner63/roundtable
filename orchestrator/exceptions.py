class OrchestrationError(Exception):
    pass


class SessionNotFoundError(OrchestrationError):
    pass


class ProviderExecutionError(OrchestrationError):
    pass
