import datetime
import time
import json
import asyncio
from connect import log_command, label_flight, get_all_flight_names
from Services.replayService import play_flight


async def simulate_flight(mode: str):
    """
    Simuliert einen Flug für einen spezifischen Modus.
    mode: 'keyboard', 'ps5' oder 'touch'
    """
    print(f"\n--- Starte Simulation für Modus: {mode.upper()} ---")

    # 1. Startzeitpunkt mit Puffer
    start_zeit = datetime.datetime.now() - datetime.timedelta(seconds=1)

    # 2. Befehle je nach Modus loggen
    if mode == "keyboard":
        log_command("FLIGHT_EVENT", "takeoff", source="keyboard")
        time.sleep(0.5)
        log_command("KEYBOARD_MOVE", "w", source="keyboard")
        time.sleep(0.5)
        log_command("FLIGHT_EVENT", "land", source="keyboard")


    elif mode == "ps5":

        log_command("FLIGHT_EVENT", "takeoff", source="ps5")

        time.sleep(0.5)

        # Sende alle Standard-Werte mit, damit set_gamepad zufrieden ist

        ps5_coords = {

            "lx": 0.0, "ly": 1.0, "rx": 0.0,

            "l2": 0.0, "r2": 0.0  # Jetzt sind l2 und r2 dabei!

        }

        log_command("PS5_MOVE", ps5_coords, source="ps5")

        time.sleep(0.5)

        log_command("FLIGHT_EVENT", "land", source="ps5")
    elif mode == "touch":
        log_command("FLIGHT_EVENT", "takeoff", source="touch")
        time.sleep(0.5)
        # Touch (Joystick) sendet ebenfalls Koordinaten
        log_command("TOUCH_MOVE", {"lx": 0.5, "ly": 0.5, "rx": 0.0, "ry": 0.0}, source="touch")
        time.sleep(0.5)
        log_command("FLIGHT_EVENT", "land", source="touch")

    # 3. Endzeitpunkt
    end_zeit = datetime.datetime.now() + datetime.timedelta(seconds=1)

    # 4. Flug benennen
    flug_name = f"Test_{mode}_{datetime.datetime.now().strftime('%H%M%S')}"
    print(f"Speichere '{mode}'-Flug unter: {flug_name}")
    label_flight(start_zeit, end_zeit, flug_name)

    return flug_name


async def run_ordered_tests():
    # Wir testen die Modi nacheinander
    for mode in ["keyboard", "ps5", "touch"]:
        name = await simulate_flight(mode)

        print(f"Prüfe Replay für {name}...")
        await play_flight(name)

        print(f"--- Modus {mode} erfolgreich abgeschlossen ---")

    # Am Ende die Liste aller Flüge ausgeben
    print("\n--- Finale Flugliste in der DB ---")
    fluege = get_all_flight_names()
    print(fluege)


if __name__ == "__main__":
    try:
        asyncio.run(run_ordered_tests())
    except KeyboardInterrupt:
        print("\nTest unterbrochen.")