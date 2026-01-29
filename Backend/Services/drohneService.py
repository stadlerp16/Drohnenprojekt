import robomaster
from robomaster import robot


def buildconnection(ip: str) -> bool:
    """
    Versucht, eine Verbindung zur Drohne über das RoboMaster-SDK aufzubauen.
    Gibt True zurück, wenn erfolgreich, sonst False.
    """

    try:

        print(ip)
        # Lokale IP setzen (wichtig für UDP)
        robomaster.config.ROBOT_IP_STR = ip

        # Roboter-Objekt erstellen
        ep_drone = robot.Drone()

        # Verbindung aufbauen (UDP / WLAN)
        if not ep_drone.initialize():
            raise ConnectionError()


        # Optional: einfacher Test, ob Verbindung steht
        battery = ep_drone.battery.get_battery()
        print(f"Verbindung erfolgreich, Batterie: {battery}%")

        return True

    except Exception as e:
        # Fehler abfangen, Verbindung fehlgeschlagen
        print(f"Verbindungsfehler zur Drohne: {e}")
        return False




