"""
Query API Request Schema Definition

Declares the Pydantic data structures for incoming API queries,
enabling schema validation, typing, and OpenAPI documentation.
"""

from pydantic import BaseModel, Field


class QuerySchema(BaseModel):
    """Request payload containing the natural language database query."""

    query: str = Field(
        ...,
        description="Natural language question, e.g. 'Show top 5 products by sales'",
        examples=["Show the top 5 products with highest sales this month"],
    )
