from robomaster import robot

drone = robot.Drone()
drone.initialize()

drone.config_sta("MeineS", "htl12345")
drone.close()