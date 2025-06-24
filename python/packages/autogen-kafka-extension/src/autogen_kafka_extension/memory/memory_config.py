from kstreams.backends.kafka import SecurityProtocol, SaslMechanism

from autogen_kafka_extension.shared.kafka_config import KafkaConfig
from autogen_kafka_extension.shared.schema_registry_service import SchemaRegistryConfig


class MemoryConfig(KafkaConfig):
    """
    Configuration class for memory management in the Kafka extension.
    This class is used to set and retrieve memory-related configurations.
    """
    def __init__(self,
                 name: str,
                 group_id: str,
                 client_id: str,
                 bootstrap_servers: list[str],
                 schema_registry_config: SchemaRegistryConfig,
                 *,
                 replication_factor: int = 1,
                 memory_topic: str = "memory",
                 security_protocol: SecurityProtocol | None = None,
                 security_mechanism: SaslMechanism | None = None,
                 sasl_plain_username: str | None = None,
                 sasl_plain_password: str | None = None) -> None:
        super().__init__(
            name=name,
            group_id=group_id,
            client_id=client_id,
            bootstrap_servers=bootstrap_servers,
            schema_registry_config=schema_registry_config,
            num_partitions=1,
            replication_factor=replication_factor,
            security_protocol=security_protocol,
            security_mechanism=security_mechanism,
            sasl_plain_username=sasl_plain_username,
            sasl_plain_password=sasl_plain_password,
            auto_offset_reset="earliest",  # Start consuming from the earliest message to rebuild memory
        )
        self._memory_topic = memory_topic

    @property
    def memory_topic(self) -> str:
        """
        The Kafka topic used for memory management.
        This topic is where memory-related messages will be published and consumed.
        """
        return self._memory_topic