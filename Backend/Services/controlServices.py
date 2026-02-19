import asyncio
from Services.flightExekutor import control_loop, stop_all, toggle_takeoff_land

class ControlSession:
    def __init__(self, hz: int = 20):
        self.hz = hz
        self.stop_event = asyncio.Event()
        self.loop_task = None

    async def start(self):
        self.loop_task = asyncio.create_task(control_loop(self.stop_event, hz=self.hz))

    async def stop(self):
        # sofort stoppen, dann Loop beenden
        stop_all()
        self.stop_event.set()
        if self.loop_task:
            await self.loop_task
        stop_all()

    async def takeoff_land(self) -> bool:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, toggle_takeoff_land)
