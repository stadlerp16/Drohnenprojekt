from robomaster import robot

drone = robot.Drone()
drone.initialize()

drone.config_sta("Samsung", "htl12345")
drone.close()