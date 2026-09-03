from collections.abc import Callable
from datetime import datetime, timezone


# Registry of environment functions that can be called
# Key: function name (string), Value: function reference
ENVIRONMENT_FUNCTIONS_REGISTRY: dict[str, Callable] = {}


def register_environment_function(func_name: str, func: Callable) -> None:
    """
    Register an environment function in the registry.

    This function allows you to register custom environment functions that can be called
    dynamically based on the `environments_to_check` field in resources.

    Args:
        func_name: Name of the function (used as key in environments_to_check JSON)
        func: The function to register (can be async or sync)

    Example:
        To register a new environment function:

        ```python
        # Define your custom environment function
        async def get_user_ip_address(ip: str | None = None, *args, **kwargs) -> str:
            if ip:
                return f"IP_{ip}"
            return "Unknown_IP"

        # Register it
        from main.services import external_service
        external_service.register_environment_function("get_user_ip_address", get_user_ip_address)
        ```

        Then in your resource's `environments_to_check` JSON field:
        ```json
        {
            "get_user_ip_address": ["192.168.1.1"]
        }
        ```

    Note:
        - Functions can be async or sync
        - Function parameters will be passed as a list from the JSON
        - Use *args and **kwargs in your function signature for flexibility
    """
    ENVIRONMENT_FUNCTIONS_REGISTRY[func_name] = func


def get_environment_function(func_name: str) -> Callable | None:
    """
    Get an environment function from the registry by name.

    Args:
        func_name: Name of the function

    Returns:
        The function if found, None otherwise
    """
    return ENVIRONMENT_FUNCTIONS_REGISTRY.get(func_name)


# ============================================================================
# Example environment functions - these can be extended or replaced
# ============================================================================
#
# HOW TO ADD A NEW ENVIRONMENT FUNCTION:
#
# 1. Define your function (can be async or sync):
#    ```python
#    async def my_custom_function(param1: str, param2: int | None = None, *args, **kwargs) -> str:
#        # Your logic here
#        return f"Result: {param1}, {param2}"
#    ```
#
# 2. Register it using register_environment_function():
#    ```python
#    from main.services import external_service
#    external_service.register_environment_function("my_custom_function", my_custom_function)
#    ```
#
# 3. Use it in your resource's environments_to_check JSON field:
#    ```json
#    {
#        "my_custom_function": ["value1", 123]
#    }
#    ```
#
# Note: Function parameters are passed as a list from the JSON, so use *args
#       in your function signature to handle variable parameters.
# ============================================================================


async def get_current_time(*args, **kwargs) -> str:
    """
    Get current time in ISO format.

    Returns:
        Current time as ISO format string
    """
    return datetime.now(timezone.utc).isoformat()


async def get_location(location_id: str | None = None, *args, **kwargs) -> str:
    """
    Get location information.

    Args:
        location_id: Optional location identifier

    Returns:
        Location string
    """
    if location_id:
        return f"Location_{location_id}"
    return "Default_Location"


async def get_device_type(device_id: str | None = None, *args, **kwargs) -> str:
    """
    Get device type information.

    Args:
        device_id: Optional device identifier

    Returns:
        Device type string
    """
    if device_id:
        return f"Device_{device_id}"
    return "Default_Device"


# Register default environment functions
register_environment_function("get_current_time", get_current_time)
register_environment_function("get_location", get_location)
register_environment_function("get_device_type", get_device_type)


# ============================================================================
# EXAMPLE: How to add a new custom environment function
# ============================================================================
#
# Step 1: Define your custom function (can be async or sync)
# ----------------------------------------------------------------------------
# async def get_user_ip_address(ip: str | None = None, *args, **kwargs) -> str:
#     """
#     Get user IP address information.
#
#     Args:
#         ip: Optional IP address string
#
#     Returns:
#         IP address string
#     """
#     if ip:
#         return f"IP_{ip}"
#     return "Unknown_IP"
#
#
# Step 2: Register the function (can be done in your application startup or module)
# ----------------------------------------------------------------------------
# from main.services import external_service
# external_service.register_environment_function("get_user_ip_address", get_user_ip_address)
#
#
# Step 3: Use it in your resource's environments_to_check JSON field
# ----------------------------------------------------------------------------
# In your database, set the environments_to_check field for a resource:
# {
#     "get_user_ip_address": ["192.168.1.1"],
#     "get_current_time": [],
#     "get_location": ["office_123"]
# }
#
# The system will automatically call these functions with the provided parameters
# when retrieving environment attributes for that resource.
#
# ============================================================================
