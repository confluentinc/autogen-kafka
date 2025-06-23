import asyncio
import json
import logging
import uuid
from asyncio import Future
from typing import Any, Mapping, Dict

from autogen_core import MessageContext, BaseAgent, JSON_DATA_CONTENT_TYPE
from autogen_core._serialization import SerializationRegistry, try_get_known_serializers_for_type
from kstreams import ConsumerRecord, Stream, Send

from autogen_kafka_extension.agent.event.agent_event import AgentEvent
from autogen_kafka_extension.agent.event.agent_event_serdes import AgentEventSerializer, AgentEventDeserializer
from autogen_kafka_extension.agent.kafka_agent_config import KafkaAgentConfig
from autogen_kafka_extension.shared.background_task_manager import BackgroundTaskManager
from autogen_kafka_extension.shared.streaming_worker_base import StreamingWorkerBase


class KafkaStreamingAgent(BaseAgent, StreamingWorkerBase[KafkaAgentConfig]):

    def __init__(self,
                 config: KafkaAgentConfig,
                 description: str) -> None:
        BaseAgent.__init__(self, description)
        StreamingWorkerBase.__init__(self,
                                     config=config,
                                     topic=config.request_topic,
                                     deserializer=AgentEventDeserializer())
        self._serialization_registry = SerializationRegistry()
        self._pending_requests: Dict[str, Future[Any]] = {}
        self._pending_requests_lock = asyncio.Lock()
        self._next_request_id = 0
        self._background_task_manager = BackgroundTaskManager()

    async def on_message_impl(self, message: Any, ctx: MessageContext) -> Any:
        type_name = self._serialization_registry.type_name(message)
        if not self._serialization_registry.is_registered(type_name = type_name,
                                                          data_content_type = JSON_DATA_CONTENT_TYPE):
            self._serialization_registry.add_serializer(try_get_known_serializers_for_type(message))

        serialized = self._serialization_registry.serialize(message=message,
                                                            type_name=type_name,
                                                            data_content_type=JSON_DATA_CONTENT_TYPE)

        # Create a future to await the response
        future = asyncio.get_event_loop().create_future()
        request_id = await self._get_new_request_id()
        self._pending_requests[request_id] = future

        event = AgentEvent(id = request_id, message=serialized, message_type=type_name)

        # Send the event to the Kafka topic
        self._background_task_manager.add_task(
            StreamingWorkerBase.send_message(self,
                                             topic=self._config.request_topic,
                                             message=event,
                                             recipient=ctx.sender.__str__(),
                                             serializer=AgentEventSerializer())
        )
        return await future

    async def save_state(self) -> Mapping[str, Any]:
        pass

    async def load_state(self, state: Mapping[str, Any]) -> None:
        pass

    async def close(self) -> None:
        logging.info("Closing KafkaStreamingAgent and releasing resources.")
        await self._background_task_manager.wait_for_completion()

    async def _get_new_request_id(self) -> str:
        """Generate a new unique request ID for correlating requests and responses.

        Returns:
            A unique string identifier for the request
        """
        async with self._pending_requests_lock:
            self._next_request_id += 1
            return str(self._next_request_id)

    async def _handle_event(self, record: ConsumerRecord, stream: Stream, send: Send) -> None:
        if record.value is None:
            logging.error("Received None value in KafkaStreamingAgent event")
            return
        if not isinstance(record.value, AgentEvent):
            logging.error(f"Received invalid message type: {type(record.value)}")
            return

        event: AgentEvent = record.value
        request_id = event.id
        if request_id not in self._pending_requests:
            logging.error(f"Received response for unknown request ID: {request_id}")
            return

        future = self._pending_requests.pop(request_id, None)
        if future is None:
            logging.error(f"Future for request ID {request_id} not found")
            return

        try:
            # For now, we support only JSON serialization
            message : Dict[str, Any] = json.loads(event.message)
            future.set_result(message)
        except Exception as e:
            logging.error(f"Error deserializing message for request ID {request_id}: {e}")
            future.set_exception(e)
            return
