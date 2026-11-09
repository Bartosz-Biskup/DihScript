from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


limiter = Limiter(key_func=get_remote_address)


def set_up_rate_limiting(app: FastAPI):
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.state.limiter = limiter
