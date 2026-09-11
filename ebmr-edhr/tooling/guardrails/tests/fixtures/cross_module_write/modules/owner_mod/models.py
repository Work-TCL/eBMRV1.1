from sqlalchemy.orm import Mapped, mapped_column


class OwnedThing(Base):
    id: Mapped[str] = mapped_column(primary_key=True)
