"""Portable column types.

The production database is PostgreSQL; the test-suite runs on SQLite so the
whole suite can execute without a server. These types render natively on
PostgreSQL (UUID, NUMERIC, JSONB) and fall back to portable equivalents
elsewhere, so model code never has to care which engine is in use.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import JSON, Numeric, Uuid
from sqlalchemy.dialects.postgresql import JSONB

#: Primary/foreign key type - native ``uuid`` on PostgreSQL, CHAR(32) elsewhere.
GUID = Uuid(as_uuid=True)

#: JSON payloads - ``jsonb`` on PostgreSQL (indexable), ``json`` elsewhere.
JSONType = JSON().with_variant(JSONB, "postgresql")

#: Money. NEVER float. 18 digits with 2 decimal places covers any personal
#: balance sheet while staying exact under addition and comparison.
MONEY_PRECISION = 18
MONEY_SCALE = 2
Money = Numeric(MONEY_PRECISION, MONEY_SCALE, asdecimal=True)

#: Quantities (mutual-fund units, crypto) need far more decimal places.
Quantity = Numeric(28, 8, asdecimal=True)

#: Percentages / rates stored with 4 decimal places (e.g. 12.5000).
Rate = Numeric(9, 4, asdecimal=True)

ZERO = Decimal("0.00")
