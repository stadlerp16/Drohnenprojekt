from datetime import datetime
from typing import Optional
import json
from sqlmodel import SQLModel, Field


class DroneCommandLog(SQLModel, table=True):
    __tablename__ = "command_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    # i. Zeitstempel
    timestamp: datetime = Field(default_factory=datetime.now, index=True)
    # ii. Art des Befehls (z.B. "RC_MOVE", "TAKEOFF")
    command_type: str = Field(index=True)
    # iii. Intensität/Wert (als JSON-String gespeichert)
    intensity_value: str = Field(nullable=False)

    source: str = Field(default="unknown")  # z.B. "ps5", "keyboard", "touch"

    flight_name: Optional[str] = Field(default=None)  # Hier kommt später "Flug 1" rein