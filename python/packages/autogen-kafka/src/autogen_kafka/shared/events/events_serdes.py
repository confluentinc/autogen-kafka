import logging
from typing import Optional, Dict, Any

from azure.core.messaging import CloudEvent
from confluent_kafka import Message
from confluent_kafka.schema_registry._sync.serde import BaseDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField

from .event_base import EventBase
from .cloudevent_schema import get_cloudevent_json_schema_compact, \
    cloud_event_to_dict, cloud_event_from_dict
from ...config import KafkaUtils


class EventDeserializer:
    """
    Middleware for deserializing Kafka ConsumerRecord values into Message objects.
    """

    def __init__(
        self,
        kafka_utils: KafkaUtils,
        target_type: type,
        *,
        schema_str: str | None = None,
    ) -> None:
        self._target_type = target_type

        if issubclass(target_type, EventBase):
            schema_str = schema_str or target_type.__schema__()
            from_dict = self._dict_to_event_base
        elif target_type is CloudEvent:
            schema_str = schema_str or get_cloudevent_json_schema_compact()
            from_dict = self._dict_to_cloud_event
        else:
            logging.error(f"Unsupported payload type: {target_type}")
            raise ValueError(f"Unsupported payload type: {target_type}")

        self._inner_deserializer: BaseDeserializer = kafka_utils.create_json_deserializer(
            schema_str=schema_str,
            from_dict=from_dict
        )

    def deserialize(self, msg: Message) -> Any:
        # If the record has a value, decode it from bytes and parse as JSON
        if msg.value() is not None:
            try:
                return self._inner_deserializer(
                    msg.value(),
                    ctx=SerializationContext(topic=msg.topic(), field=MessageField.VALUE)
                )
            except ValueError as e:
                logging.error(f"Failed to deserialize value: {e}")
                raise ValueError(f"Failed to deserialize value: {e}") from e
            except Exception as e:
                logging.error(f"Unexpected error deserializing value: {e}")
                raise ValueError(f"Unexpected error deserializing value: {e}") from e

    def _dict_to_event_base(self, data: Dict, ctx: SerializationContext) -> EventBase:
        """
        Convert a dictionary to an EventBase object.

        Args:
            data: The dictionary to convert.
            ctx: Serialization context (unused here).

        Returns:
            EventBase: The converted EventBase object.
        """
        return self._target_type.__from_dict__(data)

    def _dict_to_cloud_event(self, data: Dict, ctx: SerializationContext) -> CloudEvent:
        """
        Convert a dictionary to a CloudEvent object.

        Args:
            data: The dictionary to convert.
            ctx: Serialization context (unused here).

        Returns:
            CloudEvent: The converted CloudEvent object.
        """
        try:
            return cloud_event_from_dict(data)
        except Exception as e:
            logging.error(f"Failed to deserialize CloudEvent from data {data}: {e}")
            raise ValueError(f"Failed to deserialize CloudEvent: {e}") from e


def _event_base_to_dict(obj: EventBase, ctx: SerializationContext) -> Dict:
    """Convert EventBase object to dictionary."""
    return obj.__dict__()


def _cloud_event_to_dict(obj: CloudEvent, ctx: SerializationContext) -> Dict:
    """Convert CloudEvent object to dictionary."""
    return cloud_event_to_dict(obj)


class EventSerializer:
    """
    Serializer for Message objects and generic payloads.
    Converts Message instances or other payloads to JSON-encoded bytes for Kafka.
    """

    def __init__(self,
                 topic: str,
                 source_type: type,
                 kafka_utils: KafkaUtils,
                 *,
                 schema_str: Optional[str] = None):

        if issubclass(source_type, EventBase):
            schema_str = schema_str or source_type.__schema__()
            to_dict = _event_base_to_dict
        elif source_type is CloudEvent:
            schema_str = schema_str or get_cloudevent_json_schema_compact()
            to_dict = _cloud_event_to_dict
        else:
            logging.error(f"Unsupported payload type: {source_type}")
            raise ValueError(f"Unsupported payload type: {source_type}")

        self._kafka_utils = kafka_utils
        self._topic = topic
        self._schema_str = schema_str
        self._inner_serializer = kafka_utils.create_json_serializer(
            schema_str=schema_str,
            to_dict=to_dict)

    async def serialize(
        self,
        payload: Any,
        headers: Optional[Dict[str, str]] = None
    ) -> bytes:
        """
        Serialize the payload to bytes.

        Args:
            payload: The object to serialize. If it's a Message, use its dict representation.
            headers: Optional headers for serialization (unused here).

        Returns:
            bytes: The JSON-encoded payload as bytes.
        
        Raises:
            ValueError: If serialization fails.
        """
        try:
            result = self._inner_serializer(
                obj=payload,
                ctx=SerializationContext(topic=self._topic, field=MessageField.VALUE)
            )
            
            if result is None:
                raise ValueError("Serializer returned None")
                
            return result
        except Exception as e:
            logging.error(f"Failed to serialize payload {payload}: {e}")
            raise ValueError(f"Failed to serialize payload: {e}") from e
