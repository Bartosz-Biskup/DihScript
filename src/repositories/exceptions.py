class RepositoryException(Exception):
    ...


class NotFoundException(RepositoryException):
    ...


class AlreadyExistsException(RepositoryException):
    ...


class ModelValidationException(RepositoryException):
    ...
