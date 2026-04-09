import os
import subprocess
import sys
import threading
import time
from typing import Optional
import math

import robomaster
from robomaster import robot

ep_drone = None
_close_lock = threading.Lock()
_restart_lock = threading.Lock()

HOST = "127.0.0.1"
PORT = 8000
watchdog_running = False
count = 0
restart_in_progress = False
current_drone_ip = None
# Nur einmal beim Start auslesen und direkt entfernen
AUTO_DRONE_IP = os.environ.pop("AUTOCONNECT_DRONE_IP", None)


def is_connected() -> bool:
    return ep_drone is not None


def restart_server(target_drone_ip: Optional[str] = None):
    global restart_in_progress

    with _restart_lock:
        if restart_in_progress:
            print("[Restart] Bereits aktiv")
            return
        restart_in_progress = True

    pid = os.getpid()

    launcher = r"""
import os
import sys
import time
import socket
import subprocess

pid = int(sys.argv[1])
host = sys.argv[2]
port = int(sys.argv[3])
target_ip = sys.argv[4]

# warten bis alter Prozess wirklich beendet ist
while True:
    try:
        os.kill(pid, 0)
        time.sleep(0.1)
    except OSError:
        break

# warten bis Port wieder frei ist
deadline = time.time() + 10.0
while True:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        s.close()
        break
    except OSError:
        s.close()
        if time.time() > deadline:
            break
        time.sleep(0.2)

cwd = os.getcwd()
env = os.environ.copy()

# Nur bei bewusstem Reconnect setzen
if target_ip != "__NONE__":
    env["AUTOCONNECT_DRONE_IP"] = target_ip
else:
    env.pop("AUTOCONNECT_DRONE_IP", None)

if os.name == "nt":
    uvicorn_cmd = subprocess.list2cmdline([
        sys.executable,
        "-m", "uvicorn",
        "main:app",
        "--host", host,
        "--port", str(port)
    ])
    subprocess.Popen(["cmd.exe", "/c", uvicorn_cmd], cwd=cwd, env=env)
else:
    subprocess.Popen([
        sys.executable,
        "-m", "uvicorn",
        "main:app",
        "--host", host,
        "--port", str(port)
    ], cwd=cwd, env=env)
"""

    kwargs = {}

    if os.name == "nt":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
        )
        kwargs["close_fds"] = True
    else:
        kwargs["start_new_session"] = True

    subprocess.Popen(
        [
            sys.executable,
            "-c",
            launcher,
            str(pid),
            HOST,
            str(PORT),
            target_drone_ip if target_drone_ip else "__NONE__"
        ],
        cwd=os.getcwd(),
        **kwargs
    )

    os._exit(0)


def delayed_restart(target_drone_ip: Optional[str] = None, delay: float = 0.5):
    def worker():
        time.sleep(delay)
        restart_server(target_drone_ip)

    threading.Thread(target=worker, daemon=True).start()


def buildconnection(drone_ip: str) -> bool:
    global ep_drone, watchdog_running, count, current_drone_ip

    print("1")

    close()
    print("2")

    new_drone = None

    try:
        robomaster.config.ROBOT_IP_STR = drone_ip

        new_drone = robot.Drone()
        ok = new_drone.initialize(conn_type="sta")
        print("3")

        if not ok:
            watchdog_running = False
            try:
                new_drone.close()
            except Exception as e:
                print(f"Cleanup nach initialize(False) fehlgeschlagen: {e}")
            return False

        ep_drone = new_drone
        current_drone_ip = drone_ip
        count = 0
        new_drone.led.set_led(r=0, g=0, b=255)
        new_drone.led.set_led_blink(freq=5, r1=0, g1=0, b1=255, r2=0, g2=0, b2=0)
        time.sleep(3)

        print("4")
        ep_drone.led.set_led(r=0, g=255, b=0)
        watchdog_running = False
        starte_watchdog()
        return True

    except Exception as e:
        print(f"Verbindungsfehler: {e}")

        try:
            if new_drone is not None:
                new_drone.close()
        except Exception as cleanup_error:
            print(f"Cleanup-Fehler: {cleanup_error}")

        ep_drone = None
        current_drone_ip = None
        watchdog_running = False
        return False


def close():
    global ep_drone, watchdog_running, current_drone_ip

    print("5")

    with _close_lock:
        if ep_drone is None:
            current_drone_ip = None
            return

        finished = threading.Event()

        def close_worker(drone_ref):
            global ep_drone, watchdog_running, current_drone_ip
            try:
                ep_drone.led.set_led(r=255, g=0, b=0)
                drone_ref.close()
                watchdog_running = False
                print("6")
            except Exception as e:
                print(f"[Close] Fehler: {e}")
            finally:
                if ep_drone is drone_ref:
                    ep_drone = None
                current_drone_ip = None
                finished.set()

        drone_ref = ep_drone
        threading.Thread(target=close_worker, args=(drone_ref,), daemon=True).start()

    if not finished.wait(timeout=5):
        print("close() hängt länger als 5 Sekunden -> restart_server()")
        restart_server()


def starte_watchdog():
    global watchdog_running, count

    if watchdog_running:
        return

    count = 0
    watchdog_running = True

    def monitor_loop():
        global watchdog_running, ep_drone, count
        print("[Monitor] Überwachung gestartet.")

        last_known_value_agx = 0
        last_known_value_agy = 0
        last_known_value_agz = 0

        try:
            while watchdog_running:
                drone = ep_drone
                if drone is None:
                    break

                time.sleep(0.5)

                current_value_agx = drone.get_status(name="agx")
                current_value_agy = drone.get_status(name="agy")
                current_value_agz = drone.get_status(name="agz")

                if (
                    last_known_value_agx != current_value_agx
                    or last_known_value_agy != current_value_agy
                    or last_known_value_agz != current_value_agz
                ):
                    print(f"[Monitor] OK: Funktion läuft {current_value_agx} {current_value_agy} {current_value_agz}")
                    count = 0
                else:
                    count += 1
                    print(f"[Monitor] Gleich geblieben: {count}x")

                    if count >= 3:
                        print(f"[Monitor] Error: Funktion Still {current_value_agx} {current_value_agy} {current_value_agz}")
                        close()
                        break

                last_known_value_agx = current_value_agx
                last_known_value_agy = current_value_agy
                last_known_value_agz = current_value_agz

        except Exception as e:
            print(f"[Monitor] Exception: {e}")

        watchdog_running = False
        print("[Monitor] Überwachung beendet.")

    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()


def test_reconnect():
    global ep_drone, watchdog_running, count
    if AUTO_DRONE_IP:
        print(f"[Startup] Auto reconnect zu {AUTO_DRONE_IP}")
        try:
            success = buildconnection(AUTO_DRONE_IP)
            print(f"[Startup] Auto reconnect Ergebnis: {success}")
        except Exception as e:
            print(f"Auto reconnect fehlgeschlagen: {e}")

