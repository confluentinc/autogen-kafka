"""Base configuration class for all autogen-kafka-extension configurations.

This module provides the abstract base class that defines common patterns
and validation logic used across all configuration classes in the extension.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Union, Type
from dataclasses import dataclass
from pathlib import Path
import threading

T = TypeVar('T', bound='BaseConfig')

class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass

@dataclass(frozen=True)
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: list[str]
    warnings: list[str] | None = None
    
    def __post_init__(self):
        if self.warnings is None:
            object.__setattr__(self, 'warnings', [])

class BaseConfig(ABC):
    """Abstract base class for all configuration objects.
    
    This class defines the common interface and validation patterns used
    across all configuration classes in the autogen-kafka-extension.
    It provides validation caching, immutability patterns, and ensures 
    consistency in configuration handling.
    
    Subclasses must implement the _validate_impl() method to provide specific
    validation logic for their configuration parameters.
    """
    
    def __init__(self) -> None:
        """Initialize the base configuration."""
        self._validation_result: ValidationResult | None = None
        self._validation_lock = threading.RLock()
        # Note: Validation is deferred until first access to avoid initialization order issues

    @property 
    def is_validated(self) -> bool:
        """Check if this configuration has been validated successfully.
        
        This will trigger validation if it hasn't been performed yet.
        
        Returns:
            True if validate() has been called successfully, False otherwise.
        """
        try:
            result = self.validate()
            return result.is_valid
        except ConfigValidationError:
            return False
    
    @property
    def validation_result(self) -> ValidationResult | None:
        """Get the last validation result.
        
        Returns:
            ValidationResult if validation has been performed, None otherwise.
        """
        with self._validation_lock:
            return self._validation_result

    def validate(self) -> ValidationResult:
        """Validate the configuration parameters.
        
        This method checks all configuration parameters for validity
        and caches the result for subsequent calls.
        
        Returns:
            ValidationResult containing validation status and any errors/warnings.
            
        Raises:
            ConfigValidationError: If validation fails with critical errors.
        """
        with self._validation_lock:
            # Return cached result if available
            if self._validation_result is not None:
                return self._validation_result
                
            # Perform validation
            self._validation_result = self._validate_impl()
            
            # Raise exception for critical errors
            if not self._validation_result.is_valid:
                raise ConfigValidationError(
                    f"Configuration validation failed: {'; '.join(self._validation_result.errors)}"
                )
                
            return self._validation_result
    
    @abstractmethod
    def _validate_impl(self) -> ValidationResult:
        """Implement specific validation logic.
        
        Subclasses should implement this method to provide their specific
        validation rules.
        
        Returns:
            ValidationResult with validation status and messages.
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
    
    def ensure_valid(self) -> None:
        """Ensure the configuration is valid, raising an exception if not.
        
        This method can be called to explicitly validate the configuration
        and raise an exception immediately if validation fails.
        
        Raises:
            ConfigValidationError: If the configuration is invalid.
        """
        self.validate()
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create a configuration instance from a dictionary.
        
        This method should be implemented by subclasses to create instances
        from dictionary data loaded from files or environment variables.
        
        Args:
            data: Dictionary containing configuration parameters.
            
        Returns:
            Configuration instance.
            
        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Subclasses must implement from_dict method")
    
    @classmethod
    def from_file(
        cls: Type[T], 
        config_file: Union[str, Path],
        env_prefix: str = "AUTOGEN_KAFKA",
        base_config: Dict[str, Any] | None = None
    ) -> T:
        """Load configuration from a file with optional environment variable overrides.
        
        Args:
            config_file: Path to JSON or YAML configuration file.
            env_prefix: Prefix for environment variables that can override file values.
            base_config: Base configuration dictionary to merge with.
            
        Returns:
            Configuration instance loaded from file and environment.
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
            ValueError: If the file format is invalid.
        """
        # Import here to avoid circular imports
        from .config_loader import ConfigLoader
        
        merged_config = ConfigLoader.load_config(
            config_file=config_file,
            env_prefix=env_prefix,
            base_config=base_config
        )
        
        return cls.from_dict(merged_config)
    
    @classmethod
    def from_env(
        cls: Type[T],
        env_prefix: str = "AUTOGEN_KAFKA",
        base_config: Dict[str, Any] | None = None
    ) -> T:
        """Load configuration from environment variables.
        
        Args:
            env_prefix: Prefix for environment variables.
            base_config: Base configuration dictionary to merge with.
            
        Returns:
            Configuration instance loaded from environment variables.
        """
        # Import here to avoid circular imports
        from .config_loader import ConfigLoader
        
        merged_config = ConfigLoader.load_config(
            config_file=None,
            env_prefix=env_prefix,
            base_config=base_config
        )
        
        return cls.from_dict(merged_config)

    @staticmethod
    def config_key():
        """Get the configuration key for this class.

        This method can be overridden by subclasses to provide a unique
        key for identifying the configuration type.

        Returns:
            A string representing the configuration key.
        """
        raise NotImplementedError("Subclasses must implement config_key method.")

    def __repr__(self) -> str:
        """Return string representation of the configuration."""
        # Check validation status without triggering validation
        with self._validation_lock:
            if self._validation_result is not None:
                validation_status = "✓" if self._validation_result.is_valid else "✗"
            else:
                validation_status = "?"
        return f"{self.__class__.__name__}(validated={validation_status})"