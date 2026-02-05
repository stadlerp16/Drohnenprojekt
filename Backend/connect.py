from robomaster import robot

drone = robot.Drone()
drone.initialize()

drone.config_sta("htljoh-nwt", "nwt5600htl")
drone.close()