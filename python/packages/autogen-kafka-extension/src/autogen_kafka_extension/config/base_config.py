"""Base configuration class for all autogen-kafka-extension configurations.

This module provides the abstract base class that defines common patterns
and validation logic used across all configuration classes in the extension.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseConfig(ABC):
    """Abstract base class for all configuration objects.
    
    This class defines the common interface and validation patterns used
    across all configuration classes in the autogen-kafka-extension.
    It provides basic validation, common properties, and ensures consistency
    in configuration handling.
    
    Subclasses must implement the validate() method to provide specific
    validation logic for their configuration parameters.
    """
    
    def __init__(self) -> None:
        """Initialize the base configuration.
        """
        self._validated = False

    @property 
    def is_validated(self) -> bool:
        """Check if this configuration has been validated.
        
        Returns:
            True if validate() has been called successfully, False otherwise.
        """
        return self._validated
    
    @abstractmethod
    def validate(self) -> None:
        """Validate the configuration parameters.
        
        This method should check all configuration parameters for validity
        and raise appropriate exceptions if any issues are found.
        
        Raises:
            ValueError: If any configuration parameters are invalid.
            TypeError: If any parameters have incorrect types.
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary representation.
        
        Returns:
            A dictionary containing all public configuration parameters.
            Private attributes (starting with _) are excluded.
        """
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if hasattr(value, 'to_dict'):
                    result[key] = value.to_dict()
                else:
                    result[key] = value
        return result
    
    def __repr__(self) -> str:
        """Return string representation of the configuration."""
        return f"{self.__class__.__name__}"