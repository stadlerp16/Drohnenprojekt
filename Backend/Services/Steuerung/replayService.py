import asyncio
import json
import Services.DrohneVerwaltung.drohneService as ds
from Services.Steuerung.keyboardSteuerung import set_key
from Services.Steuerung.input_ps5 import set_gamepad
from Services.Steuerung.input_touch import set_touch
from Services.Steuerung.flightExekutor import set_rc
from Services.Steuerung.controlServices import ControlSession
from connect import get_commands_by_name

active_replay_task = None

async def play_key_duration(key: str, duration: float):
    """Drückt die Taste, wartet die Dauer und lässt sie los."""
    set_key(key, True)
    await asyncio.sleep(duration)
    set_key(key, False)
    print(f"[REPLAY] ⌨️ Taste {key} nach {duration}s losgelassen")

async def play_flight(flight_name: str):
    global active_replay_task
    commands = get_commands_by_name(flight_name)
    if not commands:
        print(f"[REPLAY] ❌ Fehler: Flug '{flight_name}' nicht gefunden.")
        return

    session = ControlSession(hz=20)
    await session.start()
    print(f"[REPLAY] 🛫 START: {flight_name} | {len(commands)} Befehle")

    try:
        last_time = commands[0].timestamp
        for i, cmd in enumerate(commands):
            wait_time = (cmd.timestamp - last_time).total_seconds()
            if wait_time > 0: await asyncio.sleep(wait_time)

            try:
                val = cmd.intensity_value
                if isinstance(val, str): val = val.strip('"').replace('\\"', '"')

                if cmd.command_type == "KEYBOARD_DURATION":
                    data = json.loads(val)
                    # Task starten, damit die Loop nicht blockiert
                    asyncio.create_task(play_key_duration(data["key"], data["duration"]))

                elif cmd.command_type in ["PS5_MOVE", "TOUCH_MOVE"]:
                    d = json.loads(val) if isinstance(val, str) else val
                    if cmd.command_type == "PS5_MOVE": set_gamepad(**d)
                    else: set_touch(**d)

                elif cmd.command_type == "FLIGHT_EVENT":
                    print(f"[REPLAY] 🚀 EVENT: {val}")
                    await session.takeoff_land()
                    if i == 0: await asyncio.sleep(4.0)

            except Exception as e:
                print(f"[REPLAY] ❌ Fehler bei Befehl {i}: {e}")
            last_time = cmd.timestamp

        await asyncio.sleep(2.0) # Warten auf letzte Tasks
        set_rc(0, 0, 0, 0)
        print(f"[REPLAY] ✅ BEENDET")
    except asyncio.CancelledError: stop_drone_immediately()
    finally:
        await session.stop()
        active_replay_task = None

def stop_drone_immediately():
    set_rc(0, 0, 0, 0)
    if ds.ep_drone: asyncio.create_task(ds.ep_drone.land().wait_for_completed())