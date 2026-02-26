import asyncio
import inspect
import json
from datetime import datetime
import Services.drohneService as ds
from Services.keyboardSteuerung import set_key
from Services.input_ps5 import set_gamepad
from connect import get_commands_by_name  # Deine DB-Funktion


async def play_flight(flight_name: str):
    commands = get_commands_by_name(flight_name)
    if not commands:
        print(f"Kein Flug unter dem Namen '{flight_name}' gefunden.")
        return

    print(f"Starte Replay von: {flight_name}")

    # Der erste Zeitstempel ist unser Referenzpunkt
    last_time = commands[0].timestamp

    for cmd in commands:
        # 1. Timing: Berechne die reale Pause zwischen den Befehlen
        wait_time = (cmd.timestamp - last_time).total_seconds()

        # Falls die Pause sinnvoll ist (z.B. > 0), warten wir
        if wait_time > 0:
            await asyncio.sleep(wait_time)

        # 2. Befehl ausführen
        try:
            if cmd.command_type == "KEYBOARD_MOVE":
                # Wir simulieren den Tastendruck
                set_key(cmd.intensity_value, True)
                # Optional: Kurz warten und Taste loslassen, falls nötig
                # await asyncio.sleep(0.05)
                # set_key(cmd.intensity_value, False)


            elif cmd.command_type == "PS5_MOVE":

                coords = json.loads(cmd.intensity_value)

                # Wir filtern die Koordinaten, damit nur geschickt wird, was set_gamepad kennt

                sig = inspect.signature(set_gamepad)

                filtered_coords = {k: v for k, v in coords.items() if k in sig.parameters}

                set_gamepad(**filtered_coords)


            elif cmd.command_type == "TOUCH_MOVE":

                coords = json.loads(cmd.intensity_value)

                # Hier rufen wir set_touch auf (nicht set_gamepad!)

                # Falls set_touch ry akzeptiert, funktioniert es jetzt

                from Services.input_touch import set_touch

                sig = inspect.signature(set_touch)

                filtered_coords = {k: v for k, v in coords.items() if k in sig.parameters}

                set_touch(**filtered_coords)

            elif cmd.command_type == "FLIGHT_EVENT":
                if cmd.intensity_value == "takeoff":
                    await ds.ep_drone.takeoff().wait_for_completed()
                elif cmd.intensity_value == "land":
                    await ds.ep_drone.land().wait_for_completed()

        except Exception as e:
            print(f"Fehler beim Replay-Befehl: {e}")
            break  # Bei Fehlern lieber abbrechen

        last_time = cmd.timestamp

    print(f"Replay von '{flight_name}' erfolgreich beendet.")