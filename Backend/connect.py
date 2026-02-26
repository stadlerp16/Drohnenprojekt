import json
from sqlmodel import create_engine, SQLModel, Session
from Models.commands import DroneCommandLog  # Importiert dein Model
from sqlmodel import select, Session, func
from Models.commands import DroneCommandLog

# Verbindung zu MariaDB (Werte müssen mit docker-compose.yml übereinstimmen)
# Format: mysql+mysqlconnector://USER:PASSWORD@HOST:PORT/DATABASE
DB_URL = "mysql+mysqlconnector://root:drohnenprojekt@localhost:3306/drohnen_db"

engine = create_engine(DB_URL)

def init_db():
    """Erstellt die Tabellen in der MariaDB, falls sie noch nicht existieren."""
    # Das nutzt die DroneCommandLog Klasse aus Models/commands.py
    SQLModel.metadata.create_all(engine)
    print("MariaDB Tabellen wurden erfolgreich initialisiert.")

def log_command(cmd_type: str, value: any, source: str):
    try:
        with Session(engine) as session:
            new_log = DroneCommandLog(
                command_type=cmd_type,
                intensity_value=json.dumps(value),
                source=source
            )
            session.add(new_log)
            session.commit()
    except Exception as e:
        # Verhindert, dass die Steuerung bei DB-Fehlern hängen bleibt
        print(f"Fehler beim Speichern in MariaDB: {e}")


from connect import init_db, log_command

try:
    print("Teste Initialisierung...")
    init_db()
    print("Initialisierung OK.")

    print("Teste Log-Eintrag...")
    log_command("TEST", {"status": "erfolgreich"}, source="test_script")
    print("Speichern OK.")
except Exception as e:
    print(f"Fehler aufgetreten: {e}")

from sqlmodel import select

def label_flight(start_time, end_time, label):
    with Session(engine) as session:
        # Finde alle Logs zwischen Start und Ende
        statement = select(DroneCommandLog).where(
            DroneCommandLog.timestamp >= start_time,
            DroneCommandLog.timestamp <= end_time
        )
        results = session.exec(statement).all()

        for log in results:
            log.flight_name = label  # Namen zuweisen
            session.add(log)

        session.commit()

def get_all_flight_names():
    with Session(engine) as session:
        # Wir wählen nur die Spalte flight_name aus und filtern Duplikate sowie NULL-Werte aus
        statement = select(DroneCommandLog.flight_name).where(
            DroneCommandLog.flight_name != None
        ).distinct()
        results = session.exec(statement).all()
        return results

def get_commands_by_name(flight_name: str):
    with Session(engine) as session:
        statement = select(DroneCommandLog).where(
            DroneCommandLog.flight_name == flight_name
        ).order_by(DroneCommandLog.timestamp) # Chronologische Reihenfolge!
        return session.exec(statement).all()
