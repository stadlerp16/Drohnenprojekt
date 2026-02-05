from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session
from pydantic import validator, IPvAnyAddress

class Drohne(SQLModel, table=True):
    __tablename__ = "drohnen"

    # Primärschlüssel (wird von MariaDB automatisch hochgezählt)
    id: Optional[int] = Field(default=None, primary_key=True)

    # Name der Drohne
    name: str = Field(index=True, max_length=100)

    # IP-Adresse (als String in der DB, aber Pydantic prüft das Format)
    ip_adresse: str = Field(unique=True, nullable=False)

    # Status (z.B. "online", "offline", "wartung")
    status: str = Field(default="offline")

    # Pydantic-Validator: Prüft, ob die IP-Adresse gültig ist
    @validator("ip_adresse")
    def check_ip_format(cls, v):
        # Versucht, den String als IP zu interpretieren
        IPvAnyAddress(v)
        return v

    def __repr__(self):
        return f"Drohne(name={self.name}, ip={self.ip_adresse}, status={self.status})"