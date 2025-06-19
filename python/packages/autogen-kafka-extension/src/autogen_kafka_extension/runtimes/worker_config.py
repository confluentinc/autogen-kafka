from kstreams.backends.kafka import SecurityProtocol, SaslMechanism
from autogen_kafka_extension.shared.kafka_config import KafkaConfig

class WorkerConfig(KafkaConfig):
    """
    Configuration class for Kafka workers in the autogen-kafka-extension.
    
    This class encapsulates all the configuration parameters needed to set up
    and run Kafka workers, including connection settings, authentication,
    topic configurations, and administrative settings.
    
    The configuration supports both secure and non-secure Kafka connections,
    with optional SASL authentication mechanisms and SSL context creation.
    
    Attributes:
        All configuration values are accessible through properties that provide
        read-only access to the internal configuration state.
    """

    def __init__(self,
                 name: str,
                 request_topic: str,
                 subscription_topic: str,
                 registry_topic: str,
                 response_topic: str,
                 group_id: str,
                 client_id: str,
                 bootstrap_servers: list[str],
                 num_partitions: int = 3,
                 replication_factor: int = 1,
                 security_protocol: SecurityProtocol | None = None,
                 security_mechanism: SaslMechanism | None = None,
                 sasl_plain_username: str | None = None,
                 sasl_plain_password: str | None = None) -> None:
        """
        Initialize the WorkerConfig with all necessary Kafka configuration parameters.
        
        Args:
            name (str): A descriptive name for this worker configuration.
            request_topic (str): The Kafka topic name for consuming incoming requests.
            subscription_topic (str): The Kafka topic name for publishing subscription messages.
            registry_topic (str): The Kafka topic name for agent registry operations.
            response_topic (str): The Kafka topic name for publishing response messages.
            group_id (str): The Kafka consumer group ID for coordinating message consumption.
            client_id (str): A unique identifier for this Kafka client instance.
            bootstrap_servers (list[str]): List of Kafka broker addresses in 'host:port' format.
            num_partitions (int, optional): Number of partitions for topics. Defaults to 3.
            replication_factor (int, optional): Replication factor for topics. Defaults to 1.
            security_protocol (SecurityProtocol | None, optional): Security protocol for Kafka connection.
                Defaults to None (PLAINTEXT).
            security_mechanism (SaslMechanism | None, optional): SASL mechanism for authentication.
                Defaults to None.
            sasl_plain_username (str | None, optional): Username for SASL PLAIN authentication.
                Required if security_mechanism is PLAIN. Defaults to None.
            sasl_plain_password (str | None, optional): Password for SASL PLAIN authentication.
                Required if security_mechanism is PLAIN. Defaults to None.
        
        Raises:
            ValueError: If required authentication parameters are missing when security is enabled.
        """
        super().__init__(
            name = name,
            group_id = group_id,
            client_id = client_id,
            bootstrap_servers = bootstrap_servers,
            num_partitions = num_partitions,
            replication_factor = replication_factor,
            security_protocol = security_protocol,
            security_mechanism = security_mechanism,
            sasl_plain_username = sasl_plain_username,
            sasl_plain_password = sasl_plain_password
            )
        self._request_topic: str = request_topic
        self._subscription: str = subscription_topic
        self._registry_topic: str = registry_topic
        self._response_topic: str = response_topic

    @property
    def request_topic(self) -> str:
        """
        The Kafka topic to consume messages from.
        If not set, the worker will not consume any messages.
        """
        return self._request_topic

    @property
    def subscription_topic(self) -> str:
        """
        The Kafka topic to produce messages to.
        If not set, the worker will not produce any messages.
        """
        return self._subscription

    @property
    def registry_topic(self) -> str:
        """
        The Kafka topic for registry messages.
        If not set, the worker will not handle registry messages.
        """
        return self._registry_topic

    @property
    def response_topic(self) -> str:
        """
        The Kafka topic to produce responses to.
        If not set, the worker will not produce responses.
        """
        return self._response_topic
