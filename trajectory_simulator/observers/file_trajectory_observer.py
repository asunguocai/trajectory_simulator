from .trajectory_observer import TrajectoryObserver
from typing import Dict
from shapely.geometry import Point

class FileTrajectoryObserver(TrajectoryObserver):
    """将轨迹保存到文件的观察者"""

    def __init__(self, filename: str):
        self.filename = filename
        with open(self.filename, 'w') as f:
            f.write("event,x,y,altitude,timestamp,heading,accuracy\n")

    def on_start_recording(self):
        self._write_event("start_recording")

    def on_stop_recording(self):
        self._write_event("stop_recording")

    def on_pause_recording(self):
        self._write_event("pause_recording")

    def on_resume_recording(self):
        self._write_event("resume_recording")

    def on_data_update(self, data: Dict):
        position = data['position']
        self._write_event("update", position.x, position.y, data['altitude'], data['timestamp'], data['heading'], data['accuracy'])

    def on_time_changed(self, new_time: float):
        self._write_event("time_changed", timestamp=new_time)

    def on_position_changed(self, new_position: Point):
        self._write_event("position_changed", x=new_position.x, y=new_position.y)

    def on_simulation_attempt(self, data: Dict):
        self._write_event("simulation_attempt", attempt=data['attempt'], max_attempts=data['max_attempts'])

    def on_simulation_retry(self, data: Dict):
        self._write_event("simulation_retry", attempt=data['attempt'], max_attempts=data['max_attempts'])

    def on_simulation_success(self, data: Dict):
        self._write_event("simulation_success", attempt=data['attempt'])

    def on_simulation_failure(self, data: Dict):
        self._write_event("simulation_failure", max_attempts=data['max_attempts'])

    def _write_event(self, event: str, x: float = None, y: float = None, altitude: float = None, timestamp: float = None, heading: float = None, accuracy: float = None, attempt: int = None, max_attempts: int = None):
        with open(self.filename, 'a') as f:
            f.write(f"{event},{x},{y},{altitude},{timestamp},{heading},{accuracy},{attempt},{max_attempts}\n")