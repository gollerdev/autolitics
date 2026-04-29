from typing import Optional

from pydantic import BaseModel


class Seller(BaseModel):
    """Seller data extracted from a MercadoLibre listing.
    Matches the ML source field names where possible."""

    # Identity
    id: int
    nickname: str
    permalink: str
    registration_date: str  # ISO timestamp

    # Type flags
    car_dealer: bool
    real_estate_agency: bool

    # Reputation
    level_id: Optional[str] = None

    # Lifetime transactions
    transactions_total: int
    transactions_completed: int
    transactions_canceled: int
    transactions_period: str  # always "historic" so far, kept for fidelity
    ratings_positive: float
    ratings_neutral: float
    ratings_negative: float

    # Recent sales
    sales_completed: int
    sales_period_days: Optional[int] = None  # parsed: "365 days" -> 365, "60 months" -> 1825