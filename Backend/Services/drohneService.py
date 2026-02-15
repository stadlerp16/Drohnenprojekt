import robomaster
from robomaster import robot

ep_drone = None

def buildconnection(drone_ip: str) -> bool:
    print("1")
    global ep_drone
    close()
    print("2")
    try:
        robomaster.config.ROBOT_IP_STR = drone_ip

        ep_drone = robot.Drone()
        ok = ep_drone.initialize(conn_type="sta")
        print("3")
        if not ok:
            close()
            return False
        print("4")
        return True

    except Exception as e:
        print(f"Verbindungsfehler: {e}")
        close()
        return False

def close():
    global ep_drone
    print("5")
    if ep_drone is not None:
        try:
            ep_drone.close()
            print("6")
        except Exception:
            pass
        finally:
            ep_drone = None
