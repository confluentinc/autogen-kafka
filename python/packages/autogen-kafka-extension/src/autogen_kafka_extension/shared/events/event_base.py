from abc import abstractmethod, ABC


class EventBase(ABC):
    """
    Base class for all events in the Kafka extension.
    This class can be extended to create specific event types.
    """

    @abstractmethod
    def __dict__(self):
        """
        Returns a dictionary representation of the event.
        This method should be implemented by subclasses to provide
        a complete representation of the event's data.
        """
        raise NotImplementedError("Subclasses must implement __dict__ method.")

    @classmethod
    def __from_dict__(cls, data: dict):
        """
        Creates an instance of the event from a dictionary.
        This method should be implemented by subclasses to handle
        the conversion from dictionary to event instance.
        """
        raise NotImplementedError("Subclasses must implement from_dict method.")

    @classmethod
    def __schema__(cls) -> str:
        """
        Returns the schema of the event.
        This method should be implemented by subclasses to provide
        a complete schema of the event's data.
        """
        raise NotImplementedError("Subclasses must implement __schema__ method.")

