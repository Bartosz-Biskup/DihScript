from pydantic import BaseModel
from typing import Literal
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


limiter = Limiter(key_func=get_remote_address)


class RateLimiterConfig(BaseModel):
    limit: int
    period: Literal["minute", "hour", "day"]

    def get_limiter_config_in_slowapi_format(self) -> str:
        return str(self.limit) + "/" + self.period


CONFIG: dict[str, RateLimiterConfig] = {
    "subscriber_router": RateLimiterConfig(limit=3, period="minute"),
    "fix_router": RateLimiterConfig(limit=20, period="hour")
}


def set_up_rate_limiting(app: FastAPI):
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.state.limiter = limiter
