from enum import Enum
from typing import Dict, Any, Union, Type, Protocol
from abc import ABC, abstractmethod

from autogen_core import Subscription, TypeSubscription, TypePrefixSubscription


class SubscriptionEvtOp(Enum):
    ADDED = "added"
    REMOVED = "removed"


class SubscriptionSerializer(Protocol):
    """Protocol for subscription serialization handlers."""
    
    @staticmethod
    def can_handle(subscription: Union[Subscription, str]) -> bool:
        """Check if this handler can serialize the given subscription."""
        ...
    
    @staticmethod
    def to_dict(subscription: Union[Subscription, str]) -> Dict[str, Any]:
        """Convert subscription to dictionary."""
        ...
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Union[Subscription, str]:
        """Create subscription from dictionary."""
        ...


class TypeSubscriptionSerializer:
    """Handles TypeSubscription serialization."""
    
    @staticmethod
    def can_handle(subscription: Union[Subscription, str]) -> bool:
        return isinstance(subscription, TypeSubscription)
    
    @staticmethod
    def to_dict(subscription: TypeSubscription) -> Dict[str, Any]:
        return {
            "type": "TypeSubscription",
            "subscription": {
                "topic_type": subscription.topic_type,
                "agent_type": subscription.agent_type,
                "id": subscription.id
            }
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> TypeSubscription:
        sub_data = data["subscription"]
        return TypeSubscription(
            topic_type=sub_data["topic_type"],
            agent_type=sub_data["agent_type"],
            id=sub_data["id"],
        )


class TypePrefixSubscriptionSerializer:
    """Handles TypePrefixSubscription serialization."""
    
    @staticmethod
    def can_handle(subscription: Union[Subscription, str]) -> bool:
        return isinstance(subscription, TypePrefixSubscription)
    
    @staticmethod
    def to_dict(subscription: TypePrefixSubscription) -> Dict[str, Any]:
        return {
            "type": "TypePrefixSubscription",
            "subscription": {
                "topic_type_prefix": subscription.topic_type_prefix,
                "agent_type": subscription.agent_type,
                "id": subscription.id
            }
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> TypePrefixSubscription:
        sub_data = data["subscription"]
        return TypePrefixSubscription(
            topic_type_prefix=sub_data["topic_type_prefix"],
            agent_type=sub_data["agent_type"],
            id=sub_data["id"]
        )


class StringSubscriptionSerializer:
    """Handles string subscription serialization."""
    
    @staticmethod
    def can_handle(subscription: Union[Subscription, str]) -> bool:
        return isinstance(subscription, str)
    
    @staticmethod
    def to_dict(subscription: str) -> Dict[str, Any]:
        return {
            "type": "StringSubscription",
            "subscription": subscription
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> str:
        return data["subscription"]


class SubscriptionEvt:
    """
    SubscriptionEvt represents an event related to a subscription.
    It handles serialization/deserialization of different subscription types
    and tracks the operation performed on the subscription.
    """
    
    # Registry of serialization handlers
    _serializers = [
        TypeSubscriptionSerializer(),
        TypePrefixSubscriptionSerializer(),
        StringSubscriptionSerializer(),
    ]
    
    # Mapping from type names to deserializers for faster lookup
    _deserializers = {
        "TypeSubscription": TypeSubscriptionSerializer,
        "TypePrefixSubscription": TypePrefixSubscriptionSerializer,
        "StringSubscription": StringSubscriptionSerializer,
    }

    def __init__(self, subscription: Union[Subscription, str], operation: SubscriptionEvtOp = SubscriptionEvtOp.ADDED):
        """
        Initialize a SubscriptionEvt.

        Args:
            subscription: The subscription object or string
            operation: The operation performed on the subscription
        """
        self._subscription = subscription
        self._operation = operation

    @property
    def subscription(self) -> Union[Subscription, str]:
        """Get the subscription."""
        return self._subscription

    @property
    def operation(self) -> SubscriptionEvtOp:
        """Get the operation."""
        return self._operation

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the SubscriptionEvt to a dictionary representation.

        Returns:
            Dict[str, Any]: A dictionary representation of the SubscriptionEvt

        Raises:
            ValueError: If the subscription type is not supported
        """
        # Find the appropriate serializer
        for serializer in self._serializers:
            if serializer.can_handle(self._subscription):
                result = serializer.to_dict(self._subscription)
                result["operation"] = self._operation.value
                return result
        
        raise ValueError(f"Unsupported subscription type: {type(self._subscription)}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubscriptionEvt':
        """
        Create a SubscriptionEvt from a dictionary representation.

        Args:
            data: A dictionary representation of the SubscriptionEvt

        Returns:
            SubscriptionEvt: An instance of SubscriptionEvt

        Raises:
            ValueError: If the subscription type is not supported or data is invalid
            KeyError: If required keys are missing from the data
        """
        try:
            operation = SubscriptionEvtOp(data["operation"])
            subscription_type = data["type"]
            
            if subscription_type not in cls._deserializers:
                raise ValueError(f"Unsupported subscription type: {subscription_type}")
            
            deserializer = cls._deserializers[subscription_type]
            subscription = deserializer.from_dict(data)
            
            return cls(subscription=subscription, operation=operation)
            
        except KeyError as e:
            raise KeyError(f"Missing required key in subscription data: {e}")
        except ValueError as e:
            if "is not a valid SubscriptionEvtOp" in str(e):
                raise ValueError(f"Invalid operation value: {data.get('operation')}")
            raise