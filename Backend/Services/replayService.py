import asyncio
import json
import Services.drohneService as ds
from Services.keyboardSteuerung import set_key
from Services.input_ps5 import set_gamepad
from Services.input_touch import set_touch
from Services.flightExekutor import set_rc
from Services.controlServices import ControlSession
from connect import get_commands_by_name, get_all_flight_names

active_replay_task = None


async def play_flight(flight_name: str):
    global active_replay_task


    commands = get_commands_by_name(flight_name)
    if not commands:
        print(f"[REPLAY] ❌ Fehler: Flug '{flight_name}' nicht gefunden.")
        return

    session = ControlSession(hz=20)
    await session.start()

    print(f"[REPLAY] 🛫 START: {flight_name} | Befehle: {len(commands)}")

    try:
        last_time = commands[0].timestamp

        for i, cmd in enumerate(commands):
            wait_time = (cmd.timestamp - last_time).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)

            try:
                val = cmd.intensity_value
                if isinstance(val, str):
                    val = val.strip('"').strip("'")

                # --- AUSFÜHRUNG MIT LOGS ---
                if cmd.command_type == "KEYBOARD_MOVE":
                    # LOG HINZUGEFÜGT
                    print(f"[REPLAY] ⌨️ Taste: {val}")
                    set_key(val, True)

                elif cmd.command_type == "PS5_MOVE":
                    if isinstance(val, str): val = json.loads(val)
                    print(f"[REPLAY] 🎮 PS5: {val}")
                    set_gamepad(**val)

                elif cmd.command_type == "TOUCH_MOVE":
                    if isinstance(val, str): val = json.loads(val)
                    print(f"[REPLAY] 📱 Touch: {val}")
                    set_touch(**val)

                elif cmd.command_type == "FLIGHT_EVENT":
                    if val in ["takeoff", "land", "takeoff_land"]:
                        print(f"[REPLAY] 🚀 EVENT: {val}")
                        await session.takeoff_land()

                        # WICHTIG: Wenn es der erste Befehl ist (Takeoff),
                        # müssen wir warten, bis die Drohne in der Luft ist!
                        if i == 0:
                            print("[REPLAY] ⏳ Warte 5s auf Takeoff...")
                            await asyncio.sleep(5.0)

            except Exception as e:
                print(f"[REPLAY] ❌ Fehler bei Befehl {i}: {e}")

            last_time = cmd.timestamp

        await asyncio.sleep(0.5)
        set_rc(0, 0, 0, 0)
        print(f"[REPLAY] ✅ BEENDET: {flight_name}")

    except asyncio.CancelledError:
        print(f"[REPLAY] ⚠️ ABBRUCH.")
        stop_drone_immediately()
        raise
    finally:
        await session.stop()
        active_replay_task = None


def stop_drone_immediately():
    print("!!! EMERGENCY STOP AKTIVIERT !!!")
    set_rc(0, 0, 0, 0)
    if ds.ep_drone:
        asyncio.create_task(ds.ep_drone.land().wait_for_completed())