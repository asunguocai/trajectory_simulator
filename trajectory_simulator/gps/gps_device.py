from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
from shapely.geometry import Point
from ..config.config import Config
from .gps_observer import GPSObserver
from .sampling_strategy import SamplingStrategy, SamplingStrategyFactory
from pyproj import CRS, Transformer

# 定义常量
POSITION_KEY = 'position' # 位置
ALTITUDE_KEY = 'altitude' # 高程
TIMESTAMP_KEY = 'timestamp' # 时间戳
HEADING_KEY = 'heading' # 航向
ACCURACY_KEY = 'accuracy' # 精度
SIGNAL_STRENGTH_KEY = 'signal_strength' # 信号强度
WGS84_POSITION_KEY = 'wgs84_position' # WGS84坐标系下的位置

class GPSDevice(ABC):
    """GPS设备抽象基类"""

    def __init__(self, config: Config):
        """
        初始化GPS设备
        
        :param config: 配置对象
        """
        self.config = config
        self.elevation_provider = config.get_elevation_provider()
        self.trajectory: List[Dict] = []
        self.is_recording = False
        self.is_paused = False
        self.current_time = 0 # 当前时间, 默认为0
        self.position = Point(0, 0) # 当前位置，默认为0
        self.wgs84_position = Point(0, 0) # WGS84坐标系下的位置
        self.altitude = 0 # 当前高程
        self.heading = 0
        self.observers: List[GPSObserver] = []
        self.last_sampled_position = self.position
        self.coordinate_system = CRS.from_string(config.get_coordinate_system())
        self.to_wgs84 = self._create_to_wgs84_transformer()
        self.time_unit = config.get_time_unit()
        self.time_unit_factor = self._get_time_unit_factor()
        self.sampling_strategy = SamplingStrategyFactory.create_sampling_strategy(config)

    def _create_to_wgs84_transformer(self):
        if self.coordinate_system == CRS.from_epsg(4326):
            return lambda x, y: (x, y)
        else:
            return Transformer.from_crs(self.coordinate_system, CRS.from_epsg(4326), always_xy=True).transform

    def _get_time_unit_factor(self):
        """获取时间单位转换因子"""
        if self.time_unit == "millisecond":
            return 0.001
        elif self.time_unit == "minute":
            return 60
        elif self.time_unit == "hour":
            return 3600
        else:  # 默认为秒
            return 1

    @abstractmethod
    def update(self, elapsed_time: float, offset: Point) -> None:
        """
        更新GPS设备状态
        
        :param elapsed_time: 经过的时间（以配置的时间单位为准）
        :param offset: 相对当前位置的偏移
        """
        raise NotImplementedError("not implemented")

    @abstractmethod
    def get_data(self) -> Dict:
        """
        获取当前GPS数据
        
        :return: 包含位置、高程、时间戳等信息的字典
        """
        raise NotImplementedError("not implemented")

    def set_position(self, new_position: Point) -> None:
        """
        设置GPS设备的当前位置，并更新WGS84坐标
        
        :param new_position: 新的位置
        """
        self.position = new_position
        wgs84_x, wgs84_y = self.to_wgs84(new_position.x, new_position.y)
        self.wgs84_position = Point(wgs84_x, wgs84_y)

    def set_time(self, new_time: float) -> None:
        """
        设置当前时间
        
        :param new_time: 新的时间
        """
        self.current_time = new_time

    def start_recording(self) -> None:
        """开始记录轨迹"""
        self.is_recording = True
        self.is_paused = False
        for observer in self.observers:
            observer.on_gps_start_recording()
        
        self.record_data()# 记录初始数据
        self.notify_observers(self.get_data())

    def stop_recording(self) -> None:
        """停止记录轨迹"""
        self.record_data()# 记录结束数据
        self.notify_observers(self.get_data())
        self.is_recording = False
        self.is_paused = False
        for observer in self.observers:
            observer.on_gps_stop_recording()

    def pause_recording(self) -> None:
        """暂停记录轨迹"""
        if self.is_recording:
            self.is_paused = True
            for observer in self.observers:
                observer.on_gps_pause_recording()

    def resume_recording(self) -> None:
        """恢复记录轨迹"""
        if self.is_recording and self.is_paused:
            self.is_paused = False
            for observer in self.observers:
                observer.on_gps_resume_recording()

    def record_data(self) -> None:
        """记录当前GPS数据到轨迹中"""
        if self.is_recording and not self.is_paused:
            self.trajectory.append(self.get_data())

    def get_trajectory(self) -> List[Dict]:
        """
        获取记录的轨迹
        
        :return: 轨迹数据列表
        """
        return self.trajectory

    def add_observer(self, observer: GPSObserver):
        self.observers.append(observer)

    def remove_observer(self, observer: GPSObserver):
        self.observers.remove(observer)

    def notify_observers(self, data: Dict):
        for observer in self.observers:
            observer.on_gps_update(data)

    def should_sample(self) -> bool:
        return self.sampling_strategy.should_sample(self)

    def get_coordinate_system(self) -> str:
        """获取当前使用的坐标系统"""
        return self.coordinate_system.to_string()

    def get_position_wgs84(self) -> Tuple[float, float]:
        """获取WGS84坐标系下的位置"""
        return self.wgs84_position.x, self.wgs84_position.y