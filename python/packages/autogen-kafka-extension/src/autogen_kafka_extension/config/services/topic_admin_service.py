import logging
from typing import Any, Optional

from confluent_kafka import KafkaException, KafkaError
from confluent_kafka.admin import ClusterMetadata, AdminClient
from confluent_kafka.cimpl import NewTopic
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism

logger = logging.getLogger(__name__)

def _handle_topic_creation_result(futures: dict, topic_names: list[str]) -> None:
    """Handle the results of topic creation futures.

    This private method processes the Future objects returned by the Kafka admin
    clients create_topics operation. It waits for each future to complete and
    handles both successful creation and various error conditions. Topics that
    already exist are logged as debug messages, while other errors are logged
    as errors and re-raised.

    Args:
        futures: Dictionary mapping topic names to their creation Future objects
                returned by the admin clients create_topics method. Each Future
                represents the asynchronous topic creation operation.
        topic_names: List of topic names that were requested to be created.
                    Used to verify that all requested topics have corresponding
                    futures and for error reporting.

    Raises:
        Exception: If any topic name doesn't have a corresponding future
        KafkaException: If topic creation fails for reasons other than topic
                       already existing (e.g., insufficient permissions, invalid
                       topic configuration, broker connectivity issues)
        Exception: For any other unexpected errors during topic creation
    """
    for topic_name in topic_names:
        if topic_name not in futures:
            error_msg = f"Failed to create topic {topic_name}. No future returned."
            logger.error(error_msg)
            raise Exception(error_msg)

        try:
            futures[topic_name].result()
        except KafkaException as e:
            if e.args[0] == KafkaError.TOPIC_ALREADY_EXISTS:
                logger.debug(f"Topic {topic_name} already exists")
            else:
                logger.error(f"Failed to create topic {topic_name}: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to create topic {topic_name}: {e}")
            raise


