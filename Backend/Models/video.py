from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Video(SQLModel, table=True):
    __tablename__ = "videos"

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(unique=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.now)

    # Optionaler Link zum Flug, falls du Video + Flugpfad doch mal koppeln willst
    flight_name: Optional[str] = Field(default=None, index=True)