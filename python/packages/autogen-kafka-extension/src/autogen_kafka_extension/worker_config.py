from aiokafka.helpers import create_ssl_context
from confluent_kafka.admin import AdminClient
from kstreams.backends import Kafka
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism

class WorkerConfig:

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

    def __init__(self,
                 title: str,
                 request_topic: str,
                 response_topic: str,
                 registry_topic: str,
                 bootstrap_servers: list[str],
                 num_partitions: int | None = 3,
                 replication_factor: int | None = 1,
                 security_protocol: SecurityProtocol | None = None,
                 security_mechanism: SaslMechanism | None = None,
                 sasl_plain_username: str | None = None,
                 sasl_plain_password: str | None = None,
                 group_id: str | None = None,
                 client_id: str | None = None) -> None:
        self._title = title
        self._request_topic: str = request_topic
        self._response_topic: str = response_topic
        self._sasl_plain_username: str | None = sasl_plain_username
        self._sasl_plain_password: str | None = sasl_plain_password
        self._security_protocol: SecurityProtocol | None = security_protocol
        self._security_mechanism: SaslMechanism | None = security_mechanism
        self._bootstrap_servers: list[str] = bootstrap_servers
        self._group_id: str | None = group_id
        self._client_id: str | None = client_id
        self._registry_topic: str = registry_topic
        self._num_partitions: int = num_partitions
        self._replication_factor = replication_factor

    @property
    def client_id(self) -> str:
        """
        The Kafka client ID.
        If not set, a default client ID will be used.
        """
        return self._client_id

    @property
    def group_id(self) -> str | None:
        """
        The Kafka consumer group ID.
        If not set, the worker will not join any consumer group.
        """
        return self._group_id

    @property
    def request_topic(self) -> str | None:
        """
        The Kafka topic to consume messages from.
        If not set, the worker will not consume any messages.
        """
        return self._request_topic

    @property
    def response_topic(self) -> str | None:
        """
        The Kafka topic to produce messages to.
        If not set, the worker will not produce any messages.
        """
        return self._response_topic

    @property
    def registry_topic(self) -> str | None:
        """
        The Kafka topic for registry messages.
        If not set, the worker will not handle registry messages.
        """
        return self._registry_topic

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
    def title(self) -> str:
        return self._title

    def get_kafka_backend(self) -> Kafka:
        return Kafka(
            bootstrap_servers=self._bootstrap_servers,
            security_protocol= self._security_protocol,
            sasl_mechanism=self._security_mechanism,
            sasl_plain_username=self._sasl_plain_username,
            sasl_plain_password=self._sasl_plain_password,
            ssl_context=create_ssl_context(),
        )

    def get_admin_client(self) -> AdminClient:
        """
        Get the Kafka admin client.
        This method returns a Kafka instance configured with the worker's settings.
        """
        config : dict[str, str] = {
            'bootstrap.servers': ','.join(self._bootstrap_servers),
            'client.id': self._client_id or 'autogen-kafka-extension',
            'group.id': self._group_id or 'autogen-kafka-extension-group',
            'security.protocol': self._security_protocol.value if self._security_protocol else SecurityProtocol.PLAINTEXT.value,
            'sasl.mechanism': self._security_mechanism.value if self._security_mechanism else SaslMechanism.PLAIN.value,
            'sasl.username': self._sasl_plain_username or None,
            'sasl.password': self._sasl_plain_password or None,
        }

        return AdminClient(conf=config)
