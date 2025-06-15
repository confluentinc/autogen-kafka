from enum import Enum
from typing import Dict, Any

from autogen_core import Subscription, TypeSubscription, TypePrefixSubscription

class SubscriptionEvtOp(Enum):
    ADDED = "added"
    REMOVED = "removed"

class SubscriptionEvt:
    """
    SubscriptionEvt is a class that represents an event related to a subscription.
    It is used to handle events in the context of Kafka subscriptions.
    """

    @property
    def subscription(self) -> Subscription | str:
        return self._subscription

    @property
    def operation(self) -> SubscriptionEvtOp:
        return self._operation

    def __init__(self, subscription: Subscription | str, operation: SubscriptionEvtOp = SubscriptionEvtOp.ADDED):
        self._subscription = subscription
        self._operation = operation

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the SubscriptionEvt to a dictionary representation.

        Returns:
            dict: A dictionary representation of the SubscriptionEvt.
        """
        if isinstance(self._subscription, TypeSubscription):
            return {
                "type": "TypeSubscription",
                "subscription": {
                    "topic_type": self._subscription.topic_type,
                    "agent_type": self._subscription.agent_type,
                    "id": self._subscription.id
                },
                "operation": self._operation.value
            }

        if isinstance(self._subscription, TypePrefixSubscription):
            return {
                "type": "TypePrefixSubscription",
                "subscription": {
                    "topic_type_prefix": self._subscription.topic_type_prefix,
                    "agent_type": self._subscription.agent_type,
                    "id": self._subscription.id
                },
                "operation": self._operation.value
            }

        if isinstance(self._subscription, str):
            return {
                "type": "StringSubscription",
                "subscription": self._subscription,
                "operation": self._operation.value
            }

        raise Exception("Unsupported subscription type")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubscriptionEvt':
        """
        Creates a SubscriptionEvt from a dictionary representation.

        Args:
            data (dict): A dictionary representation of the SubscriptionEvt.

        Returns:
            SubscriptionEvt: An instance of SubscriptionEvt.
        """
        operation = SubscriptionEvtOp(data["operation"])
        if data["type"] == "TypeSubscription":
            subscription = TypeSubscription(
                topic_type=data["subscription"]["topic_type"],
                agent_type=data["subscription"]["agent_type"],
                id=data["subscription"]["id"],
            )
        elif data["type"] == "TypePrefixSubscription":
            subscription = TypePrefixSubscription(
                topic_type_prefix=data["subscription"]["topic_type_prefix"],
                agent_type=data["subscription"]["agent_type"],
                id=data["subscription"]["id"]
            )
        elif data["type"] == "StringSubscription":
            subscription = data["subscription"]
        else:
            raise Exception("Unsupported subscription type")

        return cls(subscription = subscription, operation=operation)