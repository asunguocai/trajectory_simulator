from abc import ABC, abstractmethod
from typing import Dict
from shapely.geometry import Point

class TrajectoryObserver(ABC):
    """轨迹观察者抽象基类"""

    
    def on_start_recording(self):
        pass

    
    def on_stop_recording(self):
        pass

    
    def on_pause_recording(self):
        pass

    
    def on_resume_recording(self):
        pass

    
    def on_data_update(self, data: Dict):
        pass
    
    
    def on_time_changed(self, new_time: float):
        pass

    
    def on_position_changed(self, new_position: Point):
        pass

    
    def on_simulation_attempt(self, data: Dict):
        pass

    
    def on_simulation_retry(self, data: Dict):
        pass

    
    def on_simulation_success(self, data: Dict):
        pass

    
    def on_simulation_failure(self, data: Dict):
        pass