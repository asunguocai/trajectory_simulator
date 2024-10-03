from abc import ABC, abstractmethod
import random
import math
from typing import List,Dict
from shapely.geometry import Point, Polygon
from .config import Config
from .gps_device import GPSDevice

class PersonObserver(ABC):
    @abstractmethod
    def on_person_move(self, data: Dict):
        """
        当人员移动时调用
        
        :param data: 移动数据，包含新位置和经过的时间
        """
        pass

class MovementStrategy(ABC):
    """移动策略抽象基类"""

    @abstractmethod
    def move(self, gps_position: Point, target: Point, config: Config) -> Point:
        """
        计算下一个移动位置
        
        :param gps_position: GPS设备显示的当前位置
        :param target: 目标位置
        :param config: 配置对象
        :return: 计算得到的新位置
        """
        pass

class RealisticMovementStrategy(MovementStrategy):
    """真实场景的移动策略，包含偏航和纠偏逻辑"""

    def move(self, gps_position: Point, target: Point, elapsed_time: float, config: Config) -> Point:
        """
        计算下一个移动位置，考虑偏航因素
        
        :param gps_position: GPS设备显示的当前位置
        :param target: 目标位置
        :param config: 配置对象
        :return: 计算得到的新位置
        """
        # 计算当前位置到目标位置的方向角（航向）
        dx = target.x - gps_position.x
        dy = target.y - gps_position.y
        heading = math.degrees(math.atan2(dy, dx))

        # 模拟偏航：有一定概率偏离预定航向
        deviation_probability = config.get(Config.PERSON_DEVIATION_PROBABILITY_KEY, 0.1)
        max_deviation_angle = config.get(Config.PERSON_MAX_DEVIATION_ANGLE_KEY, 10.0)
        if random.random() < deviation_probability:
            # 在最大偏航角度范围内随机选择一个偏航角度
            heading += random.uniform(-max_deviation_angle, max_deviation_angle)

        # 计算移动距离：速度 * 时间
        speed_range = config.get(Config.PERSON_SPEED_RANGE_KEY, (0.8, 1.5))
        speed = random.uniform(*speed_range)  # 在速度范围内随机选择一个速度
        time_step = config.get("simulation.time_step", 1.0)
        distance = speed * time_step * elapsed_time

        # 计算新位置：使用极坐标到直角坐标的转换
        new_x = gps_position.x + distance * math.cos(math.radians(heading))
        new_y = gps_position.y + distance * math.sin(math.radians(heading))

        return Point(new_x, new_y)

class Person:
    """模拟人的移动行为的类"""

    def __init__(self, config: Config, gps: GPSDevice, actual_polygon: Polygon):
        """
        初始化Person对象
        
        :param config: 配置对象
        :param gps: GPS设备对象
        :param actual_polygon: 添加障碍后的实际巡检区域多边形
        """
        self.config = config
        self.gps = gps
        self.actual_polygon = actual_polygon
        self.movement_strategy = RealisticMovementStrategy()
        self.position = self.gps.position

    def move(self, target: Point, elapsed_time: float) -> Point:
        """
        执行一步移动，包括偏航纠正
        
        :param target: 目标位置
        :param elapsed_time: 经过的时间
        :return: 移动后的新位置
        """
        gps_position = self.gps.position
        new_position = self.movement_strategy.move(gps_position, target, elapsed_time, self.config)
        
        # 检查是否需要纠正航向，如果需要则进行纠正
        if self.needs_course_correction(new_position):
            new_position = self.correct_course(new_position, target)
        
        # 更新自身位置
        self.position = new_position
        
        return new_position

    def needs_course_correction(self, position: Point) -> bool:
        """
        检查是否需要航向修正
        
        :param position: 当前位置
        :return: 是否需要修正
        """
        # 获取纠正阈值，即允许偏离多边形边界的最大距离
        correction_threshold = self.config.get(Config.PERSON_CORRECTION_THRESHOLD_KEY, 5.0)
        # 计算当前位置到多边形边界的距离，如果大于阈值则需要纠正
        return self.actual_polygon.exterior.distance(position) > correction_threshold

    def correct_course(self, position: Point, target: Point) -> Point:
        """
        执行航向修正
        
        :param position: 当前位置
        :param target: 目标位置
        :return: 修正后的位置
        """
        # 找到多边形边界上距离当前位置最近的点
        nearest_point = self.actual_polygon.exterior.interpolate(self.actual_polygon.exterior.project(position))
        
        # 计算从当前位置到最近点的矢量
        correction_vector = (nearest_point.x - position.x, nearest_point.y - position.y)
        correction_distance = math.sqrt(correction_vector[0]**2 + correction_vector[1]**2)
        
        if correction_distance > 0:
            # 计算单位矢量
            unit_vector = (correction_vector[0] / correction_distance, correction_vector[1] / correction_distance)
            # 获取纠正因子，决定向最近点移动的程度
            correction_factor = self.config.get(Config.PERSON_CORRECTION_FACTOR_KEY, 0.5)
            # 计算纠正后的新位置
            return Point(
                position.x + unit_vector[0] * correction_distance * correction_factor,
                position.y + unit_vector[1] * correction_distance * correction_factor
            )
        return position  # 如果距离为0，则不需要纠正



class PersonFactory:
    """Person工厂类"""

    @staticmethod
    def create_person(config: Config, gps: GPSDevice, actual_polygon: Polygon) -> Person:
        """
        创建Person对象
        
        :param config: 配置对象
        :param gps: GPS设备对象
        :param actual_polygon: 添加障碍后的实际巡检区域多边形
        :return: 创建的Person对象
        """
        return Person(config, gps, actual_polygon)