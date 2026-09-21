from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from mcp.schemas.context import ToolContext
from mcp.schemas.results import ToolResponse

logger = logging.getLogger(__name__)

InputT = TypeVar("InputT", bound=BaseModel)


class RegisteredTool(Generic[InputT]):
    def __init__(
        self,
        name: str,
        description: str,
        input_model: type[InputT],
        handler: Callable[[InputT, ToolContext], Awaitable[Any]],
    ) -> None:
        self.name = name
        self.description = description
        self.input_model = input_model
        self.handler = handler

    def descriptor(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
        }

    async def invoke(self, arguments: dict[str, Any], context: ToolContext) -> ToolResponse[Any]:
        try:
            context.require_authenticated()
            validated_arguments = self.input_model.model_validate(arguments)
            data = await self.handler(validated_arguments, context)
            logger.info("MCP tool completed", extra={"tool_name": self.name, "user_id": str(context.user_id)})
            return ToolResponse.ok(data)
        except ValidationError:
            logger.warning("MCP tool validation failed", extra={"tool_name": self.name})
            return ToolResponse.failure("INVALID_TOOL_INPUT", "Tool arguments failed validation.")
        except PermissionError as exc:
            logger.warning("MCP tool authorization failed", extra={"tool_name": self.name})
            return ToolResponse.failure("AUTHORIZATION_ERROR", str(exc))
        except LookupError as exc:
            logger.info("MCP tool resource not found", extra={"tool_name": self.name})
            return ToolResponse.failure("NOT_FOUND", str(exc))
        except ValueError:
            logger.warning("MCP tool domain validation failed", extra={"tool_name": self.name})
            return ToolResponse.failure("DOMAIN_VALIDATION_ERROR", "The operation failed domain validation.")
        except Exception:
            logger.exception("MCP tool failed", extra={"tool_name": self.name})
            return ToolResponse.failure("TOOL_EXECUTION_ERROR", "The MCP tool could not complete.")
