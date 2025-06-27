"""Auto-validation decorator for configuration classes.

This module provides a decorator that automatically validates configuration
objects at the right time - after all initialization is complete.
"""

from typing import TypeVar, Type
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

def auto_validate_after_init(cls: Type[T]) -> Type[T]:
    """Class decorator that automatically validates configuration after initialization.
    
    This decorator wraps the __init__ method to call validation after
    all initialization is complete, solving the initialization order problem.
    
    Features:
    - Validation runs after all properties are set
    - Won't fail initialization even if validation fails
    - Validation results are cached for later access
    - Works with any BaseConfig subclass
    
    Example:
        @auto_validate_after_init
        class MyConfig(BaseConfig):
            def __init__(self, value):
                super().__init__()
                self.value = value
            
            def _validate_impl(self):
                errors = []
                if not self.value:
                    errors.append("value cannot be empty")
                return ValidationResult(is_valid=len(errors)==0, errors=errors)
    
    Args:
        cls: The configuration class to decorate
        
    Returns:
        The decorated class with auto-validation
    """
    original_init = cls.__init__
    
    @wraps(original_init)
    def wrapped_init(self, *args, **kwargs):
        """Wrapped initialization that auto-validates after completion."""
        # Call the original __init__ first
        original_init(self, *args, **kwargs)
        
        # Now that initialization is complete, trigger validation
        try:
            if hasattr(self, 'validate'):
                result = self.validate()
                logger.debug(f"Auto-validated {cls.__name__}: valid={result.is_valid}")
                if result.warnings:
                    for warning in result.warnings:
                        logger.warning(f"{cls.__name__}: {warning}")
        except Exception as e:
            # Don't fail initialization if validation fails
            # The validation error will be available when explicitly checked
            logger.debug(f"Auto-validation failed for {cls.__name__}: {e}")
    
    # Replace the original __init__ with our wrapped version
    cls.__init__ = wrapped_init
    return cls

def validate_on_property_access(*property_names: str):
    """Property decorator that ensures validation before accessing specific properties.
    
    This can be used as an additional safety net for critical properties.
    
    Args:
        *property_names: Names of properties that should trigger validation
    
    Example:
        class MyConfig(BaseConfig):
            @property
            @validate_on_property_access
            def critical_value(self):
                return self._critical_value
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Ensure validation has run before accessing the property
            if hasattr(self, 'validate') and hasattr(self, '_validation_result'):
                if self._validation_result is None:
                    try:
                        self.validate()
                    except Exception:
                        pass  # Don't prevent property access
            return func(self, *args, **kwargs)
        return wrapper
    return decorator 