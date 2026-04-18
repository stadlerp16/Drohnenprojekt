import asyncio
import json
import time
from datetime import datetime
from Services.Steuerung.replayService import play_flight
from connect import log_command, get_commands_by_name, label_flight


async def run_diagnostics(flight_name: str):
    print("=" * 50)
    print(f"🔍 FINALE DIAGNOSE: {flight_name}")
    print("=" * 50)

    # STEP 0: Testdaten erzeugen
    print("\n[STEP 0] Erzeuge Testdaten...")
    log_command("FLIGHT_EVENT", "takeoff_land", source="diag")

    # Simuliere 'w' drücken und loslassen
    log_command("KEYBOARD_MOVE", json.dumps({"key": "w", "pressed": True}), source="diag")
    time.sleep(1)
    log_command("KEYBOARD_MOVE", json.dumps({"key": "w", "pressed": False}), source="diag")

    log_command("FLIGHT_EVENT", "takeoff_land", source="diag")

    # Alle neuen Logs auf den Testnamen labeln
    label_flight(datetime.min, datetime.max, flight_name)
    print("✅ Testdaten gespeichert.")

    # STEP 1: Datenbank-Check
    print("\n[STEP 1] DB-Format prüfen...")
    commands = get_commands_by_name(flight_name)
    for c in commands:
        if c.command_type == "KEYBOARD_MOVE":
            print(f"DB-Wert: {c.intensity_value}")  # Hier sollten die Backslashes sichtbar sein

    # STEP 2: Replay-Check (Der wichtigste Teil)
    print("\n[STEP 2] Replay startet...")
    await play_flight(flight_name)

    print("\n" + "=" * 50)
    print("DIAGNOSE BEENDET")


if __name__ == "__main__":
    test_id = f"test_{int(time.time())}"
    asyncio.run(run_diagnostics(test_id))