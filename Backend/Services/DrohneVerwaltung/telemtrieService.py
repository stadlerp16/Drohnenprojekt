import math
import Services.DrohneVerwaltung.drohneService as drohne_service


def get_telemetry() -> dict:
    drone = drohne_service.ep_drone
    current_drone_ip = drohne_service.current_drone_ip

    if drone is None:
        return {
            "connected": False,
            "ip": None,
            "battery": None,
            "height": None,
            "speed": None,
            "pitch": None,
            "roll": None,
            "yaw": None,
            "error": "Keine Drohne verbunden"
        }

    def safe_status(name: str, default=None):
        try:
            return drone.get_status(name=name)
        except Exception as e:
            print(f"[Telemetry] Fehler bei {name}: {e}")
            return default

    battery = safe_status("bat")
    height = safe_status("h")

    pitch = safe_status("pitch")
    roll = safe_status("roll")
    yaw = safe_status("yaw")

    vgx = safe_status("vgx", 0)
    vgy = safe_status("vgy", 0)
    vgz = safe_status("vgz", 0)

    try:
        speed = round(math.sqrt((vgx or 0) ** 2 + (vgy or 0) ** 2 + (vgz or 0) ** 2), 2)
    except Exception:
        speed = None

    return {
        "connected": True,
        "ip": current_drone_ip,
        "battery": battery,
        "height": height,
        "speed": speed,
        "pitch": pitch,
        "roll": roll,
        "yaw": yaw,
        "vgx": vgx,
        "vgy": vgy,
        "vgz": vgz
    }

