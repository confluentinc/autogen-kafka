from dataclasses import dataclass
from typing import Any


@dataclass
class StreamingServiceConfig:
    name: str
    topic: str
    group_id: str
    client_id: str
    deserialized_type: type
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    auto_create_topics: bool = True

    def get_consumer_config(self) -> dict[str, Any]:
        """
        Get the Kafka consumer configuration dictionary.

        This method generates a complete consumer configuration dictionary suitable
        for use with Kafka consumers. It automatically appends unique UUIDs to the
        client_id and group_id to ensure uniqueness across multiple consumer instances.

        Returns:
            dict[str, Any]: A dictionary containing the consumer configuration with:
                - client_id: Original client_id with appended UUID for uniqueness
                - group_id: Original group_id with appended UUID for uniqueness
                - auto_offset_reset: Strategy for offset reset behavior
                - enable_auto_commit: Auto-commit configuration
        """
        return {
            "client_id": f"{self.client_id}",
            "group_id": f"{self.group_id}",
            "auto_offset_reset": self.auto_offset_reset,
            "enable_auto_commit": self.enable_auto_commit
        }
