import base64
import json
from typing import Dict

from autogen_core import Image
from autogen_core.memory import MemoryContent, MemoryMimeType


class MemoryEvent:
    """
    Represents a memory event with a timestamp and a value.
    """

    @property
    def memory_content(self) -> MemoryContent:
        """
        Get the memory content of the event.

        Returns:
            MemoryContent: The memory content associated with this event.
        """
        return self._memory_content

    @property
    def sender(self) -> str:
        """
        Get the sender of the event.

        Returns:
            str: The sender of this memory event.
        """
        return self._sender

    def __init__(self, memory_content: MemoryContent, sender: str):
        self._memory_content = memory_content
        self._sender = sender

    def __repr__(self):
        return f"MemoryEvent(content={self._memory_content.__repr__()}, sender={self._sender})"

    def to_dict(self):

        mime_type = self._memory_content.mime_type
        if mime_type in [MemoryMimeType.TEXT, MemoryMimeType.MARKDOWN]:
            content = str(self._memory_content.content)
        elif mime_type == MemoryMimeType.JSON:
            if isinstance(self._memory_content.content, dict):
                content = json.dumps(self._memory_content.content)
            elif isinstance(self._memory_content.content, str):
                content = str(self._memory_content.content)
            else:
                raise ValueError("JSON content must be a dict or str")
        elif mime_type in [MemoryMimeType.IMAGE, MemoryMimeType.BINARY]:
            if isinstance(self._memory_content.content, bytes):
                content = base64.b64encode(self._memory_content.content).decode("ascii")
            elif isinstance(self._memory_content.content, str):
                content = self._memory_content.content
            elif isinstance(self._memory_content.content, Image):
                content = self._memory_content.content.to_base64()
            else:
                raise ValueError("Image or binary content must be bytes, str, or Image instance")
        else:
            raise ValueError(f"Unsupported content type: {mime_type}")


        return {
            "sender": self._sender,
            "mime_type": str(self._memory_content.mime_type.value),
            "content": content,
            "metadata": json.dumps(self._memory_content.metadata) if self._memory_content.metadata else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "MemoryEvent":
        """
        Create a MemoryEvent instance from a dictionary.

        Args:
            data (dict): Dictionary containing 'timestamp' and 'value'.

        Returns:
            MemoryEvent: An instance of MemoryEvent.
        """
        sender = data["sender"]
        mime_type = MemoryMimeType(data.get("mime_type"))
        if mime_type is None:
            raise ValueError("Missing 'mime_type' in data")

        content = data.get("content")
        metadata = json.loads(data.get("metadata"))

        decoded_content = None
        if mime_type in [MemoryMimeType.TEXT, MemoryMimeType.MARKDOWN]:
            decoded_content = content
        elif mime_type == MemoryMimeType.JSON:
            decoded_content = json.loads(content)
        elif mime_type == MemoryMimeType.IMAGE:
            decoded_content = Image.from_base64(content)
        elif mime_type == MemoryMimeType.BINARY:
            decoded_content = content.encode("ascii")
        else:
            raise ValueError(f"Unsupported content type: {mime_type}")

        memory_content = MemoryContent(
            content=decoded_content,
            mime_type=MemoryMimeType(mime_type) if isinstance(mime_type, str) else mime_type,
            metadata=metadata if metadata else None
        )

        return cls(memory_content=memory_content, sender=sender)