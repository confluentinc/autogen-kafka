import logging
from typing import Optional, Dict

from aiokafka import ConsumerRecord
from cloudevents.pydantic import CloudEvent
from kstreams import middleware

import json

from kstreams.serializers import Serializer

from autogen_kafka_extension.services.constants import EVENT_TYPE_ATTR
from autogen_kafka_extension.events.request_event import RequestEvent
from autogen_kafka_extension.events.registration_event import RegistrationEvent
from autogen_kafka_extension.events.response_event import ResponseEvent
from autogen_kafka_extension.events.subscription_event import SubscriptionEvent


class EventDeserializer(middleware.BaseMiddleware):
    """
    Middleware for deserializing Kafka ConsumerRecord values into Message objects.
    """

    async def __call__(self, cr: ConsumerRecord):
        # If the record has a value, decode it from bytes and parse as JSON
        if cr.value is not None:
            # Convert the cr.headers to a dictionary suitable for CloudEvent
            evt_type : str | None = None
            headers: Dict[str, str | None] = {}
            for key, v in cr.headers:
                if v is None:
                    headers[key] = None

                v_str = v.decode() if isinstance(v, bytes) else v
                if key == EVENT_TYPE_ATTR:
                    evt_type = v_str
                elif v_str.startswith("str:"):
                    headers[key] = v_str[4:]
                elif v_str.startswith("json:"):
                    try:
                        headers[key] = json.loads(v_str[5:])
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to decode JSON header {key}: {e}")
                        raise ValueError(f"Invalid JSON in header {key}: {v_str[6:]}")
                elif v_str == "None":
                    headers[key] = None
                else:
                    headers[key] = v_str

            if evt_type is None:
                logging.error(f"missing event type attribute {EVENT_TYPE_ATTR} in headers")
                raise ValueError(f"Missing required header: {EVENT_TYPE_ATTR}")

            try:
                # Wrap the parsed data in a Message object
                if evt_type == RequestEvent.__name__:
                    # If the event type is Message, create a Message instance
                    values = json.loads(cr.value)
                    cr.value = RequestEvent.from_dict(values)
                elif evt_type == RegistrationEvent.__name__:
                    # If the event type is RegistrationMessage, create a RegistrationMessage instance
                    values = json.loads(cr.value)
                    cr.value = RegistrationEvent.from_dict(values)
                elif evt_type == SubscriptionEvent.__name__:
                    # If the event type is SubscriptionEvt, create a SubscriptionEvt instance
                    values = json.loads(cr.value)
                    cr.value = SubscriptionEvent.from_dict(values)
                elif evt_type == ResponseEvent.__name__:
                    # If the event type is SubscriptionEvt, create a SubscriptionEvt instance
                    values = json.loads(cr.value)
                    cr.value = ResponseEvent.from_dict(values)
                elif evt_type == CloudEvent.__name__:
                    cr.value = CloudEvent(attributes=headers, data=cr.value)
            except ValueError as e:
                logging.error(f"Failed to deserialize value {cr.value} with headers {headers}: {e}")
                raise ValueError(f"Failed to deserialize value: {e}")

        # Pass the modified ConsumerRecord to the next middleware or handler
        return await self.next_call(cr)


class EventSerializer(Serializer):
    """
    Serializer for Message objects and generic payloads.
    Converts Message instances or other payloads to JSON-encoded bytes for Kafka.
    """

    async def serialize(
        self,
        payload: any,
        headers: Optional[Dict[str, str]] = None,
        serializer_kwargs: Optional[Dict] = None
    ) -> bytes:
        """
        Serialize the payload to bytes.

        Args:
            payload: The object to serialize. If it's a Message, use its dict representation.
            headers: Optional headers for serialization (unused here).
            serializer_kwargs: Optional extra arguments for serialization (unused here).

        Returns:
            bytes: The JSON-encoded payload as bytes.
        """
        if isinstance(payload, CloudEvent):
            attributes = payload.get_attributes()
            result = payload.data

            for key, value in attributes.items():
                if value is None:
                    headers[key] = "None"
                elif isinstance(value, str):
                    headers[key] = "str:" + value
                elif isinstance(value, dict):
                    # Convert dict values to JSON strings
                    headers[key] = 'json:' + json.dumps(value)
                elif isinstance(value, bytes) and result is None:
                    result = value
                else:
                    logging.warning(f"Non-string header value for {key}: {value}")
            headers[EVENT_TYPE_ATTR] = CloudEvent.__name__

            return result
        elif (not isinstance(payload, RequestEvent) and
              not isinstance(payload, RegistrationEvent) and
              not isinstance(payload, SubscriptionEvent) and
              not isinstance(payload, ResponseEvent)):
            raise RuntimeError(f"Unsupported payload type: {type(payload)}")

        try:
            values = payload.to_dict()
            headers[EVENT_TYPE_ATTR] = payload.__class__.__name__

            json_value = json.dumps(values)
        except TypeError as e:
            logging.error(f"Failed to serialize payload {payload} to JSON: {e}")
            raise RuntimeError(f"Failed to serialize payload to JSON: {e}")

        # Encode JSON string to bytes for Kafka transport
        return json_value.encode()