from typing import Annotated

from fastapi import APIRouter, Depends

from repositories.models import Subscriber
from services.subscriber_service import SubscriberCreate, SubscriberService

from .dependencies import get_subscriber_service

subscriber_router = APIRouter(prefix="/subscriber", tags=["subscriber"])


@subscriber_router.post("", response_model=Subscriber, status_code=201)
def register_subscriber(
    payload: SubscriberCreate,
    subscriber_service: Annotated[SubscriberService, Depends(get_subscriber_service)],
) -> Subscriber:
    return subscriber_service.register_subscriber(payload.name, payload.email)
