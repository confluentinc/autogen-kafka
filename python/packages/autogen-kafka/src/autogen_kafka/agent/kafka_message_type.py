from abc import ABC


class KafkaMessageType(ABC):

    @staticmethod
    def __schema__() -> str:
        raise NotImplementedError("__schema__ not implemented for KafkaMessageType.")