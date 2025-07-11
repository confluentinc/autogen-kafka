import json
import logging
from typing import Any

from azure.core.messaging import CloudEvent
from pydantic import BaseModel

from ..shared.events import get_cloudevent_json_schema_compact

logger = logging.getLogger(__name__)

class SchemaUtils:

    @staticmethod
    def get_schema_str(obj_type: type) -> str:
        message_schema = SchemaUtils.get_schema(obj_type)
        return json.dumps(message_schema)

    @staticmethod
    def get_schema(obj_type: type) -> Any:
        if issubclass(obj_type, BaseModel):
            return obj_type.model_json_schema()
        elif obj_type == CloudEvent:
            return json.loads(get_cloudevent_json_schema_compact())
        elif getattr(obj_type, '__schema__', None) is not None:
            return json.loads(obj_type.__schema__())
        else:
            logging.error(f"Object type {obj_type} does not have a schema defined.")
            raise ValueError(f"Object type {obj_type} does not have a schema defined.")