from typing import Any

from main.commons.resources.resource import Resource
from main.libs.retrieve_lib.common import get_resource_instance_types
from main.services import external_service


async def _call_environment_function(
    func_name: str,
    params: list[Any] | dict[str, Any] | None = None,
) -> Any:
    """
    Call an environment function with given parameters.

    Args:
        func_name: Name of the function to call
        params: List of parameters to pass to the function

    Returns:
        Result from the function call

    Raises:
        ValueError: If function is not found in registry
        Exception: If function call fails
    """
    func = external_service.get_environment_function(func_name)
    if func is None:
        # Strict behavior: function must be registered in ENVIRONMENT_FUNCTIONS_REGISTRY
        raise ValueError(
            f"Environment function '{func_name}' is not registered "
            "in ENVIRONMENT_FUNCTIONS_REGISTRY.",
        )

    # Call the function with parameters
    import inspect

    if params is None:
        call_args: tuple[list[Any], dict[str, Any]] = ([], {})
    elif isinstance(params, dict):
        call_args = ([], params)
    elif isinstance(params, list | tuple):  # type: ignore[arg-type]
        call_args = (list(params), {})
    else:
        # Single value -> positional argument
        call_args = ([params], {})

    args, kwargs = call_args

    # Check if function is async
    if hasattr(func, "__call__"):
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    # Fallback: call callable-like objects
    return func(*args, **kwargs)


def _get_all_environments_to_check_from_resource(resource: Resource) -> dict:
    """
    Get and merge all environments_to_check from a Resource instance and its parent hierarchy.
    Merges from most distant ancestor to closest parent, then child.
    If both child and parent have the same function name, child's value takes precedence.

    Example:
        GrandParent: {"func1": [1]}
        Parent: {"func1": [2], "func2": [3]}
        Child: {"func2": [4]}
        Result: {"func1": [2], "func2": [4]}
        (Parent's func1 overrides GrandParent's, Child's func2 overrides Parent's)

    Args:
        resource: Resource instance

    Returns:
        Merged environments_to_check dict (child overrides parent for same function names)
    """
    merged_envs = {}

    # Collect all environments_to_check from parent hierarchy (from closest to most distant)
    # We'll merge in reverse order so closer parents override distant ancestors
    parent_envs_list = []
    current = resource
    while current:
        if hasattr(current, "parent") and current.parent:
            parent = current.parent
            if hasattr(parent, "environments_to_check"):
                parent_envs = parent.environments_to_check
                if (
                    parent_envs
                    and isinstance(parent_envs, dict)
                    and len(parent_envs) > 0
                ):
                    parent_envs_list.append(parent_envs)
            current = parent
        else:
            break

    # Merge parent environments from most distant to closest
    # This means closer parents override distant ancestors
    for parent_envs in reversed(parent_envs_list):
        merged_envs.update(parent_envs)

    # Finally, add/override with child's environments_to_check (child takes precedence over all)
    if hasattr(resource, "environments_to_check"):
        child_envs = resource.environments_to_check
        if child_envs and isinstance(child_envs, dict) and len(child_envs) > 0:
            merged_envs.update(child_envs)

    return merged_envs


async def get_additional_environment_attributes(
    resources: list[dict | Resource] | None,
) -> dict:
    """
    Retrieve environment attributes from resources.

    For each resource in the list, extracts the `environments_to_check` dict,
    calls the corresponding functions with their parameters, and collects results.

    Args:
        resources: List of resource dictionaries or Resource instances,
                   each containing an `environments_to_check` field

    Returns:
        A dictionary of environment attributes, where keys are resource identifiers
        and values are dictionaries of function results
    """
    if not resources:
        return {}

    environment_attributes = {}

    for resource in resources:
        # Handle both Resource instances and dicts
        if isinstance(resource, Resource):
            # Extract and merge all environments_to_check from Resource instance and parent hierarchy
            environments_to_check = _get_all_environments_to_check_from_resource(
                resource,
            )
            # Get resource identifier
            resource_id = (
                getattr(resource, "id", None)
                or getattr(resource, "_id", None)
                or f"resource_{resources.index(resource)}"
            )
        else:
            # Handle dict (for backward compatibility, but dicts don't have parent hierarchy)
            environments_to_check = resource.get("environments_to_check") or {}
            # Get resource identifier
            resource_id = (
                resource.get("id")
                or resource.get("_id")
                or f"resource_{resources.index(resource)}"
            )

        if (
            not environments_to_check
            or not isinstance(environments_to_check, dict)
            or len(environments_to_check) == 0
        ):
            continue

        # Store results for this resource
        resource_env_attributes = {}

        # Iterate through each function name and its parameters
        for func_name, params in environments_to_check.items():
            try:
                # Ensure params is a list
                if not isinstance(params, list):
                    params = [params] if params is not None else []

                # Call the function with parameters
                result = await _call_environment_function(func_name, params)
                resource_env_attributes[func_name] = result
            except Exception as e:
                # Log error but continue with other functions
                # You might want to add proper logging here
                resource_env_attributes[func_name] = {
                    "error": f"Failed to call {func_name}: {e!s}",
                }

        if resource_env_attributes:
            environment_attributes[resource_id] = resource_env_attributes

    return environment_attributes


async def get_additional_environment_attributes_for_resources(
    resource_instances: list[Resource],
) -> list:
    """
    Retrieve and merge additional environment attributes for a list of resources.
    Args:
        resources: List of Resource instances
    Returns:
        Resources with additional environment attributes merged in
    """
    # Convert resource instances to dicts for response (exclude environments_to_check)
    resource_attributes_list = None
    if resource_instances:
        resource_attributes_list = []
        for resource in resource_instances:
            resource_dict = resource.to_dict(exclude_fields={"environments_to_check"})
            # Get types for this specific resource instance
            resource_dict["types"] = get_resource_instance_types(
                resource,
            )
            resource_attributes_list.append(resource_dict)

    # Retrieve and merge environment attributes into each resource
    if resource_instances and resource_attributes_list:
        environment_attributes = await get_additional_environment_attributes(
            resources=resource_instances,
        )

        # Merge environment attributes into each resource dict
        if environment_attributes:
            # Create a list of environment attributes in the same order as resources
            env_attrs_list = []
            for idx, resource_instance in enumerate(resource_instances):
                # Try to match by id first
                resource_id = getattr(resource_instance, "id", None) or getattr(
                    resource_instance,
                    "_id",
                    None,
                )
                env_attrs = None

                if resource_id is not None:
                    # Try exact match first
                    if resource_id in environment_attributes:
                        env_attrs = environment_attributes[resource_id]
                    # Try string conversion
                    elif str(resource_id) in environment_attributes:
                        env_attrs = environment_attributes[str(resource_id)]

                # If no match by id, try by index (fallback)
                if env_attrs is None:
                    fallback_key = f"resource_{idx}"
                    if fallback_key in environment_attributes:
                        env_attrs = environment_attributes[fallback_key]

                env_attrs_list.append(env_attrs)

            # Merge environment attributes into each resource dict
            for resource_dict, env_attrs in zip(
                resource_attributes_list,
                env_attrs_list,
            ):
                if env_attrs:
                    resource_dict.update(env_attrs)
    return resource_attributes_list
