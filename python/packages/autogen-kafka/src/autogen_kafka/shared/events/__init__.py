"""Events subpackage for autogen-kafka-extension.

This package provides event classes and serialization utilities for
Kafka message handling.
"""

from .event_base import EventBase
from .cloudevent_schema import (
    get_cloudevent_json_schema_compact, 
    cloud_event_to_dict, 
    cloud_event_from_dict
)
from .events_serdes import EventSerializer, EventDeserializer
from .memory_event import MemoryEvent
from .request_event import RequestEvent
from .response_event import ResponseEvent
from .subscription_event import SubscriptionEvent
from .registration_event import RegistrationEvent

__all__ = [
    "EventBase",
    "get_cloudevent_json_schema_compact",
    "cloud_event_to_dict",
    "cloud_event_from_dict",
    "EventSerializer",
    "EventDeserializer",
    "MemoryEvent", 
    "RequestEvent",
    "ResponseEvent",
    "SubscriptionEvent",
    "RegistrationEvent",
]
