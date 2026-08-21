"""Backwards-compatible shim over :mod:`app.services.messaging`.

Delivery grew beyond SMS - codes now go out over WhatsApp too - so the real
implementation lives in ``messaging``. This module stays so that existing
imports of ``services.sms`` keep working.
"""

from __future__ import annotations

from app.services.messaging import DeliveryResult, send_otp  # noqa: F401

__all__ = ["DeliveryResult", "send_otp"]
