import logging
from typing import List, Optional

from autogen_core import Subscription, AgentId, TopicId
from autogen_core._runtime_impl_helpers import SubscriptionManager
from autogen_core._serialization import SerializationRegistry
from autogen_core._telemetry import TraceHelper
from kstreams import ConsumerRecord, Stream, Send
from opentelemetry.trace import TracerProvider

from autogen_kafka_extension.services.streaming_service import StreamingService
from autogen_kafka_extension.events.message_serdes import EventSerializer
from autogen_kafka_extension.events.subscription_event import SubscriptionEvent, SubscriptionEvtOp
from autogen_kafka_extension.services.streaming_worker_base import StreamingWorkerBase
from autogen_kafka_extension.worker_config import WorkerConfig

logger = logging.getLogger(__name__)


class SubscriptionService(StreamingWorkerBase):
    """
    Service for managing agent subscriptions with distributed coordination via Kafka.
    
    The SubscriptionService provides centralized management of agent subscriptions across
    a distributed system using Kafka for coordination. It maintains both local subscriptions
    (managed by this service instance) and global subscriptions (all subscriptions across
    all service instances).
    
    Key Features:
    - Distributed subscription management via Kafka topics
    - Local and global subscription tracking
    - Automatic broadcasting of subscription changes
    - Event-driven coordination between service instances
    - Built-in validation and error handling
    
    The service operates by:
    1. Managing local subscriptions for agents on this instance
    2. Broadcasting subscription changes to other service instances
    3. Listening for subscription events from other instances
    4. Maintaining a global view of all subscriptions
    
    Attributes:
        _local_subscriptions (SubscriptionManager): Manages subscriptions for this service instance
        _global_subscriptions (SubscriptionManager): Tracks all subscriptions across all instances
    """

    @property
    def local_subscriptions(self) -> SubscriptionManager:
        """
        Get the local subscription manager for this service instance.
        
        Returns:
            SubscriptionManager: The subscription manager containing only subscriptions
                managed by this specific service instance.
        """
        return self._local_subscriptions

    @property
    def global_subscriptions(self) -> SubscriptionManager:
        """
        Get the global subscription manager tracking all service instances.
        
        Returns:
            SubscriptionManager: The subscription manager containing all subscriptions
                across all service instances in the distributed system.
        """
        return self._global_subscriptions

    def __init__(self,
                 config: WorkerConfig,
                 streaming_service: Optional[StreamingService] = None,
                 monitoring: Optional[TraceHelper] | Optional[TracerProvider] = None,
                 serialization_registry: SerializationRegistry = SerializationRegistry()) -> None:
        """
        Initialize the SubscriptionService.
        
        Args:
            config (WorkerConfig): Configuration for the worker including subscription topic settings
            streaming_service (Optional[StreamingService], optional): Service for Kafka streaming operations.
                If None, a default service will be created. Defaults to None.
            monitoring (Optional[TraceHelper] | Optional[TracerProvider], optional): Monitoring and tracing
                provider for observability. Defaults to None.
            serialization_registry (SerializationRegistry, optional): Registry for message serialization.
                Defaults to SerializationRegistry().
        """
        super().__init__(config = config,
                         topic=config.subscription_topic,
                         monitoring=monitoring,
                         streaming_service=streaming_service,
                         serialization_registry=serialization_registry)
        self._local_subscriptions = SubscriptionManager()
        self._global_subscriptions = SubscriptionManager()

    async def get_local_recipients(self, topic_id: TopicId) -> List[AgentId]:
        """
        Get recipients subscribed to a topic on this service instance.
        
        Args:
            topic_id (TopicId): The topic identifier to find subscribers for
            
        Returns:
            List[AgentId]: List of agent IDs that are subscribed to the topic
                on this specific service instance
        """
        return await self._local_subscriptions.get_subscribed_recipients(topic_id)

    async def get_global_recipients(self, topic_id: TopicId) -> List[AgentId]:
        """
        Get all recipients subscribed to a topic across all service instances.
        
        Args:
            topic_id (TopicId): The topic identifier to find subscribers for
            
        Returns:
            List[AgentId]: List of agent IDs that are subscribed to the topic
                across all service instances in the distributed system
        """
        return await self._global_subscriptions.get_subscribed_recipients(topic_id)

    def get_all_subscriptions(self) -> List[Subscription]:
        """
        Get all subscriptions tracked globally.
        
        Returns:
            List[Subscription]: List of all subscriptions across all service instances
                in the distributed system
        """
        return self._global_subscriptions._subscriptions

    async def add_subscription(self, subscription: Subscription) -> None:
        """
        Add a new subscription and broadcast to other service instances.
        
        This method validates the subscription, broadcasts the addition event to other
        service instances via Kafka, and adds it to the local subscription manager.
        
        Args:
            subscription (Subscription): The subscription to add, containing agent ID,
                topic ID, and other subscription details
                
        Raises:
            ValueError: If the subscription is invalid (None, empty ID, etc.)
            Exception: If broadcasting or local addition fails
        """
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
        """
        Remove a subscription and broadcast to other service instances.
        
        This method broadcasts the removal event to other service instances via Kafka
        and removes the subscription from the local subscription manager.
        
        Args:
            subscription_id (str): The unique identifier of the subscription to remove
            
        Raises:
            ValueError: If the subscription_id is empty or None
            Exception: If broadcasting or local removal fails
        """
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
        """
        Remove all local subscriptions and broadcast removals.
        
        This method iterates through all local subscriptions and removes each one,
        broadcasting the removal to other service instances. It continues processing
        even if individual removals fail, logging errors for failed removals.
        """
        subscriptions = list(self._local_subscriptions.subscriptions)
        
        for subscription in subscriptions:
            try:
                await self.remove_subscription(subscription.id)
            except Exception as e:
                logger.error(f"Failed to remove subscription {subscription.id} during unsubscribe_all: {e}")
                # Continue with other subscriptions
        
        logger.info("Completed unsubscribe_all operation")

    def _validate_subscription(self, subscription: Subscription) -> None:
        """
        Validate subscription before adding.
        
        Performs basic validation checks on a subscription to ensure it's valid
        before attempting to add it to the subscription manager.
        
        Args:
            subscription (Subscription): The subscription to validate
            
        Raises:
            ValueError: If the subscription is None or has an empty ID
        """
        if not subscription:
            raise ValueError("Subscription cannot be None")
        if not subscription.id:
            raise ValueError("Subscription ID cannot be empty")

    async def _broadcast_subscription_event(
        self,
        operation: SubscriptionEvtOp,
        subscription: Subscription | str,
    ) -> None:
        """
        Broadcast subscription event to other service instances.
        
        Creates a SubscriptionEvent and sends it to the subscription topic so that
        other service instances can be notified of subscription changes.
        
        Args:
            operation (SubscriptionEvtOp): The type of operation (ADDED or REMOVED)
            subscription (Subscription | str): The subscription object for additions,
                or subscription ID string for removals
        """
        event = SubscriptionEvent(subscription=subscription, operation=operation)

        await self._service_manager.service.send(
            topic=self._config.subscription_topic,
            value=event,
            headers={},
            serializer=EventSerializer()
        )

    async def _handle_event(self, record: ConsumerRecord, stream: Stream, send: Send) -> None:
        """
        Process incoming subscription events from other service instances.
        
        This method is called when subscription events are received from the Kafka topic.
        It processes the events and updates the global subscription manager accordingly.
        
        Args:
            record (ConsumerRecord): The Kafka consumer record containing the subscription event
            stream (Stream): The Kafka stream context
            send (Send): The Kafka send context for producing messages
        """
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

    async def get_subscribed_recipients(self, topic_id: TopicId) -> List[AgentId]:
        """
        Get recipients subscribed to a topic on this service instance.
        
        Note:
            This method is deprecated. Use get_local_recipients instead.
            
        Args:
            topic_id (TopicId): The topic identifier to find subscribers for
            
        Returns:
            List[AgentId]: List of agent IDs that are subscribed to the topic
                on this specific service instance
        """
        logger.warning("get_subscribed_recipients is deprecated, use get_local_recipients")
        return await self.get_local_recipients(topic_id)

    async def get_all_subscribed_recipients(self, topic_id: TopicId) -> List[AgentId]:
        """
        Get all recipients subscribed to a topic across all service instances.
        
        Note:
            This method is deprecated. Use get_global_recipients instead.
            
        Args:
            topic_id (TopicId): The topic identifier to find subscribers for
            
        Returns:
            List[AgentId]: List of agent IDs that are subscribed to the topic
                across all service instances in the distributed system
        """
        logger.warning("get_all_subscribed_recipients is deprecated, use get_global_recipients")
        return await self.get_global_recipients(topic_id)