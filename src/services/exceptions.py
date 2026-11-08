class ServiceException(Exception):
    """Base for every failure raised by the services layer.

    Subclasses of this class are mapped to HTTP responses by the API
    exception handlers, so nothing that reaches the API layer should leak
    as a raw 500.
    """


class NotFoundException(ServiceException):
    """A requested entity does not exist."""


class AlreadyExistsException(ServiceException):
    """An entity with the same identity already exists."""


class LLMException(ServiceException):
    """Base for everything that goes wrong around the language model.

    Raised only by the LLM layer. Layers above it should treat this as
    "the fix could not be produced" without caring about the reason.
    """


class ModelProviderException(LLMException):
    """The model provider could not be reached, or rejected the request.

    Covers network failures, bad API keys, rate limits, and provider-side
    errors — anything that happens *before* we can judge the reply itself.
    """


class EmptyPromptException(LLMException):
    """The prompt handed to the model was empty or only whitespace.

    This is a caller mistake, never a provider problem, which is why it is
    mapped to 400 while the rest of the LLM failures map to 502.
    """


class InvalidModelResponseException(LLMException):
    """The model replied, but the reply could not be parsed into the
    expected response shape (after all retry attempts were exhausted).
    """
