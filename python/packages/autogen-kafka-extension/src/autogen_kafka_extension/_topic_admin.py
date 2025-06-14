import logging
from typing import Any

from confluent_kafka import KafkaException, KafkaError
from confluent_kafka.admin import ClusterMetadata
from confluent_kafka.cimpl import NewTopic
from kafka.errors import TopicAlreadyExistsError

from autogen_kafka_extension.worker_config import WorkerConfig

logger = logging.getLogger(__name__)

class TopicAdmin:

    def __init__(self, config: WorkerConfig):
        self._config = config
        self._admin_client = config.get_admin_client()

    def create_topic(self, topic_name):
        new_topic = NewTopic(topic=topic_name,
            num_partitions=self._config.num_partitions,
            replication_factor=self._config.replication_factor)
        try:
            futures = self._admin_client.create_topics([new_topic])
            if topic_name in futures:
                futures[topic_name].result()
            else:
                logger.error(f"Failed to create topic {topic_name}. No future returned.")
                raise Exception(f"Failed to create topic {topic_name}. No future returned.")

            logger.info(f"Created topic {topic_name}")
        except KafkaException as e:
            if e.args[0] == KafkaError.TOPIC_ALREADY_EXISTS:
                logger.debug(f"Topic {topic_name} already exists")
            else:
                logger.error(f"Failed to create topic {topic_name}: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to create topic {topic_name}: {e}")
            raise

    def list_topics(self) -> dict[str, Any]:
        metadata: ClusterMetadata = self._admin_client.list_topics()
        return metadata.topics

    def create_topics(self, topics: list[str]) -> None:
        new_topics = []
        for topic in topics:
            new_topic = NewTopic(topic=topic,
                                 num_partitions=self._config.num_partitions,
                                 replication_factor=self._config.replication_factor)
            new_topics.append(new_topic)
        try:
            futures = self._admin_client.create_topics(new_topics)
            for topic_name in topics:
                if topic_name in futures:
                    futures[topic_name].result()
                else:
                    logger.error(f"Failed to create topic {topic_name}. No future returned.")
                    raise Exception(f"Failed to create topic {topic_name}. No future returned.")

            logger.info(f"Created topics {topics}")
        except KafkaException as e:
            if e.args[0] == KafkaError.TOPIC_ALREADY_EXISTS:
                logger.debug(f"Topic {topics} already exists")
            else:
                logger.error(f"Failed to create topic {topics}: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to create topic {topics}: {e}")
            raise