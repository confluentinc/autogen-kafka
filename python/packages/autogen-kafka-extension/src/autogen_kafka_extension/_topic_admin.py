import logging
from typing import Any

from confluent_kafka import KafkaException, KafkaError
from confluent_kafka.admin import ClusterMetadata
from confluent_kafka.cimpl import NewTopic

from autogen_kafka_extension.worker_config import WorkerConfig

logger = logging.getLogger(__name__)


class TopicAdmin:
    """Admin client for managing Kafka topics."""

    def __init__(self, config: WorkerConfig) -> None:
        """Initialize TopicAdmin with worker configuration.
        
        Args:
            config: WorkerConfig containing Kafka connection settings, partition count, 
                   and replication factor for topic creation
        """
        self._config = config
        self._admin_client = config.get_admin_client()

    def _create_new_topic(self, topic_name: str) -> NewTopic:
        """Create a NewTopic object with configured partitions and replication factor.
        
        Args:
            topic_name: The name of the Kafka topic to create
            
        Returns:
            NewTopic object configured with the topic name, partition count, and 
            replication factor from the worker configuration
        """
        return NewTopic(
            topic=topic_name,
            num_partitions=self._config.num_partitions,
            replication_factor=self._config.replication_factor
        )

    def _handle_topic_creation_result(self, futures: dict, topic_names: list[str]) -> None:
        """Handle the results of topic creation futures.
        
        Args:
            futures: Dictionary mapping topic names to their creation Future objects
            topic_names: List of topic names that were requested to be created
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

    def create_topic(self, topic_name: str) -> None:
        """Create a single Kafka topic.
        
        Args:
            topic_name: The name of the Kafka topic to create
        """
        new_topic = self._create_new_topic(topic_name)
        
        try:
            futures = self._admin_client.create_topics([new_topic])
            self._handle_topic_creation_result(futures, [topic_name])
            logger.info(f"Successfully processed topic creation for: {topic_name}")
        except Exception:
            # Re-raise the exception as it's already logged in _handle_topic_creation_result
            raise

    def create_topics(self, topic_names: list[str]) -> None:
        """Create multiple Kafka topics.
        
        Args:
            topic_names: List of topic names to create in Kafka
        """
        if not topic_names:
            logger.warning("No topics provided for creation")
            return

        new_topics = [self._create_new_topic(topic_name) for topic_name in topic_names]
        
        try:
            futures = self._admin_client.create_topics(new_topics)
            self._handle_topic_creation_result(futures, topic_names)
            logger.info(f"Successfully processed topic creation for: {topic_names}")
        except Exception:
            # Re-raise the exception as it's already logged in _handle_topic_creation_result
            raise

    def list_topics(self) -> dict[str, Any]:
        """List all available Kafka topics.
        
        Returns:
            Dictionary mapping topic names to their metadata (partitions, replicas, etc.)
        """
        metadata: ClusterMetadata = self._admin_client.list_topics()
        return metadata.topics