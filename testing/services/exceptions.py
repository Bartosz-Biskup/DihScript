class TestingServiceException(Exception):
    ...


class GroupNotFoundException(TestingServiceException):
    ...


class GroupNotFinishedException(TestingServiceException):
    ...
