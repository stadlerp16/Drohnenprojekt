import asyncio
import json
from datetime import datetime
from Services.replayService import play_flight
from Services.input_ps5 import set_gamepad
from connect import log_command, get_commands_by_name

async def run_diagnostics(flight_name: str):
    print("=" * 50)
    print(f"🔍 DIAGNOSE-TEST FÜR FLUG: {flight_name}")
    print("=" * 50)

    # 1. LIVE-EINGABE SIMULIEREN (Was passiert normalerweise?)
    print("\n[STEP 1] Simuliere LIVE-Eingabe (Controller)...")
    test_coords = {"lx": 0.5, "ly": -0.5, "rx": 0.0, "l2": 0.0, "r2": 1.0}
    print(f"Sende an set_gamepad: {test_coords}")
    # Hier rufen wir die Funktion direkt auf
    set_gamepad(**test_coords)
    print("✅ Live-Simulation abgeschlossen.")

    print("-" * 30)

    # 2. DATENBANK-CHECK
    print("[STEP 2] Lese Befehle aus der Datenbank...")
    commands = get_commands_by_name(flight_name)

    if not commands:
        print(f"❌ FEHLER: Kein Flug mit Name '{flight_name}' gefunden!")
        return

    print(f"Gefunden: {len(commands)} Befehle.")
    sample = commands[0]
    print(f"Beispiel-Befehl aus DB: Typ={sample.command_type}, Wert={sample.intensity_value}")

    print("-" * 30)

    # 3. REPLAY STARTEN & WERTE VERGLEICHEN
    print("[STEP 3] Starte Replay-Prozess...")
    print("Achte jetzt auf die Terminal-Ausgabe von 'set_rc'!")

    try:
        # Wir starten das echte Replay
        await play_flight(flight_name)
    except Exception as e:
        print(f"❌ Fehler während des Replays: {e}")

    print("\n" + "=" * 50)
    print("DIAGNOSE BEENDET")
    print("=" * 50)


if __name__ == "__main__":
    # Ersetze 'MeinTestFlug' mit einem echten Namen aus deiner DB
    asyncio.run(run_diagnostics("test"))