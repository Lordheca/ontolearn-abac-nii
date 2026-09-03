from typing import Any

from main.libs.log import get_logger
from main.libs.retrieve_lib.environment_retrieve_lib import _call_environment_function


logger = get_logger(__name__)


async def get_environment_attributes(
    input_data: dict[str, dict[str, Any] | list[Any] | Any],
) -> dict[str, list[Any] | dict[str, Any]]:
    """
    Retrieve environment attributes by dynamically calling environment functions.

    Args:
        input_data:
            Dict where:
                - key: function name (string)
                - value: parameters for that function, in one of forms:
                    * dict  -> passed as **kwargs
                    * list/tuple -> passed as *args
                    * single value -> passed as single positional arg

            Example:
                {
                    "geo_location": {
                        "location": "Japan",
                        "latitude": 35.6895,
                        "longitude": 139.6917
                    },
                    "get_quota": {
                        "server_id": "1234567890"
                    }
                }

    Returns:
        Dict mapping function name to:
            - list of return values (even if the function only returns 1 value,
              it will be wrapped into a single-element list), or
            - error dict if there's an error when calling.
    """
    environment_attributes: dict[str, list[Any] | dict[str, Any]] = {}

    for func_name, params in input_data.items():
        try:
            # _call_environment_function now supports:
            # - dict  -> kwargs
            # - list/tuple -> args
            # - single value / None
            result = await _call_environment_function(func_name, params)

            # Normalize: always return a list of values for each function
            if isinstance(result, (list, tuple)):
                values = list(result)
            else:
                values = [result]

            environment_attributes[func_name] = values
        except Exception as exc:
            environment_attributes[func_name] = {
                "error": f"Failed to call environment function '{func_name}': {exc!s}",
            }

    logger.info(
        "Environment attributes retrieved",
        data=environment_attributes,
    )

    return environment_attributes
