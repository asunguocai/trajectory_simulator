from typing import List, Dict
from shapely.geometry import Point, Polygon, LineString
from .config import Config
from .person import Person, PersonFactory, PersonObserver
from .gps_device import GPSDevice, GPSDeviceFactory, POSITION_KEY, ALTITUDE_KEY, TIMESTAMP_KEY, HEADING_KEY, ACCURACY_KEY, GPSObserver
import time

class InspectionTask:
    """巡检任务类，管理巡检路径和目标点"""

    def __init__(self, polygon: Polygon, config: Config):
        """
        初始化巡检任务
        
        :param polygon: 巡检区域多边形
        :param config: 配置对象
        """
        self.original_polygon = polygon
        self.config = config
        self.target_index = 0
        self.current_edge = None
        self.valid_vertices = list(polygon.exterior.coords)
        self.update_current_edge()

    def update_current_edge(self):
        """更新当前行进边"""
        start = Point(self.valid_vertices[self.target_index])
        end = Point(self.valid_vertices[(self.target_index + 1) % len(self.valid_vertices)])
        self.current_edge = LineString([start, end])

    def get_next_target(self) -> Point:
        """
        获取下一个目标点
        
        :return: 下一个目标点，如果巡检完成则返回None
        """
        if self.target_index >= len(self.valid_vertices) - 1:
            return None
        
        target = Point(self.valid_vertices[self.target_index + 1])
        return target
    
    def is_on_current_edge(self, point: Point, tolerance: float = 1e-6) -> bool:
        """
        检查点是否在当前行进边的终点或其延长线上
        
        :param point: 要检查的点
        :param tolerance: 容差值
        :return: 是否在当前行进边的终点或其延长线上
        """
        end_point = Point(self.current_edge.coords[-1])
        if self.target_index == len(self.valid_vertices) - 1:  # 如果是最后一条边
            print(f"最后一条边，距离终点距离: {point.distance(end_point)}")
            closing_distance = self.config.get(Config.CLOSING_DISTANCE_KEY, tolerance)
            return point.distance(end_point) < closing_distance
        return point.distance(end_point) < tolerance

    def move_to_next_target(self) -> bool:
        """
        移动到下一个目标点
        
        :return: 是否成功移动到下一个目标点
        """
        self.target_index += 1
        if self.target_index >= len(self.valid_vertices) - 1:
            return False
        self.update_current_edge()
        return True

    def is_complete(self) -> bool:
        """
        检查巡检是否完成
        
        :return: 巡检是否完成
        """
        return self.target_index >= len(self.valid_vertices) - 1

    def get_polygon(self) -> Polygon:
        """
        获取处理后的多边形
        
        :return: 处理后的多边形
        """
        return self.original_polygon

class TrajectoryObserver:
    """轨迹观察者抽象基类"""

    def update(self, event: str, data: Dict = None):
        if event == "start_recording":
            self.on_start_recording()
        elif event == "stop_recording":
            self.on_stop_recording()
        elif event == "pause_recording":
            self.on_pause_recording()
        elif event == "resume_recording":
            self.on_resume_recording()
        elif event == "update":
            self.on_data_update(data)
        elif event == "time_changed":
            self.on_time_changed(data)
        elif event == "position_changed":
            self.on_position_changed(data)
        elif event == "simulation_attempt":
            self.on_simulation_attempt(data)
        elif event == "simulation_retry":
            self.on_simulation_retry(data)
        elif event == "simulation_success":
            self.on_simulation_success(data)
        elif event == "simulation_failure":
            self.on_simulation_failure(data)

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
            observer.update(event, data)

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
        position = data[POSITION_KEY]
        print(f"当前位置: ({position.x}, {position.y}), 高程: {data[ALTITUDE_KEY]}, 时间: {data[TIMESTAMP_KEY]}")

    def on_simulation_attempt(self, data: Dict):
        print(f"开始第 {data['attempt']}/{data['max_attempts']} 次模拟尝试")

    def on_simulation_retry(self, data: Dict):
        print(f"第 {data['attempt']}/{data['max_attempts']} 次模拟失败，准备重试")

    def on_simulation_success(self, data: Dict):
        print(f"模拟成功，用时 {data['attempt']} 次尝试")

    def on_simulation_failure(self, data: Dict):
        print(f"模拟失败，达到最大尝试次数 {data['max_attempts']}")

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
        position = data[POSITION_KEY]
        self._write_event("update", position.x, position.y, data[ALTITUDE_KEY], data[TIMESTAMP_KEY], data[HEADING_KEY], data[ACCURACY_KEY])

    def on_simulation_attempt(self, data: Dict):
        self._write_event("simulation_attempt", attempt=data['attempt'], max_attempts=data['max_attempts'])

    def on_simulation_retry(self, data: Dict):
        self._write_event("simulation_retry", attempt=data['attempt'], max_attempts=data['max_attempts'])

    def on_simulation_success(self, data: Dict):
        self._write_event("simulation_success", attempt=data['attempt'])

    def on_simulation_failure(self, data: Dict):
        self._write_event("simulation_failure", max_attempts=data['max_attempts'])

    def _write_event(self, event: str, x: float = None, y: float = None, altitude: float = None, timestamp: float = None, heading: float = None, accuracy: float = None):
        with open(self.filename, 'a') as f:
            f.write(f"{event},{x},{y},{altitude},{timestamp},{heading},{accuracy}\n")