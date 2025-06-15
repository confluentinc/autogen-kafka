import logging
from typing import List

from autogen_core import Subscription, AgentId, TopicId
from autogen_core._runtime_impl_helpers import SubscriptionManager
from kstreams import ConsumerRecord

from autogen_kafka_extension.streaming_service import StreamingService
from autogen_kafka_extension.events.message_serdes import EventSerializer
from autogen_kafka_extension.events.subscription_evt import SubscriptionEvt, SubscriptionEvtOp
from autogen_kafka_extension.worker_config import WorkerConfig

logger = logging.getLogger(__name__)

class SubscriptionService:

    @property
    def subscription_manager(self) -> SubscriptionManager:
        """Get the subscription manager for handling subscriptions."""
        return self._subscription

    @property
    def all_subscription_manager(self) -> SubscriptionManager:
        """Get the subscription manager for all subscriptions."""
        return self._all_subscription

    def __init__(self, config: WorkerConfig, streaming: StreamingService | None = None) -> None:
        self._subscription = SubscriptionManager()
        self._all_subscription = SubscriptionManager()
        self._started: bool = False
        self._startable: bool = streaming is None
        self._config = config
        self._streaming = streaming if streaming else StreamingService(config)

        # Set up the registration stream
        self._setup_registration_stream()

    async def get_subscribed_recipients(self, topic_id: TopicId) -> List[AgentId]:
        """Get the list of subscriptions for a given topic ID."""
        return await self._subscription.get_subscribed_recipients(topic_id)

    async def get_all_subscribed_recipients(self, topic_id: TopicId) -> List[AgentId]:
        """Get the list of subscriptions for a given topic ID."""
        return await self._all_subscription.get_subscribed_recipients(topic_id)

    def get_all_subscriptions(self) -> List[Subscription]:
        """Get all subscriptions managed by this service."""
        return self._all_subscription._subscriptions

    def _setup_registration_stream(self) -> None:
        """Set up the Kafka stream for agent registration messages."""
        self._streaming.create_and_add_stream(
            name=f"{self._config.title}_sub",
            topics=[self._config.subscription_topic],
            group_id=f"{self._config.group_id}_sub",
            client_id=f"{self._config.client_id}_sub",
            func=self._on_record
        )

    async def start(self) -> None:
        """Start the subscription service and its streaming component."""
        if not self._startable:
            raise RuntimeError("SubscriptionService cannot be started with a provided streaming service.")
        if self._started:
            raise RuntimeError("SubscriptionService is already started.")

        await self._streaming.start()
        self._started = True
        logger.info("SubscriptionService started.")

    async def stop(self) -> None:
        """Stop the subscription service and its streaming component."""
        if not self._startable:
            raise RuntimeError("SubscriptionService cannot be stopped with a provided streaming service.")
        if not self._started:
            raise RuntimeError("SubscriptionService is not started.")

        await self._streaming.stop()
        self._started = False
        logger.info("SubscriptionService stopped.")

    async def unsubscribe_all(self) -> None:
        subscriptions = self._subscription.subscriptions
        for subscription in subscriptions:
            await self.remove_subscription(subscription.id)


    async def add_subscription(self, subscription: Subscription) -> None:
        try:
            # Broadcast registration to other workers
            await self._send_message(
                evt_type=SubscriptionEvtOp.ADDED,
                subscription=subscription
            )

            await self._subscription.add_subscription(subscription)
            logger.info(f"Added subscription {subscription}")
        except Exception as e:
            # Rollback local registration on failure
            logger.error(f"Failed to add subscription {subscription}: {e}")
            raise

    async def remove_subscription(self, subscription_id: str) -> None:
        try:
            # Broadcast removal to other workers
            await self._send_message(
                evt_type=SubscriptionEvtOp.REMOVED,
                subscription=subscription_id
            )

            await self._subscription.remove_subscription(subscription_id)
            logger.info(f"Removed subscription {subscription_id}")
        except Exception as e:
            # Rollback local registration on failure
            logger.error(f"Failed to remove subscription {subscription_id}: {e}")
            raise

    async def _send_message(
            self,
            evt_type: SubscriptionEvtOp,
            subscription: Subscription | str,
    ) -> None:
        message = SubscriptionEvt(subscription=subscription, operation=evt_type)

        await self._streaming.send(
            topic=self._config.subscription_topic,
            value=message,
            headers={},
            serializer=EventSerializer()
        )

    async def _on_record(self, cr: ConsumerRecord) -> None:
        if not isinstance(cr.value, SubscriptionEvt):
            logger.error(f"Received invalid message type: {type(cr.value)}")
            return

        message = cr.value

        try:
            if message.operation == SubscriptionEvtOp.ADDED:
                await self._all_subscription.add_subscription(message.subscription)
            elif message.operation == SubscriptionEvtOp.REMOVED:
                await self._all_subscription.remove_subscription(message.subscription)
            else:
                logger.error(f"Unknown subscription operation: {message.operation}")
                return
        except Exception as e:
            logger.error(f"Failed to process subscription event: {e}")
            return