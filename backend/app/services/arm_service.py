"""
arm_service.py
--------------
Dedicated service for managing robotic arm sequences and serial communication.
"""

import asyncio
import threading
from typing import List
from app.services.serial_service import serial_service
from app.core.logger import AppLogger
from app.core.events import event_bus

# Resting pose — held whenever the arm is idle
REST_POSE = [90, 90, 90, 81, 145, 90]

# Sequence Definitions
SORT_A_SEQUENCE = [
    [90, 90, 90, 81, 145, 90],
    [90, 90, 90, 80, 128, 90],
    [90, 90, 90, 123, 128, 90],
    [90, 15, 90, 123, 128, 90],
    [0, 15, 90, 125, 128, 90],
    [0, 64, 90, 125, 128, 90],
    [0, 64, 90, 125, 153, 90],
    [0, 64, 90, 100, 153, 90],
    [0, 64, 90, 100, 153, 40],
    [0, 64, 90, 100, 122, 40],
    [0, 64, 90, 121, 122, 40],
    [90, 64, 90, 121, 122, 40],
    [90, 64, 90, 85, 122, 40],
    [90, 65, 90, 85, 144, 40],
    [90, 65, 90, 85, 144, 90]

]

SORT_B_SEQUENCE = [
 [90, 90, 90, 81, 145, 90],
    [90, 90, 90, 80, 128, 90],
    [90, 90, 90, 123, 128, 90],
    [90, 15, 90, 123, 128, 90],
    [0, 15, 90, 125, 128, 90],
    [0, 64, 90, 125, 128, 90],
    [0, 64, 90, 125, 153, 90],
    [0, 64, 90, 100, 153, 90],
    [0, 64, 90, 100, 153, 132],
    [0, 64, 90, 100, 122, 132],
    [0, 64, 90, 121, 122, 132],
    [90, 64, 90, 121, 122, 132],
    [90, 64, 90, 85, 122, 132],
    [90, 65, 90, 85, 144, 132],
    [90, 65, 90, 85, 144, 90]
]

class ArmService:
    def __init__(self):
        self._is_busy = False
        self._lock = threading.Lock()

    @property
    def is_busy(self) -> bool:
        with self._lock:
            return self._is_busy

    def go_to_rest(self):
        """Immediately moves the arm to the resting position (non-blocking, Thread-safe)."""
        loop = event_bus.get_loop()
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self._execute_rest_async(), loop)
        else:
            AppLogger.log_sync("WARNING", "ArmService: No event loop available to send rest pose.")

    def run_sort_a(self):
        """Runs sequence for Category A (Thread-safe)"""
        self._schedule_sequence(SORT_A_SEQUENCE)

    def run_sort_b(self):
        """Runs sequence for Category B (Thread-safe)"""
        self._schedule_sequence(SORT_B_SEQUENCE)

    def trigger_reject_cooldown(self):
        """Triggers a 5-second busy state for rejected items (No arm movement)"""
        loop = event_bus.get_loop()
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self._execute_reject_cooldown_async(), loop)

    def _schedule_sequence(self, sequence: List[List[int]]):
        """Schedules a sequence to run on the main event loop from any thread"""
        loop = event_bus.get_loop()
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self._execute_sequence_async(sequence), loop)
        else:
            AppLogger.log_sync("ERROR", "ArmService: No running event loop found to schedule sequence")

    def _lerp_poses(self, from_pose: List[int], to_pose: List[int], steps: int) -> List[List[int]]:
        """Generate linearly interpolated frames between two poses (exclusive of from_pose)."""
        frames = []
        for s in range(1, steps + 1):
            t = s / steps
            frame = [round(from_pose[j] + (to_pose[j] - from_pose[j]) * t) for j in range(len(from_pose))]
            frames.append(frame)
        return frames



    async def _send_pose(self, pose: List[int]):
        """Send all servo angles for a single pose with a small serial gap between commands."""
        for i, angle in enumerate(pose):
            serial_service.send_servo_command(i + 1, angle)
            await asyncio.sleep(0.005)  # Minimal serial buffer gap

    async def _execute_sequence_async(self, sequence: List[List[int]]):
        """Internal async executor for sequences — uses linear interpolation for smooth motion."""
        with self._lock:
            if self._is_busy:
                AppLogger.log_sync("WARNING", "ArmService: Attempted to start sequence while busy.")
                return
            self._is_busy = True

        INTERP_STEPS =  12  # Intermediate frames between keyframes
        FRAME_DELAY  = 0.02  # Seconds between each interpolated frame (controls speed)

        AppLogger.log_sync("WARNING", "Robotic Arm: Sequence Started. Scanning paused.")
        serial_service.send_command("STOP")
        try:
            # Move to the first keyframe
            await self._send_pose(sequence[0])
            await asyncio.sleep(1.0)  # Settle at start pose

            # Smoothly interpolate from each keyframe to the next
            for k in range(1, len(sequence)):
                frames = self._lerp_poses(sequence[k - 1], sequence[k], INTERP_STEPS)
                for frame in frames:
                    await self._send_pose(frame)
                    await asyncio.sleep(FRAME_DELAY)

            AppLogger.log_sync("INFO", "Robotic sequence complete")
        except Exception as e:
            AppLogger.log_sync("ERROR", f"ArmService: Sequence error: {e}")
        finally:
            with self._lock:
                self._is_busy = False
            serial_service.send_command("START")
            AppLogger.log_sync("INFO", "rescanning started...")
            # Return arm to resting position after every sort
            await self._send_pose(REST_POSE)
            AppLogger.log_sync("INFO", "Arm returned to rest pose.")

    async def _execute_reject_cooldown_async(self):
        """Internal async executor for rejection pause"""
        with self._lock:
            if self._is_busy: return
            self._is_busy = True
        
        AppLogger.log_sync("WARNING", "System: Item Rejected. 5s Cooldown active.")
        serial_service.send_command("STOP")
        try:
            await asyncio.sleep(5.0)
        finally:
            with self._lock:
                self._is_busy = False
            serial_service.send_command("START")
            AppLogger.log_sync("INFO", "rescanning started...")

    async def _execute_rest_async(self):
        """Sends the arm directly to REST_POSE without acquiring the busy lock."""
        try:
            await self._send_pose(REST_POSE)
            AppLogger.log_sync("INFO", "Arm moved to rest pose.")
        except Exception as e:
            AppLogger.log_sync("ERROR", f"ArmService: Failed to send rest pose: {e}")

# Global Instance
arm_service = ArmService()
