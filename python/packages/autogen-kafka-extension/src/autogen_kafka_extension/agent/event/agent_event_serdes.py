import logging

from autogen_kafka_extension.agent.event.agent_event import AgentEvent
from typing import Optional, Dict
from aiokafka import ConsumerRecord

import json

from kstreams.middleware.middleware import MiddlewareProtocol
from kstreams.serializers import Serializer

class AgentEventDeserializer(MiddlewareProtocol):
    """
    Middleware for deserializing Kafka ConsumerRecord values into Message objects.
    """
    async def __call__(self, cr: ConsumerRecord):
        try:
                # If the event type is Message, create a Message instance
            values = json.loads(cr.value)
            cr.value = AgentEvent.from_dict(values)
        except ValueError as e:
            logging.error(f"Failed to deserialize value {cr.value}: {e}")
            raise ValueError(f"Failed to deserialize value: {e}")

        # Pass the modified ConsumerRecord to the next middleware or handler
        return await self.next_call(cr)

class AgentEventSerializer(Serializer):
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
        if not isinstance(payload, AgentEvent):
            raise RuntimeError(f"Unsupported payload type: {type(payload)}")

        try:
            values = payload.to_dict()

            json_value = json.dumps(values)
        except TypeError as e:
            logging.error(f"Failed to serialize payload {payload} to JSON: {e}")
            raise RuntimeError(f"Failed to serialize payload to JSON: {e}")

        # Encode JSON string to bytes for Kafka transport
        return json_value.encode()