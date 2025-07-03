"""
Schema Registry service for managing Avro/JSON/Protobuf serialization and deserialization.
"""

from typing import Dict, Optional, Callable
import logging

from confluent_kafka.schema_registry import SchemaRegistryClient, SchemaRegistryError
from confluent_kafka.schema_registry.json_schema import JSONSerializer, JSONDeserializer

logger = logging.getLogger(__name__)

class SchemaRegistryConfig:
    """Configuration for Schema Registry."""

    def __init__(
            self,
            url: str = "http://localhost:8081",
            api_key: str | None = None,
            api_secret: str | None = None,
            ssl_ca_location: str | None = None,
            ssl_cert_location: str | None = None,
            ssl_key_location: str | None = None
    ):
        self.url = url
        self.api_key = api_key
        self.api_secret = api_secret
        self.ssl_ca_location = ssl_ca_location
        self.ssl_cert_location = ssl_cert_location
        self.ssl_key_location = ssl_key_location

    def to_dict(self) -> Dict[str, str]:
        """Convert configuration to dictionary."""
        config = {'url': self.url}

        if self.api_key and self.api_secret:
            config.update({
                'basic.auth.credentials.source': 'USER_INFO',
                'basic.auth.user.info': f'{self.api_key}:{self.api_secret}'
            })

        if self.ssl_ca_location:
            config['ssl.ca.location'] = self.ssl_ca_location
        if self.ssl_cert_location:
            config['ssl.certificate.location'] = self.ssl_cert_location
        if self.ssl_key_location:
            config['ssl.key.location'] = self.ssl_key_location

        return config

class SchemaRegistryService:
    """Service for managing schema registry operations."""
    
    def __init__(
        self,
        config: SchemaRegistryConfig
    ):
        """
        Initialize Schema Registry service.
        
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
        """
        Register a schema with the Schema Registry.
        
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
    
    def get_latest_schema(self, subject: str) -> tuple[int, str]:
        """Get the latest schema for a subject."""
        try:
            schema_version = self.client.get_latest_version(subject)
            if schema_version and schema_version.schema_id and schema_version.schema and schema_version.schema.schema_str:
                return schema_version.schema_id, schema_version.schema.schema_str
            raise ValueError(f"Latest schema for subject '{subject}' not found or incomplete")
        except SchemaRegistryError as e:
            logger.error(f"Failed to get latest schema for subject '{subject}': {e}")
            raise

    def create_json_serializer(
        self, 
        schema_str: str, 
        to_dict: Optional[Callable] = None
    ) -> JSONSerializer:
        """Create JSON Schema serializer."""
        return JSONSerializer(
            schema_registry_client = self.client,
            schema_str = schema_str,
            to_dict=to_dict or (lambda obj, ctx: obj.__dict__ if hasattr(obj, '__dict__') else obj)
        )
    
    def create_json_deserializer(
        self, 
        schema_str: str, 
        from_dict: Optional[Callable] = None
    ) -> JSONDeserializer:
        """Create JSON Schema deserializer."""
        return JSONDeserializer(
            schema_registry_client = self.client,
            schema_str = schema_str,
            from_dict=from_dict or (lambda data, ctx: data)
        )