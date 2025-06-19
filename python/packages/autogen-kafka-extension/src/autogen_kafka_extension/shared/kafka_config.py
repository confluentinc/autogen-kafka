from aiokafka.helpers import create_ssl_context
from confluent_kafka.admin import AdminClient
from kstreams.backends import Kafka
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism

class KafkaConfig:
    @property
    def num_partitions(self) -> int:
        """
        The number of partitions for the request topic.
        Default is 3.
        """
        return self._num_partitions

    @property
    def replication_factor(self) -> int:
        """
        The replication factor for the request topic.
        Default is 1.
        """
        return self._replication_factor

    @property
    def is_compacted(self) -> bool:
        """
        Indicates whether the topic is compacted.
        Default is False.
        """
        return self._is_compacted

    @property
    def auto_offset_reset(self) -> str:
        """
        The auto offset reset policy for the consumer.
        Default is 'latest'.
        """
        return self._auto_offset_reset

    def __init__(self,
                 name: str,
                 group_id: str,
                 client_id: str,
                 bootstrap_servers: list[str],
                 num_partitions: int = 3,
                 replication_factor: int = 1,
                 is_compacted: bool = False,
                 auto_offset_reset: str = 'latest',
                 security_protocol: SecurityProtocol | None = None,
                 security_mechanism: SaslMechanism | None = None,
                 sasl_plain_username: str | None = None,
                 sasl_plain_password: str | None = None) -> None:
        """
        Initialize the WorkerConfig with all necessary Kafka configuration parameters.

        Args:
            name (str): A descriptive name for this worker configuration.
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
        self._name = name
        self._sasl_plain_username: str | None = sasl_plain_username
        self._sasl_plain_password: str | None = sasl_plain_password
        self._security_protocol: SecurityProtocol | None = security_protocol
        self._security_mechanism: SaslMechanism | None = security_mechanism
        self._bootstrap_servers: list[str] = bootstrap_servers
        self._group_id: str = group_id
        self._client_id: str = client_id
        self._num_partitions: int = num_partitions
        self._replication_factor = replication_factor
        self._is_compacted = is_compacted
        self._auto_offset_reset: str = auto_offset_reset

    @property
    def client_id(self) -> str:
        """
        The Kafka client ID.
        If not set, a default client ID will be used.
        """
        return self._client_id

    @property
    def group_id(self) -> str:
        """
        The Kafka consumer group ID.
        If not set, the worker will not join any consumer group.
        """
        return self._group_id

    @property
    def sasl_plain_username(self) -> str | None:
        """
        The username for SASL PLAIN authentication.
        If not set, SASL PLAIN authentication will not be used.
        """
        return self._sasl_plain_username

    @property
    def sasl_plain_password(self) -> str | None:
        """
        The password for SASL PLAIN authentication.
        If not set, SASL PLAIN authentication will not be used.
        """
        return self._sasl_plain_password

    @property
    def name(self) -> str:
        """
        The descriptive name for this worker configuration.

        Returns:
            str: The name string assigned to this configuration.
        """
        return self._name

    def get_kafka_backend(self) -> Kafka:
        """
        Create and configure a Kafka backend instance for streaming operations.

        This method creates a kstreams Kafka backend configured with all the
        security and connection settings from this configuration. The backend
        can be used for creating producers, consumers, and streaming applications.

        Returns:
            Kafka: A configured Kafka backend instance ready for streaming operations.

        Note:
            The SSL context is automatically created if security protocols require it.
        """
        return Kafka(
            bootstrap_servers=self._bootstrap_servers,
            security_protocol=self._security_protocol or SecurityProtocol.PLAINTEXT,
            sasl_mechanism=self._security_mechanism or SaslMechanism.PLAIN,
            sasl_plain_username=self._sasl_plain_username,
            sasl_plain_password=self._sasl_plain_password,
            ssl_context=create_ssl_context(),
        )

    def get_admin_client(self) -> AdminClient:
        """
        Create and configure a Kafka AdminClient for administrative operations.

        This method creates a confluent-kafka AdminClient configured with the
        worker's connection and security settings. The admin client can be used
        for topic management, cluster metadata operations, and other administrative
        tasks.

        Returns:
            AdminClient: A configured Kafka AdminClient instance for administrative operations.

        Note:
            - Default values are provided for client.id and group.id if not configured
            - Security settings default to PLAINTEXT and PLAIN if not specified
            - None values for SASL credentials are handled appropriately
        """
        config: dict[str, str] = {
            'bootstrap.servers': ','.join(self._bootstrap_servers),
            'client.id': self._client_id or 'autogen-kafka-extension',
            'group.id': self._group_id or 'autogen-kafka-extension-group',
            'security.protocol': self._security_protocol.value if self._security_protocol else SecurityProtocol.PLAINTEXT.value,
            'sasl.mechanism': self._security_mechanism.value if self._security_mechanism else SaslMechanism.PLAIN.value,
        }
        
        # Only add SASL credentials if they are provided
        if self._sasl_plain_username:
            config['sasl.username'] = self._sasl_plain_username
        if self._sasl_plain_password:
            config['sasl.password'] = self._sasl_plain_password

        return AdminClient(conf=config)