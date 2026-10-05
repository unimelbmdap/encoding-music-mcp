import inspect
from functools import wraps
from typing import Any, Callable

from fastmcp.server.sessions import SessionId



def expose_session_id(
        function: Callable[..., Any],
        )  -> Callable[..., Any]:
    """Expose session_id in the MCP schema without passing it to the function."""

    signature = inspect.signature(function) #params + return type

    # Check if the function already has a session_id parameter
    if "session_id" in signature.parameters:
        raise TypeError(f"{function.__name__} already defines session_id")

    #define a new parameter for session_id to be added to the function's signature
    session_parameter = inspect.Parameter(
        name="session_id",
        kind=inspect.Parameter.KEYWORD_ONLY,
        annotation=SessionId,
    )

    # retreive the existing parameters and insert the new session_id parameter at the appropriate position
    parameters = list(signature.parameters.values())
    insert_at = next(
        (
            index
            for index, parameter in enumerate(parameters)
            if parameter.kind is inspect.Parameter.VAR_KEYWORD
        ),
        len(parameters),
    )
    parameters.insert(insert_at, session_parameter)
    exposed_signature = signature.replace(parameters=parameters)

    # Create a wrapper function that removes session_id from kwargs before calling the original function
    if inspect.iscoroutinefunction(function): 

        @wraps(function) #copies metadata from original function to wrapper
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            #remove session_id from kwargs before calling the original function
            kwargs.pop("session_id", None)
            return await function(*args, **kwargs)

        wrapper = async_wrapper
    else:
        @wraps(function)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            kwargs.pop("session_id", None)
            return function(*args, **kwargs)

        wrapper = sync_wrapper

    # FastMCP inspects this signature when generating the tool schema.
    wrapper.__signature__ = exposed_signature  
    return wrapper