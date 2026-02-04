import robomaster
from robomaster import robot

ep_drone = None

def buildconnection(ip: str) -> bool:
    global ep_drone
    print(ip)
    close()

    try:
        # ...
        ep_drone = robot.Drone()
        ok = ep_drone.initialize()
        if not ok:
            return False

        battery = ep_drone.battery.get_battery()
        print(f"OK, Batterie: {battery}%")
        return True

    except Exception as e:
        print(f"Verbindungsfehler: {e}")
        close()
        return False


def close():
    global ep_drone
    if ep_drone is not None:
        try:
            ep_drone.close()
        except Exception:
            pass
        finally:
            ep_drone = None

