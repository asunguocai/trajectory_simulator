from typing import List, Dict
from shapely.geometry import Point, Polygon
from .config.config import Config
from .person.person import Person, PersonFactory
from .gps.gps_device import GPSDevice
from .gps.gps_device_factory import GPSDeviceFactory
from .gps.gps_device import POSITION_KEY, ALTITUDE_KEY, TIMESTAMP_KEY, HEADING_KEY, ACCURACY_KEY
from .gps.gps_observer import GPSObserver
from .observers.trajectory_observer import TrajectoryObserver
from .observers.console_trajectory_observer import ConsoleTrajectoryObserver
# 移除 GPXTrajectoryObserver 的导入
from .inspection_task import InspectionTask
import time

class TrajectorySimulator(GPSObserver):
    """轨迹模拟器类"""

    def __init__(self, config: Config):
        """
        初始化轨迹模拟器
        
        :param config: 配置对象
        """
        self.config = config
        self.gps = GPSDeviceFactory.create_gps_device(config)
        self.observers: List[TrajectoryObserver] = []
        self.gps.add_observer(self)

    def simulate(self, start_time: float, start_position: Point, polygon: Polygon) -> List[Dict]:
        """
        模拟轨迹
        
        :param start_time: 起始时间
        :param start_position: 起始位置
        :param polygon: 模拟区域多边形
        :return: 模拟生成的轨迹
        """
        max_attempts = self.config.get(Config.MAX_SIMULATION_ATTEMPTS_KEY, 3)
        
        for attempt in range(max_attempts):
            self.notify_observers("simulation_attempt", {"attempt": attempt + 1, "max_attempts": max_attempts})
            
            # 重置模拟器状态
            self.reset_simulation(start_time, start_position, polygon)
            
            # 开始记录GPS数据
            self.gps.start_recording()

            # 主要模拟循环
            while not self.inspection_task.is_complete():
                current_time = time.time()
                elapsed_time = 1
                self.last_update_time = current_time

                # 获取下一个目标点
                target = self.inspection_task.get_next_target()
                # 移动人员到新位置
                new_position = self.person.move(target, elapsed_time)

                # 更新GPS设备位置
                offset = Point(new_position.x - self.gps.position.x, new_position.y - self.gps.position.y)
                self.gps.update(elapsed_time, offset)
                
                # 检查GPS显示的点是否在当前行进边上
                gps_position = self.gps.get_data()[POSITION_KEY]
                if self.inspection_task.is_on_current_edge(gps_position, self.tolerance):
                    if not self.inspection_task.move_to_next_target():
                        break
            
            # 停止记录GPS数据
            self.gps.stop_recording()
            # 获取完整轨迹
            trajectory = self.gps.get_trajectory()
            
            # 检查轨迹是否有效
            if self.is_valid_trajectory(trajectory, polygon):
                self.notify_observers("simulation_success", {"attempt": attempt + 1})
                return trajectory

            self.notify_observers("simulation_retry", {"attempt": attempt + 1, "max_attempts": max_attempts})

        self.notify_observers("simulation_failure", {"max_attempts": max_attempts})
        return self.gps.get_trajectory()

    def reset_simulation(self, start_time: float, start_position: Point, polygon: Polygon) -> None:
        """
        重置模拟器状态
        
        :param start_time: 起始时间
        :param start_position: 起始位置
        :param polygon: 模拟区域多边形
        """
        self.gps.set_time(start_time)
        self.gps.set_position(start_position)
        self.last_update_time = start_time
        self.actual_polygon = self._generate_terrain(polygon)
        self.person = PersonFactory.create_person(self.config, self.gps, self.actual_polygon)
        self.inspection_task = InspectionTask(self.actual_polygon, self.config)
        self.tolerance = self.config.get(Config.TOLERANCE_KEY, 1.0)

    def is_valid_trajectory(self, trajectory: List[Dict], polygon: Polygon) -> bool:
        """
        检查轨迹是否有效
        
        :param trajectory: 轨迹数据
        :param polygon: 原始多边形
        :return: 轨迹是否有效
        """
        if len(trajectory) < 3:
            return False
        # 从轨迹数据中提取坐标
        coordinates = [(data[POSITION_KEY].x, data[POSITION_KEY].y) for data in trajectory]
        
        try:
            trajectory_polygon = Polygon(coordinates)
            original_area = polygon.area
            trajectory_area = trajectory_polygon.area
            
            area_threshold = self.config.get(Config.TRAJECTORY_AREA_THRESHOLD_KEY, 0.9)
            return trajectory_area / original_area >= area_threshold
        except ValueError as e:
            print(f"创建轨迹多边形时出错: {e}")
            return False

    def _generate_terrain(self, polygon: Polygon) -> Polygon:
        """
        生成地形，添加额外的点以创建更复杂的多边形，例如添加障碍
        
        :param polygon: 输入多边形
        :return: 生成的地形多边形
        """
        return polygon

    def set_time(self, new_time: float) -> None:
        """设置模拟器的当前时间"""
        self.gps.set_time(new_time)
        self.last_update_time = new_time
        self.notify_observers("time_changed", {"new_time": new_time})

    def set_position(self, new_position: Point) -> None:
        """设置模拟器的当前位置"""
        self.gps.set_position(new_position)
        self.notify_observers("position_changed", {"new_position": new_position})

    def add_observer(self, observer: TrajectoryObserver):
        self.observers.append(observer)

    def remove_observer(self, observer: TrajectoryObserver):
        self.observers.remove(observer)

    def notify_observers(self, event: str, data=None):
        for observer in self.observers:
            if event == "start_recording":
                observer.on_start_recording()
            elif event == "stop_recording":
                observer.on_stop_recording()
            elif event == "pause_recording":
                observer.on_pause_recording()
            elif event == "resume_recording":
                observer.on_resume_recording()
            elif event == "update":
                observer.on_data_update(data)
            elif event == "time_changed":
                observer.on_time_changed(data["new_time"])
            elif event == "position_changed":
                observer.on_position_changed(data["new_position"])
            elif event == "simulation_attempt":
                observer.on_simulation_attempt(data)
            elif event == "simulation_retry":
                observer.on_simulation_retry(data)
            elif event == "simulation_success":
                observer.on_simulation_success(data)
            elif event == "simulation_failure":
                observer.on_simulation_failure(data)

    def on_gps_update(self, data: Dict):
        """处理 GPS 更新事件"""
        self.notify_observers("update", data)

    def on_gps_start_recording(self):
        """处理 GPS 开始记录事件"""
        self.notify_observers("start_recording")

    def on_gps_stop_recording(self):
        """处理 GPS 停止记录事件"""
        self.notify_observers("stop_recording")

    def on_gps_pause_recording(self):
        """处理 GPS 暂停记录事件"""
        self.notify_observers("pause_recording")

    def on_gps_resume_recording(self):
        """处理 GPS 恢复记录事件"""
        self.notify_observers("resume_recording")