import asyncio
from connect import init_db, log_command


def test_db():
    print("Initialisiere DB...")
    init_db()

    print("Sende Test-Befehle...")
    # Simuliere verschiedene Steuerungen
    log_command("KEYBOARD_MOVE", "w", source="keyboard")
    log_command("PS5_MOVE", {"lx": 0.8, "ly": -0.2}, source="ps5")
    log_command("FLIGHT_EVENT", "takeoff", source="touch")

    print("Fertig! Schau jetzt in deine MariaDB (DBeaver/HeidiSQL).")


if __name__ == "__main__":
    test_db()