"""
The user's pydantic model, pasted into the consultation as the
Path 2 input.

`schema-designer` does NOT execute this file; the model is text
context for the user's intent. Path 2 parses the equivalent
JSON Schema (the pydantic v2.5+ `model_json_schema()` export)
rather than importing the model.

This file is included in the fixture so the fixture is
self-contained — a reviewer reading the fixture can see exactly
what the user brought.
"""

from pydantic import BaseModel, Field
from typing import Literal


class TicketTriage(BaseModel):
    queue: Literal["billing", "general", "abuse"] = Field(
        description="The queue the ticket routes to."
    )
    urgency: Literal["low", "normal", "high"] = Field(
        description="The ticket's urgency tier at intake."
    )
    requires_human_review: bool = Field(
        description=(
            "True when the model is below its confidence threshold "
            "for autonomous routing."
        )
    )