class TopicAdminService:
    """Admin client for managing Kafka topics.
    
    This class provides a high-level interface for Kafka topic administration operations
    including creating single or multiple topics and listing existing topics. It handles
    the underlying Kafka admin client configuration and provides error handling for
    common scenarios like a topic already exists.
    
    The TopicAdmin uses the WorkerConfig to determine topic creation parameters such as
    the number of partitions and replication factor. It also handles Kafka connection
    settings through the admin client provided by the WorkerConfig.
    
    Typical usage:
        config = WorkerConfig(...)
        admin = TopicAdmin(config)
        admin.create_topic("my-topic")
        topics = admin.list_topics()
    
    Attributes:
        _config: The WorkerConfig instance containing Kafka settings
        _admin_client: The underlying Kafka admin client for operations
    """
    def __init__(self,
                 bootstrap_servers: list[str],
                 *,
                 num_partitions: int = 3,
                 replication_factor: int = 1,
                 is_compacted: bool = False,
                 security_protocol: Optional[SecurityProtocol] = None,
                 security_mechanism: Optional[SaslMechanism] = None,
                 sasl_plain_username: Optional[str] = None,
                 sasl_plain_password: Optional[str] = None,
                 ) -> None:
        """Initialize TopicAdmin with worker configuration.
        
        Sets up the admin client using the provided WorkerConfig which contains
        all necessary Kafka connection parameters, authentication settings, and
        topic creation defaults.
        
        Args:
            bootstrap_servers: List of Kafka broker addresses in 'host:port' format.
            num_partitions: Number of partitions for topics. Defaults to 3.
            replication_factor: Replication factor for topics. Defaults to 1.
            is_compacted: Whether topics should be compacted. Defaults to False.
            security_protocol: Security protocol for Kafka connection.
            security_mechanism: SASL mechanism for authentication.
            sasl_plain_username: Username for SASL PLAIN authentication.
            sasl_plain_password: Password for SASL PLAIN authentication.
        Raises:
            Exception: If the config fails to provide a valid admin client
        """
        self._is_compacted = is_compacted
        self._num_partitions = num_partitions
        self._admin_client = self._get_admin_client(
            bootstrap_servers=bootstrap_servers,
            security_protocol=security_protocol,
            security_mechanism=security_mechanism,
            sasl_plain_password=sasl_plain_password,
            sasl_plain_username=sasl_plain_username
        )

        future = self._admin_client.describe_cluster()
        cluster_info = future.result()

        if len(cluster_info.nodes) == 0:
            logger.error("No Kafka brokers found in cluster")
            raise Exception("No Kafka brokers found in cluster")

        self._num_partitions = num_partitions
        self._replication_factor = min(replication_factor, len(cluster_info.nodes))
        if self._replication_factor < replication_factor:
            logger.warning(
                f"Configured replication factor {replication_factor} exceeds available brokers "
                f"({len(cluster_info.nodes)}). Using {self._replication_factor} instead."
            )

    @staticmethod
    def _get_admin_client(bootstrap_servers: list[str],
                          *,
                          security_protocol: Optional[SecurityProtocol] = None,
                          security_mechanism: Optional[SaslMechanism] = None,
                          sasl_plain_username: Optional[str] = None,
                          sasl_plain_password: Optional[str] = None,
                          ) -> AdminClient:
        """Create and configure a Kafka AdminClient for administrative operations.

        This method creates a confluent-kafka AdminClient configured with the
        configuration's connection and security settings. The admin client can be
        used for topic management, cluster metadata operations, and other
        administrative tasks.

        Args:
            bootstrap_servers: List of Kafka broker addresses in 'host:port' format.
            security_protocol: Security protocol for Kafka connection.
            security_mechanism: SASL mechanism for authentication.
            sasl_plain_username: Username for SASL PLAIN authentication.
            sasl_plain_password: Password for SASL PLAIN authentication.
        Returns:
            A configured Kafka AdminClient instance for administrative operations.

        Note:
            - Default values are provided for client.id and group.id if not configured
            - Security settings default to PLAINTEXT and PLAIN if not specified
            - None values for SASL credentials are handled appropriately
        """
        config = {
            'bootstrap.servers': ','.join(bootstrap_servers),
            'client.id': 'autogen-kafka-extension',
            'group.id': 'autogen-kafka-extension-group',
            'security.protocol': (
                security_protocol.value
                if security_protocol
                else SecurityProtocol.PLAINTEXT.value
            ),
            'sasl.mechanism': (
                security_mechanism.value
                if security_mechanism
                else SaslMechanism.PLAIN.value
            ),
        }

        # Only add SASL credentials if they are provided
        if sasl_plain_username:
            config['sasl.username'] = sasl_plain_username
        if sasl_plain_password:
            config['sasl.password'] = sasl_plain_password

        return AdminClient(conf=config)

    def _create_new_topic(self, topic_name: str) -> NewTopic:
        """Create a NewTopic object with configured partitions and replication factor.
        
        This private method creates a NewTopic instance using the topic name provided
        and the partition count and replication factor from the WorkerConfig. The
        NewTopic object is used by the Kafka admin client for topic creation operations.
        
        Args:
            topic_name: The name of the Kafka topic to create. Must be a valid Kafka
                       topic name following Kafka naming conventions (alphanumeric
                       characters, dots, dashes, and underscores).
            
        Returns:
            NewTopic: A NewTopic object configured with the topic name, partition count, 
                     and replication factor from the worker configuration. This object
                     is ready to be used with the Kafka admin clients create_topics method.
        """

        return NewTopic(
            topic=topic_name,
            num_partitions=self._num_partitions,
            replication_factor=self._replication_factor,
            config = {
                "cleanup.policy": "compact" if self._is_compacted else "delete"
            }
        )

    def create_topic(self, topic_name: str) -> None:
        """Create a single Kafka topic.
        
        Creates a new Kafka topic with the specified name using the partition count
        and replication factor configured in the WorkerConfig. If the topic already
        exists, the operation completes successfully (idempotent behavior).
        
        The topic will be created with the following properties:
        - Partition count: As specified in WorkerConfig.num_partitions
        - Replication factor: As specified in WorkerConfig.replication_factor
        - Default topic configuration from Kafka cluster settings
        
        Args:
            topic_name: The name of the Kafka topic to create. Must follow Kafka
                       topic naming conventions (max 249 characters, alphanumeric
                       characters, dots, dashes, and underscores only).
                       
        Raises:
            KafkaException: If topic creation fails due to Kafka-related errors
                           such as insufficient permissions, invalid configuration,
                           or broker connectivity issues
            Exception: For any other unexpected errors during topic creation
            
        Example:
            admin = TopicAdmin(config)
            admin.create_topic("user-events")
        """
        new_topic = self._create_new_topic(topic_name)
        
        try:
            futures = self._admin_client.create_topics([new_topic])
            _handle_topic_creation_result(futures, [topic_name])
            logger.info(f"Successfully processed topic creation for: {topic_name}")
        except Exception:
            # Re-raise the exception as it's already logged in _handle_topic_creation_result
            raise

    def create_topics(self, topic_names: list[str]) -> None:
        """Create multiple Kafka topics.
        
        Creates multiple Kafka topics in a single batch operation using the partition
        count and replication factor configured in the WorkerConfig. This method is
        more efficient than calling create_topic multiple times as it performs the
        creation operations in parallel.
        
        All topics will be created with the same configuration:
        - Partition count: As specified in WorkerConfig.num_partitions  
        - Replication factor: As specified in WorkerConfig.replication_factor
        - Default topic configuration from Kafka cluster settings
        
        If any topics already exist, they are skipped (idempotent behavior).
        If creation of any topic fails, the method raises an exception but other
        topics in the batch may still be created successfully.
        
        Args:
            topic_names: List of topic names to create in Kafka. Each name must
                        follow Kafka topic naming conventions. Empty list is
                        handled gracefully with a warning log.
                        
        Raises:
            KafkaException: If any topic creation fails due to Kafka-related errors
                           such as insufficient permissions, invalid configuration,
                           or broker connectivity issues  
            Exception: For any other unexpected errors during topic creation
            
        Example:
            admin = TopicAdmin(config)
            admin.create_topics(["user-events", "order-events", "payment-events"])
        """
        if not topic_names:
            logger.warning("No topics provided for creation")
            return

        new_topics = [self._create_new_topic(topic_name) for topic_name in topic_names]
        
        try:
            futures = self._admin_client.create_topics(new_topics)
            _handle_topic_creation_result(futures, topic_names)
            logger.info(f"Successfully processed topic creation for: {topic_names}")
        except Exception:
            # Re-raise the exception as it's already logged in _handle_topic_creation_result
            raise

    def delete_topics(self, topic_names: list[str]) -> None:
        """Delete multiple Kafka topics.

        Deletes specified Kafka topics in a single batch operation. This method
        allows for efficient removal of multiple topics at once, rather than
        deleting them one by one.

        If any topic does not exist, it is skipped (idempotent behavior).
        If deletion of any topic fails, the method raises an exception but other
        topics in the batch may still be deleted successfully.

        Args:
            topic_names: List of topic names to delete from Kafka. Each name must
                        follow Kafka topic naming conventions. Empty list is
                        handled gracefully with a warning log.

        Raises:
            KafkaException: If any topic deletion fails due to Kafka-related errors
                           such as insufficient permissions, invalid configuration,
                           or broker connectivity issues
            Exception: For any other unexpected errors during topic deletion

        Example:
            admin = TopicAdmin(config)
            admin.delete_topics(["user-events", "order-events"])
        """
        if not topic_names:
            logger.warning("No topics provided for deletion")
            return

        try:
            futures = self._admin_client.delete_topics(topic_names)
            for topic_name in topic_names:
                if topic_name in futures:
                    futures[topic_name].result()
                    logger.info(f"Successfully deleted topic: {topic_name}")
                else:
                    logger.warning(f"Topic {topic_name} not found for deletion")
        except Exception as e:
            logger.error(f"Failed to delete topics: {e}")
            raise

    def list_topics(self) -> dict[str, Any]:
        """List all available Kafka topics.
        
        Retrieves metadata for all topics in the Kafka cluster that the admin client
        has access to. This includes topic names, partition information, replica
        assignments, and other topic-level metadata.
        
        The returned dictionary contains topic metadata objects that provide detailed
        information about each topic including:
        - Number of partitions
        - Replica assignments for each partition  
        - In-sync replica (ISR) information
        - Topic configuration details
        
        Returns:
            dict[str, Any]: Dictionary mapping topic names to their metadata objects.
                           The metadata objects contain detailed information about
                           partitions, replicas, and topic configuration. Returns
                           empty dict if no topics exist or are accessible.
                           
        Raises:
            KafkaException: If unable to retrieve topic metadata due to Kafka-related
                           errors such as broker connectivity issues or insufficient
                           permissions
            Exception: For any other unexpected errors during metadata retrieval
            
        Example:
            admin = TopicAdmin(config)
            topics = admin.list_topics()
            for topic_name, metadata in topics.items():
                print(f"Topic: {topic_name}, Partitions: {len(metadata.partitions)}")
        """
        metadata: ClusterMetadata = self._admin_client.list_topics()
        return metadata.topics