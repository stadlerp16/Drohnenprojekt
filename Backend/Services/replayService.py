import asyncio
import json
import Services.drohneService as ds
from Services.keyboardSteuerung import set_key
from Services.input_ps5 import set_gamepad
from Services.input_touch import set_touch
from Services.flightExekutor import set_rc
from Services.controlServices import ControlSession  # DER ENTSCHEIDENDE IMPORT
from connect import get_commands_by_name

# Globaler Tracker für die aktive Replay-Aufgabe
active_replay_task = None


async def play_flight(flight_name: str):
    """
    Lädt eine Flugroute aus der DB und spielt sie in Echtzeit ab,
    indem eine eigene ControlSession für den Hardware-Stream genutzt wird.
    """
    global active_replay_task

    # 1. Daten laden
    commands = get_commands_by_name(flight_name)
    if not commands:
        print(f"Fehler: Flug '{flight_name}' nicht gefunden.")
        return

    # 2. Hardware-Session starten (20Hz Loop für set_rc)
    session = ControlSession(hz=20)
    await session.start()

    print(f"--- REPLAY START: {flight_name} ({len(commands)} Befehle) ---")

    try:
        # Erster Zeitstempel als Referenz für das Timing
        last_time = commands[0].timestamp

        for cmd in commands:
            # Timing berechnen und warten
            wait_time = (cmd.timestamp - last_time).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)

            try:
                # Daten-Parsing
                val = cmd.intensity_value
                if (cmd.command_type in ["PS5_MOVE", "TOUCH_MOVE"]) and isinstance(val, str):
                    val = json.loads(val)

                # Befehl in den Speicher schreiben (ControlSession sendet diese dann)
                if cmd.command_type == "KEYBOARD_MOVE":
                    set_key(val, True)

                elif cmd.command_type == "PS5_MOVE":
                    set_gamepad(**val)

                elif cmd.command_type == "TOUCH_MOVE":
                    set_touch(**val)

                elif cmd.command_type == "FLIGHT_EVENT":
                    if val == "takeoff":
                        await ds.ep_drone.takeoff().wait_for_completed()
                    elif val == "land":
                        await ds.ep_drone.land().wait_for_completed()

            except Exception as e:
                print(f"Fehler bei Befehl-Ausführung: {e}")

            last_time = cmd.timestamp

        # Kurze Pause nach dem letzten Befehl, damit die Bewegung ankommt
        await asyncio.sleep(0.5)

        # Sicherheit: Alle Steuerwerte auf 0 setzen
        set_rc(0, 0, 0, 0)
        print(f"--- REPLAY ERFOLGREICH BEENDET: {flight_name} ---")

    except asyncio.CancelledError:
        print(f"--- REPLAY MANUELL ABGEBROCHEN: {flight_name} ---")
        stop_drone_immediately()
        raise
    finally:
        # 3. Hardware-Session stoppen und Task leeren
        await session.stop()
        active_replay_task = None


def stop_drone_immediately():
    """
    Not-Aus: Stoppt Replay-Werte und erzwingt Landung.
    """
    print("!!! EMERGENCY STOP AKTIVIERT !!!")
    set_rc(0, 0, 0, 0)

    if ds.ep_drone:
        # Landen als separate Task starten
        asyncio.create_task(ds.ep_drone.land().wait_for_completed())