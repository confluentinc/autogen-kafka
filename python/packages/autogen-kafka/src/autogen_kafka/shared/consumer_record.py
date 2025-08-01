from typing import Any, Dict


class ConsumerRecord:

    def __init__(self,
                 topic: str,
                 partition: int,
                 offset: int,
                 key: bytes,
                 value: Any,
                 headers: Dict[str, Any]):
        self.topic = topic
        self.partition = partition
        self.offset = offset
        self.key = key
        self.value = value
        self.headers = headers

    def __repr__(self):
        return f"ConsumerRecord(topic={self.topic}, partition={self.partition}, offset={self.offset}, key={self.key}, value={self.value}, timestamp={self.timestamp}, headers={self.headers})"
