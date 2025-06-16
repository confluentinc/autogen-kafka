import asyncio
import logging
import uuid
from asyncio import Future
from typing import Dict, Callable, Awaitable, TypeVar, Any, Sequence, Mapping, Type

from autogen_core import (
    AgentRuntime, Agent, AgentId, Subscription, TopicId, CancellationToken,
    AgentType, AgentMetadata, MessageSerializer,
)
from cloudevents.pydantic import CloudEvent
from kstreams import ConsumerRecord, Stream, Send
from opentelemetry.trace import TracerProvider

from autogen_kafka_extension.messaging_client import MessagingClient
from autogen_kafka_extension.agent_registry import AgentRegistry
from autogen_kafka_extension.agent_manager import AgentManager
from autogen_kafka_extension.events.request_event import RequestEvent
from autogen_kafka_extension.streaming_worker_base import StreamingWorkerBase
from autogen_kafka_extension.message_processor import MessageProcessor
from autogen_kafka_extension.subscription_service import SubscriptionService
from autogen_kafka_extension.worker_config import WorkerConfig

T = TypeVar("T", bound=Agent)
logger = logging.getLogger(__name__)


class KafkaWorkerAgentRuntime(StreamingWorkerBase, AgentRuntime):
    """
    A Kafka worker agent runtime that processes messages from Kafka topics.
    Extends AgentRuntime to provide Kafka-specific functionality for consuming
    and processing messages from configured Kafka topics.
    """

    def __init__(
        self,
        config: WorkerConfig,
        tracer_provider: TracerProvider | None = None
    ) -> None:
        """Initialize a new KafkaWorkerAgentRuntime instance."""
        AgentRuntime.__init__(self)
        StreamingWorkerBase.__init__(self,
                               config = config,
                               name= "KafkaWorkerAgentRuntime",
                               topic=config.request_topic,
                               tracer_provider=tracer_provider)

        # Kafka components
        self._agent_registry : AgentRegistry = AgentRegistry(config=config,
                                                             streaming=self._streaming_service)
        self._subscription_svc: SubscriptionService = SubscriptionService(config=self._config,
                                                                          streaming_service=self._streaming_service)
        self._agent_client : MessagingClient = MessagingClient(config=self._config,
                                                       streaming_service=self._streaming_service,
                                                       serialization_registry=self._serialization_registry,
                                                       trace_helper=self._trace_helper)

        # Component managers
        self._agent_manager = AgentManager(self)
        self._message_processor = MessageProcessor(
            self._agent_manager,
            self._serialization_registry,
            self._subscription_svc,
            self._trace_helper,
            self._config
        )

        # Request/response handling
        self._pending_requests: Dict[str, Future[Any]] = {}
        self._pending_requests_lock = asyncio.Lock()
        self._next_request_id = 0


    async def stop(self) -> None:
        """Stop the Kafka stream processing engine and wait for background tasks to finish."""
        if not self.is_started:
            return

        logger.info("Stopping subscription service and Kafka stream engine...")
        await self._subscription_svc.unsubscribe_all()

        await super().stop()

    async def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
        message_id: str | None = None
    ) -> Any:
        return await self._agent_client.send_message(
            message=message,
            recipient=recipient,
            sender=sender,
            cancellation_token=cancellation_token,
            message_id=message_id
        )

    async def publish_message(
        self,
        message: Any,
        topic_id: TopicId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
        message_id: str | None = None,
    ) -> None:
        await self._agent_client.publish_message(
            message=message,
            topic_id=topic_id,
            sender=sender,
            cancellation_token=cancellation_token,
            message_id=message_id
        )

    async def remove_subscription(self, id: str) -> None:
        """Remove a subscription by its ID."""
        await self._subscription_svc.remove_subscription(id)

    async def add_subscription(self, subscription: Subscription) -> None:
        """Add a new subscription."""
        await self._subscription_svc.add_subscription(subscription)

    async def register_factory(
        self,
        type: str | AgentType,
        agent_factory: Callable[[], T | Awaitable[T]],
        *,
        expected_class: type[T] | None = None
    ) -> AgentType:
        """Register a factory for creating agents of a given type."""
        return await self._agent_manager.register_factory(
            type, agent_factory, self._agent_registry, expected_class=expected_class
        )

    async def register_agent_instance(
        self,
        agent_instance: Agent,
        agent_id: AgentId,
    ) -> AgentId:
        """Register a specific agent instance with a given ID."""
        return await self._agent_manager.register_instance(agent_instance, agent_id)

    async def save_state(self) -> Mapping[str, Any]:
        """Save the runtime state (not implemented)."""
        raise NotImplementedError("Saving state is not yet implemented.")

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load the runtime state (not implemented)."""
        raise NotImplementedError("Loading state is not yet implemented.")

    async def agent_metadata(self, agent: AgentId) -> AgentMetadata:
        """Get agent metadata (not implemented)."""
        raise NotImplementedError("Agent metadata is not yet implemented.")

    async def agent_save_state(self, agent: AgentId) -> Mapping[str, Any]:
        """Save agent state (not implemented)."""
        raise NotImplementedError("Agent save_state is not yet implemented.")

    async def agent_load_state(self, agent: AgentId, state: Mapping[str, Any]) -> None:
        """Load agent state (not implemented)."""
        raise NotImplementedError("Agent load_state is not yet implemented.")

    async def try_get_underlying_agent_instance(self, id: AgentId, type: Type[T] = Agent) -> T:  # type: ignore[assignment]
        return await self._agent_manager.try_get_underlying_agent_instance(id, type)

    async def _get_new_request_id(self) -> str:
        """Generate a new unique request ID for correlating requests and responses."""
        async with self._pending_requests_lock:
            self._next_request_id += 1
            return str(self._next_request_id)

    async def _handle_event(self, cr: ConsumerRecord, stream: Stream, send: Send) -> None:
        """Callback for processing incoming Kafka records."""
        if isinstance(cr.value, RequestEvent):
            self._background_task_manager.add_task(
                self._message_processor.process_request(cr.value, send)
            )
            return

        if isinstance(cr.value, CloudEvent):
            # Process as a CloudEvent
            await self._message_processor.process_event(cr.value)
            return

        logger.error(f"Received unknown event type: {cr.value}. Expected 'CloudEvent' or 'Message'.")

    def add_message_serializer(self, serializer: MessageSerializer[Any] | Sequence[MessageSerializer[Any]]) -> None:
        self._serialization_registry.add_serializer(serializer)