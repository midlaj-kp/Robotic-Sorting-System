import asyncio
from typing import Dict, List, Any

class EventManager:
    """ Simple async pub/sub bus for decoupled components """
    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._main_loop: asyncio.AbstractEventLoop | None = None
        self._central_queue = asyncio.Queue()

    def register_loop(self, loop: asyncio.AbstractEventLoop):
        self._main_loop = loop

    def get_loop(self) -> asyncio.AbstractEventLoop | None:
        return self._main_loop

    def subscribe(self, event_type: str) -> asyncio.Queue:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        queue = asyncio.Queue()
        self._subscribers[event_type].append(queue)
        return queue

    def unsubscribe(self, event_type: str, queue: asyncio.Queue):
        if event_type in self._subscribers:
            if queue in self._subscribers[event_type]:
                self._subscribers[event_type].remove(queue)

    async def publish(self, event_type: str, data: Any):
        event_payload = {"event": event_type, "data": data}
        # Put the event in the central queue for the websocket listener
        await self._central_queue.put(event_payload)
        
        if event_type in self._subscribers:
            # Create tasks to put items in all topic-specific subscriber queues
            for queue in self._subscribers[event_type]:
                await queue.put(event_payload)

    def publish_threadsafe(self, event_type: str, data: Any):
        """For publishing events from a different thread."""
        if self._main_loop:
            asyncio.run_coroutine_threadsafe(self.publish(event_type, data), self._main_loop)

    async def get(self):
        """Get an event from the central queue."""
        return await self._central_queue.get()

# Global event bus instance
event_bus = EventManager()
