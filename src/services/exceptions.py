class ServiceException(Exception):
    ...


class LLMServiceException(ServiceException):
    ...


class EmptyPromptException(LLMServiceException):
    ...


class EmptyResponseException(LLMServiceException):
    ...


class InvalidModelOutputException(ServiceException):
    ...
