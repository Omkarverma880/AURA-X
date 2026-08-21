"""Shared schema building blocks."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer

T = TypeVar("T")


def _to_money(value: object) -> object:
    """Accept ints, floats and strings but settle on an exact 2dp Decimal.

    Money arriving as a JSON float is quantised immediately, so nothing further
    down the stack ever performs binary floating-point arithmetic on rupees.
    """
    if value is None or isinstance(value, Decimal):
        return value
    if isinstance(value, (int, str)):
        return Decimal(str(value))
    if isinstance(value, float):
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return value


#: Money on the wire. Exact Decimal in Python, plain JSON number for the client
#: (rupee amounts stay far inside the range JavaScript represents exactly).
Money = Annotated[
    Decimal,
    BeforeValidator(_to_money),
    PlainSerializer(lambda v: float(v) if v is not None else None, return_type=float, when_used="json"),
]

#: Money that may legitimately be absent, e.g. masked while financially locked.
OptionalMoney = Annotated[
    Decimal | None,
    BeforeValidator(_to_money),
    PlainSerializer(
        lambda v: float(v) if v is not None else None, return_type=float | None, when_used="json"
    ),
]

Percent = Annotated[
    Decimal,
    BeforeValidator(_to_money),
    PlainSerializer(lambda v: float(v) if v is not None else None, return_type=float, when_used="json"),
]

OptionalPercent = Annotated[
    Decimal | None,
    BeforeValidator(_to_money),
    PlainSerializer(
        lambda v: float(v) if v is not None else None, return_type=float | None, when_used="json"
    ),
]

Units = Annotated[
    Decimal,
    PlainSerializer(lambda v: float(v) if v is not None else None, return_type=float, when_used="json"),
]

PositiveMoney = Annotated[Money, Field(gt=0)]
NonNegativeMoney = Annotated[Money, Field(ge=0)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return max((self.total + self.page_size - 1) // self.page_size, 1)


class MessageResponse(BaseModel):
    message: str
    ok: bool = True


class IdResponse(BaseModel):
    id: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: object | None = None


class ErrorResponse(BaseModel):
    """The single error envelope every failing endpoint returns."""

    error: ErrorBody
