from typing import Optional

from .topic_admin_service import TopicAdminService
from .schema_registry_service import SchemaRegistryService
from ..schema_registry_config import SchemaRegistryConfig


class KafkaUtils(SchemaRegistryService, TopicAdminService):

    def __init__(
        self,
        bootstrap_servers: list[str],
        schema_registry_config: SchemaRegistryConfig,
        *,
        num_partitions: int = 3,
        replication_factor: int = 1,
        is_compacted: bool = False,
        security_protocol: str | None = None,
        security_mechanism: str | None = None,
        sasl_plain_username: str | None = None,
        sasl_plain_password: str | None = None):

        SchemaRegistryService.__init__(self, schema_registry_config)
        TopicAdminService.__init__(self, bootstrap_servers=bootstrap_servers,
                                    security_protocol=security_protocol,
                                    security_mechanism=security_mechanism,
                                    sasl_plain_password=sasl_plain_password,
                                    sasl_plain_username=sasl_plain_username,
                                    num_partitions=num_partitions,
                                    replication_factor=replication_factor,
                                    is_compacted=is_compacted)