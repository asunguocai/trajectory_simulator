from .gps_device import GPSDevice, POSITION_KEY, ALTITUDE_KEY, TIMESTAMP_KEY, HEADING_KEY, ACCURACY_KEY, SIGNAL_STRENGTH_KEY, WGS84_POSITION_KEY
from ..config.config import Config
import random
import math
from typing import Dict
from shapely.geometry import Point

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