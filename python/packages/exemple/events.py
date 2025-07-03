from dataclasses import dataclass

from autogen_kafka_extension.agent.kafka_message_type import KafkaMessageType


@dataclass
class SentimentRequest(KafkaMessageType):
    text: str

    @staticmethod
    def __schema__() -> str:
        return """
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "text": {
                    "type": "string"
                }
            },
            "required": ["text"]
        }
        """

@dataclass
class SentimentResponse(KafkaMessageType):
    sentiment: str

    @staticmethod
    def __schema__() -> str:
        return """
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "sentiment": {
                    "type": "string"
                }
            },
            "required": ["sentiment"]
        }
        """
