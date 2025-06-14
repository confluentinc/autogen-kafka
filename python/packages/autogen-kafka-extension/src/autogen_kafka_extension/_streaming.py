import uuid

from kstreams import Stream, middleware, StreamEngine, PrometheusMonitor, Consumer, Producer
from kstreams.types import StreamFunc

from autogen_kafka_extension._message_serdes import EventSerializer, EventDeserializer
from autogen_kafka_extension._topic_admin import TopicAdmin
from autogen_kafka_extension.worker_config import WorkerConfig


class Streaming(StreamEngine):
    def __init__(self, config: WorkerConfig):
        super().__init__(
            backend=config.get_kafka_backend(),
            title=config.title,
            serializer=EventSerializer(),
            monitor=PrometheusMonitor(),
            consumer_class = Consumer,
            producer_class = Producer,
        )
        self._config = config
        self._topics_admin = TopicAdmin(self._config)

    def create_topics(self, topics: list[str]) -> None:
        """
        Create Kafka topics if they do not already exist.
        """
        self._topics_admin.create_topics(topics=topics)

    def create_and_add_stream(self,
                            name: str,
                            topics: list[str],
                            group_id: str,
                            client_id: str,
                            func: StreamFunc) -> Stream:
        # Make sure the topics exist
        self._topics_admin.create_topics(topics=topics)

        # Create and add a stream for incoming requests
        stream = Stream(
            topics=topics,
            name=name,
            func=func,
            middlewares=[middleware.Middleware(EventDeserializer)],
            config={
                "client_id": client_id + str(uuid.uuid4()),
                "group_id": group_id + str(uuid.uuid4()),
                "auto_offset_reset": "latest",
                "enable_auto_commit": True
            },
            backend=self.backend
        )
        self.add_stream(stream)

        return stream

