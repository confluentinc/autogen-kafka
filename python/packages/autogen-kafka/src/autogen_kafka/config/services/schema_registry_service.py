import json
import logging
from typing import Optional, Callable

from confluent_kafka.schema_registry import SchemaRegistryClient, SchemaRegistryError
from confluent_kafka.schema_registry._sync.json_schema import JSONSerializer, JSONDeserializer

from autogen_kafka.config.schema_registry_config import SchemaRegistryConfig

logger = logging.getLogger(__name__)

class SchemaRegistryService:
    """Service for managing schema registry operations."""

    def __init__(
            self,
            config: SchemaRegistryConfig
    ):
        """Initialize Schema Registry service.

        Args:
            config: SchemaRegistryConfig instance containing connection details.
        """
        try:
            self.client = SchemaRegistryClient(config.to_dict())
            logger.info(f"Connected to Schema Registry at {config.url}")
        except Exception as e:
            logger.error(f"Failed to connect to Schema Registry: {e}")
            raise

    def register_schema(self, subject: str, schema_str: str, schema_type: str = "AVRO") -> int:
        """Register a schema with the Schema Registry.

        Args:
            subject: Subject name for the schema
            schema_str: Schema definition as string
            schema_type: Type of schema (AVRO, JSON, PROTOBUF)

        Returns:
            Schema ID
        """
        try:
            from confluent_kafka.schema_registry import Schema

            schema = Schema(schema_str, schema_type)
            schema_id = self.client.register_schema(subject, schema)
            logger.info(f"Registered schema for subject '{subject}' with ID {schema_id}")
            return schema_id
        except SchemaRegistryError as e:
            logger.error(f"Failed to register schema for subject '{subject}': {e}")
            raise

    def get_schema(self, schema_id: int) -> str:
        """Get schema by ID."""
        try:
            schema = self.client.get_schema(schema_id)
            if schema and schema.schema_str:
                return schema.schema_str
            raise ValueError(f"Schema with ID {schema_id} not found or has no schema string")
        except SchemaRegistryError as e:
            logger.error(f"Failed to get schema with ID {schema_id}: {e}")
            raise

    def get_latest_schema(self, subject: str) -> tuple[int | None, str | None] | tuple[None, None]:
        """Get the latest schema for a subject."""
        try:
            schema_version = self.client.get_latest_version(subject)
            if schema_version and schema_version.schema_id and schema_version.schema and schema_version.schema.schema_str:
                return schema_version.schema_id, schema_version.schema.schema_str
            raise ValueError(f"Latest schema for subject '{subject}' not found or incomplete")
        except SchemaRegistryError as e:
            if e.http_status_code == 404:
                logger.debug(f"Subject '{subject}' not found in Schema Registry")
                return None, None

            logger.error(f"Failed to get latest schema for subject '{subject}': {e}")
            raise

    def create_json_serializer(
            self,
            schema_str: str,
            to_dict: Optional[Callable] = None
    ) -> JSONSerializer:
        """Create JSON Schema serializer."""
        return JSONSerializer(
            schema_registry_client=self.client,
            schema_str=schema_str,
            to_dict=to_dict or (lambda obj, ctx: obj.__dict__ if hasattr(obj, '__dict__') else obj),
            conf = {
                "auto.register.schemas": True,
            }
        )

    def create_json_deserializer(
            self,
            schema_str: str,
            from_dict: Optional[Callable] = None
    ) -> JSONDeserializer:
        """Create JSON Schema deserializer."""
        return JSONDeserializer(
            schema_registry_client=self.client,
            schema_str=schema_str,
            from_dict=from_dict or (lambda data, ctx: data)
        )

    def register_or_upgrade_schema(self, topic: str, for_key: bool, schema_str: str, schema_type: str = "AVRO") -> dict:
        """
        Register a schema or upgrade if schema already exists and needs upgrading.

        Args:
            topic: Topic name for the schema
            for_key: Whether the schema is for the key or value
            schema_str: Schema definition as string
            schema_type: Type of schema (AVRO, JSON, PROTOBUF)

        Returns:
            Dictionary containing:
            - 'schema_id': The schema ID
            - 'action': 'registered' (new registration) or 'upgraded' (schema upgraded) or 'exists' (no change needed)
            - 'version': The version number
            - 'message': Description of what happened
        """

        subject = f"{topic}-key" if for_key else f"{topic}-value"

        try:
            from confluent_kafka.schema_registry import Schema

            schema = Schema(schema_str, schema_type)

            # Try to get the latest schema for this subject
            try:
                compatible = self.client.test_compatibility(subject, schema)
                if not compatible:
                    logger.warning(f"Schema for subject '{subject}' is not compatible: {compatible}")
                    raise SchemaRegistryError(f"Schema for subject '{subject}' is not compatible")

                latest_schema_id, latest_schema_str = self.get_latest_schema(subject)
                if latest_schema_id is None:
                    return self._register_schema(schema, subject)

                latest = json.loads(latest_schema_str)
                schema_to_add = json.loads(schema_str)

                # Compare schemas to see if upgrade is needed
                if latest == schema_to_add:
                    logger.info(f"Schema for subject '{subject}' is already up to date")
                    latest_version = self.client.get_latest_version(subject)
                    return {
                        'schema_id': latest_schema_id,
                        'action': 'exists',
                        'version': latest_version.version,
                        'message': f"Schema for subject '{subject}' already exists and is up to date"
                    }
                else:
                    return self._register_schema(schema, subject)

            except (SchemaRegistryError, ValueError):
                return self._register_schema(schema, subject)

        except SchemaRegistryError as e:
            logger.error(f"Failed to register or upgrade schema for subject '{subject}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during schema registration/upgrade for subject '{subject}': {e}")
            raise

    def _register_schema(self, schema, subject):
        # Schema needs to be upgraded
        schema_id = self.client.register_schema(subject, schema)
        # Get the new version number
        new_version = self.client.get_latest_version(subject)
        logger.info(
            f"Upgraded schema for subject '{subject}' to version {new_version.version} with ID {schema_id}")
        return {
            'schema_id': schema_id,
            'action': 'upgraded',
            'version': new_version.version,
            'message': f"Schema for subject '{subject}' upgraded to version {new_version.version}"
        }
