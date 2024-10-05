from shapely.geometry import Point, Polygon, LineString
from .config.config import Config

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