from typing import Any, Generic, TypeVar

from pydantic import BaseModel


class ToolError(BaseModel):
    code: str
    message: str


ResultT = TypeVar("ResultT")


class ToolResponse(BaseModel, Generic[ResultT]):
    success: bool
    data: ResultT | None = None
    error: ToolError | None = None

    @classmethod
    def ok(cls, data: ResultT) -> "ToolResponse[ResultT]":
        return cls(success=True, data=data)

    @classmethod
    def failure(cls, code: str, message: str) -> "ToolResponse[Any]":
        return cls(success=False, error=ToolError(code=code, message=message))
