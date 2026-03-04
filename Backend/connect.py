import json
from sqlmodel import create_engine, SQLModel, Session
from Models.commands import DroneCommandLog  # Importiert dein Model

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