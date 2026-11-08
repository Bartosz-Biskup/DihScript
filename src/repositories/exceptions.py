class RepositoryException(Exception):
    """Base for every failure raised by the repositories layer."""


class NotFoundException(RepositoryException):
    """A requested row does not exist in the database."""


class AlreadyExistsException(RepositoryException):
    """A row with the same identity already exists in the database."""


class ModelValidationException(RepositoryException):
    """A domain model was constructed with values that break its rules."""
