from kstreams.backends.kafka import SecurityProtocol, SaslMechanism

from autogen_kafka_extension.shared.kafka_config import KafkaConfig


class KafkaAgentConfig(KafkaConfig):

    def __init__(self,
                 name: str,
                 group_id: str,
                 client_id: str,
                 bootstrap_servers: list[str],
                 request_topic: str = "agent_request",
                 response_topic: str = "agent_response",
                 num_partitions: int = 3,
                 replication_factor: int = 1,
                 auto_offset_reset: str = 'latest',
                 security_protocol: SecurityProtocol | None = None,
                 security_mechanism: SaslMechanism | None = None,
                 sasl_plain_username: str | None = None,
                 sasl_plain_password: str | None = None) -> None:
        super().__init__(
            name=name,
            group_id=group_id,
            client_id=client_id,
            bootstrap_servers=bootstrap_servers,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            is_compacted=False,
            auto_offset_reset=auto_offset_reset,
            security_protocol=security_protocol,
            security_mechanism=security_mechanism,
            sasl_plain_username=sasl_plain_username,
            sasl_plain_password=sasl_plain_password
        )
        self._request_topic: str = request_topic
        self._response_topic: str = response_topic

    @property
    def request_topic(self) -> str:
        """
        The Kafka topic used for sending requests to the agent.
        """
        return self._request_topic

    @property
    def response_topic(self) -> str:
        """
        The Kafka topic used for receiving responses from the agent.
        """
        return self._response_topic