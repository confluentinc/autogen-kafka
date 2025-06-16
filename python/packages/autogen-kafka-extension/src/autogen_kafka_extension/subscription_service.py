import logging
from typing import List, Optional

from autogen_core import Subscription, AgentId, TopicId
from autogen_core._runtime_impl_helpers import SubscriptionManager
from autogen_core._serialization import SerializationRegistry
from autogen_core._telemetry import TraceHelper
from kstreams import ConsumerRecord, Stream, Send
from opentelemetry.trace import TracerProvider

from autogen_kafka_extension.streaming_service import StreamingService
from autogen_kafka_extension.events.message_serdes import EventSerializer
from autogen_kafka_extension.events.subscription_event import SubscriptionEvent, SubscriptionEvtOp
from autogen_kafka_extension.streaming_worker_base import StreamingWorkerBase
from autogen_kafka_extension.worker_config import WorkerConfig

logger = logging.getLogger(__name__)


class SubscriptionService(StreamingWorkerBase):
    """
    Service for managing agent subscriptions with distributed coordination via Kafka.
    
    Maintains two subscription managers:
    - local_subscriptions: Subscriptions managed by this service instance
    - global_subscriptions: All subscriptions across all service instances
    """

    @property
    def local_subscriptions(self) -> SubscriptionManager:
        """Get the local subscription manager for this service instance."""
        return self._local_subscriptions

    @property
    def global_subscriptions(self) -> SubscriptionManager:
        """Get the global subscription manager tracking all service instances."""
        return self._global_subscriptions

    def __init__(self,
                 config: WorkerConfig,
                 streaming_service: Optional[StreamingService] = None,
                 trace_helper: TraceHelper | None = None,
                 tracer_provider: TracerProvider | None = None,
                 serialization_registry: SerializationRegistry = SerializationRegistry()) -> None:
        super().__init__(config = config,
                         topic=config.subscription_topic,
                         trace_helper=trace_helper,
                         tracer_provider=tracer_provider,
                         streaming_service=streaming_service,
                         serialization_registry=serialization_registry)
        self._local_subscriptions = SubscriptionManager()
        self._global_subscriptions = SubscriptionManager()

    async def get_local_recipients(self, topic_id: TopicId) -> List[AgentId]:
        """Get recipients subscribed to a topic on this service instance."""
        return await self._local_subscriptions.get_subscribed_recipients(topic_id)

    async def get_global_recipients(self, topic_id: TopicId) -> List[AgentId]:
        """Get all recipients subscribed to a topic across all service instances."""
        return await self._global_subscriptions.get_subscribed_recipients(topic_id)

    def get_all_subscriptions(self) -> List[Subscription]:
        """Get all subscriptions tracked globally."""
        return self._global_subscriptions._subscriptions

    def is_started(self) -> bool:
        """Check if the service is currently started."""
        return self._is_started

    async def add_subscription(self, subscription: Subscription) -> None:
        """Add a new subscription and broadcast to other service instances."""
        self._validate_subscription(subscription)
        
        try:
            await self._broadcast_subscription_event(
                operation=SubscriptionEvtOp.ADDED,
                subscription=subscription
            )
            await self._local_subscriptions.add_subscription(subscription)
            logger.info(f"Added subscription: {subscription}")
        except Exception as e:
            logger.error(f"Failed to add subscription {subscription}: {e}")
            raise

    async def remove_subscription(self, subscription_id: str) -> None:
        """Remove a subscription and broadcast to other service instances."""
        if not subscription_id:
            raise ValueError("Subscription ID cannot be empty")
        
        try:
            await self._broadcast_subscription_event(
                operation=SubscriptionEvtOp.REMOVED,
                subscription=subscription_id
            )
            await self._local_subscriptions.remove_subscription(subscription_id)
            logger.info(f"Removed subscription: {subscription_id}")
        except Exception as e:
            logger.error(f"Failed to remove subscription {subscription_id}: {e}")
            raise

    async def unsubscribe_all(self) -> None:
        """Remove all local subscriptions and broadcast removals."""
        subscriptions = list(self._local_subscriptions.subscriptions)
        
        for subscription in subscriptions:
            try:
                await self.remove_subscription(subscription.id)
            except Exception as e:
                logger.error(f"Failed to remove subscription {subscription.id} during unsubscribe_all: {e}")
                # Continue with other subscriptions
        
        logger.info("Completed unsubscribe_all operation")

    def _validate_subscription(self, subscription: Subscription) -> None:
        """Validate subscription before adding."""
        if not subscription:
            raise ValueError("Subscription cannot be None")
        if not subscription.id:
            raise ValueError("Subscription ID cannot be empty")

    async def _broadcast_subscription_event(
        self,
        operation: SubscriptionEvtOp,
        subscription: Subscription | str,
    ) -> None:
        """Broadcast subscription event to other service instances."""
        event = SubscriptionEvent(subscription=subscription, operation=operation)

        await self._streaming_service.send(
            topic=self._config.subscription_topic,
            value=event,
            headers={},
            serializer=EventSerializer()
        )

    async def _handle_event(self, record: ConsumerRecord, stream: Stream, send: Send) -> None:
        """Process incoming subscription events from other service instances."""
        if not isinstance(record.value, SubscriptionEvent):
            logger.error(f"Received invalid subscription event type: {type(record.value)}")
            return

        event = record.value

        try:
            if event.operation == SubscriptionEvtOp.ADDED:
                await self._global_subscriptions.add_subscription(event.subscription)
                logger.debug(f"Processed subscription addition: {event.subscription}")
            elif event.operation == SubscriptionEvtOp.REMOVED:
                await self._global_subscriptions.remove_subscription(event.subscription)
                logger.debug(f"Processed subscription removal: {event.subscription}")
            else:
                logger.error(f"Unknown subscription operation: {event.operation}")
        except Exception as e:
            logger.error(f"Failed to process subscription event {event}: {e}")

    # Backward compatibility properties (deprecated)
    @property
    def subscription_manager(self) -> SubscriptionManager:
        """Deprecated: Use local_subscriptions instead."""
        logger.warning("subscription_manager is deprecated, use local_subscriptions")
        return self._local_subscriptions

    @property
    def all_subscription_manager(self) -> SubscriptionManager:
        """Deprecated: Use global_subscriptions instead."""
        logger.warning("all_subscription_manager is deprecated, use global_subscriptions")
        return self._global_subscriptions

    async def get_subscribed_recipients(self, topic_id: TopicId) -> List[AgentId]:
        """Deprecated: Use get_local_recipients instead."""
        logger.warning("get_subscribed_recipients is deprecated, use get_local_recipients")
        return await self.get_local_recipients(topic_id)

    async def get_all_subscribed_recipients(self, topic_id: TopicId) -> List[AgentId]:
        """Deprecated: Use get_global_recipients instead."""
        logger.warning("get_all_subscribed_recipients is deprecated, use get_global_recipients")
        return await self.get_global_recipients(topic_id)