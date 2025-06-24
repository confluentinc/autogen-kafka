import logging
from typing import Optional, Dict

from aiokafka import ConsumerRecord

from azure.core.messaging import CloudEvent
from confluent_kafka.schema_registry._sync.serde import BaseDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField
from kstreams import types, Stream
from kstreams.middleware import BaseMiddleware
from kstreams.serializers import Serializer

from autogen_kafka_extension.shared.events.event_base import EventBase
from autogen_kafka_extension.shared.schema_registry_service import SchemaRegistryService
from autogen_kafka_extension.shared.events.cloudevent_schema import get_cloudevent_json_schema_compact, \
    cloud_event_to_dict, cloud_event_from_dict


class EventDeserializer(BaseMiddleware):
    """
    Middleware for deserializing Kafka ConsumerRecord values into Message objects.
    """

    def __init__(
        self,
        *,
        schema_registry_service: SchemaRegistryService,
        target_type: type,
        next_call: types.NextMiddlewareCall,
        send: types.Send,
        stream: "Stream",
    ) -> None:
        super().__init__(next_call = next_call,
                         send = send,
                         stream = stream)
        self._target_type = target_type

        if issubclass(target_type, EventBase):
            schema_str = target_type.__schema__()
            from_dict = self._dict_to_event_base
        elif target_type is CloudEvent:
            schema_str = get_cloudevent_json_schema_compact()
            from_dict = self._dict_to_cloud_event
        else:
            logging.error(f"Unsupported payload type: {type(target_type)}")
            raise ValueError(f"Unsupported payload type: {type(target_type)}")

        self._inner_deserializer : BaseDeserializer = schema_registry_service.create_json_deserializer(
            schema_str=schema_str,
            from_dict=from_dict
        )

    async def __call__(self, cr: ConsumerRecord):
        # If the record has a value, decode it from bytes and parse as JSON
        if cr.value is not None:
            try:
                cr.value = self._inner_deserializer(
                    cr.value,
                    ctx=SerializationContext(topic=cr.topic, field=MessageField.VALUE)
                )

            except ValueError as e:
                logging.error(f"Failed to deserialize value {cr.value}: {e}")
                raise ValueError(f"Failed to deserialize value: {e}")

        # Pass the modified ConsumerRecord to the next middleware or handler
        return await self.next_call(cr)

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
        Convert a dictionary to an object of the specified type.

        Args:
            data: The dictionary to convert.
            ctx: Serialization context (unused here).

        Returns:
            Any: The converted object.
        """
        try:
            return cloud_event_from_dict(data)
        except Exception as e:
            logging.error(f"Failed to deserialize CloudEvent from data {data}: {e}")
            raise ValueError(f"Failed to deserialize CloudEvent: {e}") from e

def _event_base_to_dict(obj : EventBase, ctx: SerializationContext) -> Dict:
    return obj.__dict__()

def _cloud_event_to_dict(obj : CloudEvent, ctx: SerializationContext) -> Dict:
    return cloud_event_to_dict(obj)

class EventSerializer(Serializer):
    """
    Serializer for Message objects and generic payloads.
    Converts Message instances or other payloads to JSON-encoded bytes for Kafka.
    """

    def __init__(self,
                 topic: str,
                 source_type: type,
                 schema_registry_service: Optional[SchemaRegistryService] ):

        if issubclass(source_type, EventBase):
            schema_str = source_type.__schema__()
            to_dict = _event_base_to_dict
        elif source_type is CloudEvent:
            schema_str = get_cloudevent_json_schema_compact()
            to_dict = _cloud_event_to_dict
        else:
            logging.error(f"Unsupported payload type: {type(source_type)}")
            raise ValueError(f"Unsupported payload type: {type(source_type)}")

        self._schema_registry_service = schema_registry_service
        self._topic = topic
        self._schema_str = schema_str
        self._inner_serializer = schema_registry_service.create_json_serializer(
            schema_str=schema_str,
            to_dict=to_dict)

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
        try:
            return self._inner_serializer(
                obj=payload,
                ctx=SerializationContext(topic=self._topic, field=MessageField.VALUE)
            )
        except Exception as e:
            logging.error(f"Failed to serialize payload {payload}: {e}")
            raise ValueError(f"Failed to serialize payload: {e}") from e
