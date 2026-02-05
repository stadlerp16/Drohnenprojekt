import robomaster
from robomaster import robot

ep_drone = None

def buildconnection(drone_ip: str) -> bool:
    global ep_drone
    close()

    try:
        robomaster.config.ROBOT_IP_STR = drone_ip

        ep_drone = robot.Drone()
        ok = ep_drone.initialize(conn_type="sta")
        if not ok:
            close()
            return False

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
