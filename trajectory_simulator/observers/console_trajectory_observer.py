from .trajectory_observer import TrajectoryObserver
from typing import Dict
from shapely.geometry import Point

class ConsoleTrajectoryObserver(TrajectoryObserver):
    """将轨迹输出到控制台的观察者"""

    def on_start_recording(self):
        print("开始记录轨迹")

    def on_stop_recording(self):
        print("停止记录轨迹")

    def on_pause_recording(self):
        print("暂停记录轨迹")

    def on_resume_recording(self):
        print("恢复记录轨迹")

    def on_data_update(self, data: Dict):
        position = data['position']
        print(f"当前位置: ({position.x}, {position.y}), 高程: {data['altitude']}, 时间: {data['timestamp']}")

    def on_time_changed(self, new_time: float):
        print(f"时间更新: {new_time}")

    def on_position_changed(self, new_position: Point):
        print(f"位置更新: ({new_position.x}, {new_position.y})")

    def on_simulation_attempt(self, data: Dict):
        print(f"开始第 {data['attempt']}/{data['max_attempts']} 次模拟尝试")

    def on_simulation_retry(self, data: Dict):
        print(f"第 {data['attempt']}/{data['max_attempts']} 次模拟失败，准备重试")

    def on_simulation_success(self, data: Dict):
        print(f"模拟成功，用时 {data['attempt']} 次尝试")

    def on_simulation_failure(self, data: Dict):
        print(f"模拟失败，达到最大尝试次数 {data['max_attempts']}")