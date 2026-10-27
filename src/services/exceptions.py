class ServiceException(Exception):
    ...


class NotFoundException(ServiceException):
    ...


class AlreadyExistsException(ServiceException):
    ...


class LLMServiceException(ServiceException):
    ...


class EmptyPromptException(LLMServiceException):
    ...


class EmptyResponseException(LLMServiceException):
    ...


class InvalidModelOutputException(ServiceException):
    ...
