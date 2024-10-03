from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
from shapely.geometry import Point
from .config import Config
import random
import math
from pyproj import CRS, Transformer

# 定义常量
POSITION_KEY = 'position' # 位置
ALTITUDE_KEY = 'altitude' # 高程
TIMESTAMP_KEY = 'timestamp' # 时间戳
HEADING_KEY = 'heading' # 航向
ACCURACY_KEY = 'accuracy' # 精度
SIGNAL_STRENGTH_KEY = 'signal_strength' # 信号强度
WGS84_POSITION_KEY = 'wgs84_position' # WGS84坐标系下的位置

class GPSObserver(ABC):
    @abstractmethod
    def on_gps_update(self, data: Dict):
        """
        当 GPS 数据更新时调用
        
        :param data: 更新的 GPS 数据
        """
        pass

    @abstractmethod
    def on_gps_start_recording(self):
        """
        当 GPS 开始记录时调用
        """
        pass

    @abstractmethod
    def on_gps_stop_recording(self):
        """
        当 GPS 停止记录时调用
        """
        pass

    @abstractmethod
    def on_gps_pause_recording(self):
        """
        当 GPS 暂停记录时调用
        """
        pass

    @abstractmethod
    def on_gps_resume_recording(self):
        """
        当 GPS 恢复记录时调用
        """
        pass

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
        self.sampling_distance = config.get(Config.GPS_SAMPLING_DISTANCE_KEY, 5.0)  # 默认采样距离为5米
        self.coordinate_system = CRS.from_string(config.get_coordinate_system())
        self.to_wgs84 = self._create_to_wgs84_transformer()
        self.time_unit = config.get_time_unit()
        self.time_unit_factor = self._get_time_unit_factor()

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
        """
        检查是否应该进行采样
        
        :return: 是否应该采样
        """
        current_distance = self.position.distance(self.last_sampled_position)
        return current_distance >= self.sampling_distance

    def get_coordinate_system(self) -> str:
        """获取当前使用的坐标系统"""
        return self.coordinate_system.to_string()

    def get_position_wgs84(self) -> Tuple[float, float]:
        """获取WGS84坐标系下的位置"""
        return self.wgs84_position.x, self.wgs84_position.y

class AdvancedGPSDevice(GPSDevice):
    """高级GPS设备实现，包含复杂的模拟逻辑"""

    def __init__(self, config: Config):
        """
        初始化高级GPS设备
        
        :param config: 配置对象
        """
        super().__init__(config)
        self.accuracy = config.get(Config.GPS_INITIAL_ACCURACY_KEY)
        
        # 初始化信号强度
        min_strength = config.get(Config.GPS_INITIAL_SIGNAL_STRENGTH_MIN_KEY, 0.8)
        max_strength = config.get(Config.GPS_INITIAL_SIGNAL_STRENGTH_MAX_KEY, 1.0)

        lon, lat = self.get_position_wgs84()
        self.altitude = self.elevation_provider.get_elevation(lon, lat)
        self.__signal_strength = random.uniform(min_strength, max_strength)

    def update(self, elapsed_time: float, offset: Point) -> None:
        """
        更新高级GPS设备状态，包括精度变化、信号强度变化和位置更新
        
        :param elapsed_time: 经过的时间（以配置的时间单位为准）
        :param offset: 相对当前位置的偏移
        """
        # 将elapsed_time转换为秒
        elapsed_time_seconds = elapsed_time * self.time_unit_factor
        self.current_time += elapsed_time_seconds
        # 更新真实位置
        self.set_position(Point(self.position.x + offset.x, self.position.y + offset.y))
        
        # 模拟信号强度变化
        old_signal_strength = self.__signal_strength
        self._update_signal_strength()
        
        # 模拟精度变化
        self._update_accuracy()
        
        # 更新GPS位置
        self._update_position(old_signal_strength)

        self.altitude = self.elevation_provider.get_elevation(self.wgs84_position.x, self.wgs84_position.y)
        if self.should_sample():
            self.record_data()
            self.last_sampled_position = self.position
            self.notify_observers(self.get_data())

    def _update_position(self, old_signal_strength: float):
        """
        更新GPS位置
        当信号强度显著提高时，模拟位置跳变到更精确的位置
        
        :param old_signal_strength: 更新前的信号强度
        """
        # 定义信号强度显著提高的阈值
        SIGNAL_IMPROVEMENT_THRESHOLD = 0.2
        
        if self.__signal_strength - old_signal_strength > SIGNAL_IMPROVEMENT_THRESHOLD:
            # 信号强度显著提高，更新到更精确的位置
            error_distance = random.uniform(0, self.accuracy)
            error_angle = random.uniform(0, 2 * math.pi)
            error_x = error_distance * math.cos(error_angle)
            error_y = error_distance * math.sin(error_angle)
            self.set_position(Point(self.position.x + error_x, self.position.y + error_y))
        else:
            # 信号强度变化不大，保持小幅度抖动
            jitter_distance = random.uniform(0, self.accuracy / 10)
            jitter_angle = random.uniform(0, 2 * math.pi)
            jitter_x = jitter_distance * math.cos(jitter_angle)
            jitter_y = jitter_distance * math.sin(jitter_angle)
            self.set_position(Point(self.position.x + jitter_x, self.position.y + jitter_y))

    def _update_accuracy(self):
        """
        模拟GPS精度变化
        精度与信号强度成反比：
        - 信号强度高 -> 精度值小 -> 定位更精确
        - 信号强度低 -> 精度值大 -> 定位不精确
        """
        min_accuracy = self.config.get(Config.GPS_MIN_ACCURACY_KEY, 2.5)
        max_accuracy = self.config.get(Config.GPS_MAX_ACCURACY_KEY, 12.0)
        
        # 计算精度：信号强度越高，精度值越接近最小值（最精确）
        accuracy_range = max_accuracy - min_accuracy
        self.accuracy = max_accuracy - (self.__signal_strength * accuracy_range)
        
        # 添加一些随机波动以模拟真实世界的不确定性
        accuracy_variation = random.uniform(-0.5, 0.5)
        self.accuracy = max(min_accuracy, min(max_accuracy, self.accuracy + accuracy_variation))

    def _update_signal_strength(self):
        """模拟GPS信号强度变化"""
        min_strength = self.config.get(Config.GPS_MIN_SIGNAL_STRENGTH_KEY, 0.4)
        strength_change = random.uniform(-0.05, 0.05)  # 信号强度变化范围为 -0.05 到 0.05
        self.__signal_strength = max(min_strength, min(1.0, self.__signal_strength + strength_change))

    def get_data(self) -> Dict:
        """
        获取高级GPS设备的当前数据
        
        :return: GPS数据字典
        """
        data = {
            POSITION_KEY: self.position,
            ALTITUDE_KEY: self.altitude,
            TIMESTAMP_KEY: self.current_time,
            HEADING_KEY: self.heading,
            ACCURACY_KEY: self.accuracy,
            SIGNAL_STRENGTH_KEY: self.__signal_strength,
            WGS84_POSITION_KEY: self.wgs84_position,
        }
        return data

class GPSDeviceFactory:
    """GPS设备工厂类"""

    @staticmethod
    def create_gps_device(config: Config) -> GPSDevice:
        """
        创建GPS设备实例
        
        :param config: 配置对象
        :return: GPS设备实例
        """
        return AdvancedGPSDevice(config)