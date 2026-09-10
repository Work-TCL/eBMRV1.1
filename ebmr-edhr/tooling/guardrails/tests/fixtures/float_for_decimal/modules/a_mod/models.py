from decimal import Decimal

from sqlalchemy import Float, Numeric
from sqlalchemy.orm import Mapped, mapped_column


class Thing(Base):
    id: Mapped[str] = mapped_column(primary_key=True)
    # violation: DB type is Numeric (exact decimal) but the Python annotation says float -- SQLAlchemy
    # hands the app a lossy binary float on every read.
    quantity: Mapped[float | None] = mapped_column(Numeric(18, 6))
    # allowed: correctly typed.
    weight: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    # allowed: float column backed by a float DB type, not a Numeric/DECIMAL one -- not this check's
    # concern (a non-regulated-quantity float column is fine; only the Numeric/float mismatch is flagged).
    confidence_score: Mapped[float] = mapped_column(Float)
