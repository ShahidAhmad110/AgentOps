from uuid import UUID

from pydantic import BaseModel


class ToolContext(BaseModel):
    """Identity supplied by the authenticated agent request boundary."""

    user_id: UUID
    organization_id: UUID | None = None
    is_authenticated: bool = True

    def require_authenticated(self) -> None:
        if not self.is_authenticated:
            raise PermissionError("Authentication is required to execute MCP tools.")
