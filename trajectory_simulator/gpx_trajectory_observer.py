from typing import Dict
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from shapely.geometry import Point, Polygon
from .trajectory_simulator import TrajectoryObserver
from .gps_device import POSITION_KEY, ALTITUDE_KEY, TIMESTAMP_KEY, WGS84_POSITION_KEY


class GPXTrajectoryObserver(TrajectoryObserver):
    """将轨迹保存为GPX文件的观察者"""

    # 可配置参数的常量
    CREATOR_KEY = "creator"
    METADATA_NAME_KEY = "metadata_name"
    TRACK_NAME_KEY = "track_name"
    METADATA_DESCRIPTION_KEY = "metadata_description"
    METADATA_AUTHOR_KEY = "metadata_author"

    def __init__(self, file_path: str, config: Dict, elevation_provider=None):
        """
        初始化GPX轨迹观察者
        
        :param file_path: 输出的GPX文件路径
        :param config: 配置字典，包含GPX文件的元数据信息
        :param elevation_provider: 高程数据提供者
        """
        self.file_path = file_path
        self.config = config
        self.elevation_provider = elevation_provider
        self.initial_time = None

        # 创建GPX根元素，设置版本和创建者
        self.root = ET.Element("gpx", version="1.1", 
                               creator=self.config.get(self.CREATOR_KEY, "ArcGIS Trajectory Simulator"))
        # 添加元数据、轨迹和轨迹段元素
        self.metadata = ET.SubElement(self.root, "metadata")
        self.track = ET.SubElement(self.root, "trk")
        self.segment = ET.SubElement(self.track, "trkseg")
        # 初始化轨迹点列表和时间记录
        self.trajectory = []
        self.start_time = None
        self.end_time = None

    def on_start_recording(self):
        """开始记录时的操作，添加元数据和轨迹名称"""
        # 设置元数据名称
        ET.SubElement(self.metadata, "name").text = self.config.get(self.METADATA_NAME_KEY, "Simulated Trajectory")
        # 设置轨迹名称
        ET.SubElement(self.track, "name").text = self.config.get(self.TRACK_NAME_KEY, "Simulated Track")
        
        # 添加其他可能的元数据
        if self.METADATA_DESCRIPTION_KEY in self.config:
            ET.SubElement(self.metadata, "desc").text = self.config[self.METADATA_DESCRIPTION_KEY]
        if self.METADATA_AUTHOR_KEY in self.config:
            author = ET.SubElement(self.metadata, "author")
            ET.SubElement(author, "name").text = self.config[self.METADATA_AUTHOR_KEY]

    def on_stop_recording(self):
        """停止记录时的操作，添加扩展信息并写入GPX文件"""
        self._add_elevations()
        self._add_extensions()
        tree = ET.ElementTree(self.root)
        tree.write(self.file_path, encoding="utf-8", xml_declaration=True)

    def on_data_update(self, data: Dict):
        """
        更新轨迹数据
        
        :param data: 包含位置、时间戳和高程信息的字典
        """
        wgs84_position = data[WGS84_POSITION_KEY]
        timestamp = datetime.fromtimestamp(data[TIMESTAMP_KEY], tz=timezone.utc)

        # 创建轨迹点元素，但暂不添加高程信息
        trkpt = ET.SubElement(self.segment, "trkpt", lat=str(wgs84_position.y), lon=str(wgs84_position.x))
        ET.SubElement(trkpt, "time").text = timestamp.isoformat()

        # 记录轨迹点信息
        self.trajectory.append((wgs84_position, timestamp, trkpt))

        # 更新开始和结束时间
        if self.start_time is None:
            self.start_time = timestamp
        self.end_time = timestamp

    def _add_elevations(self):
        """在记录结束后统一添加高程信息"""
        if self.elevation_provider:
            lon_lat_list = [(point[0].x, point[0].y) for point in self.trajectory]
            elevations = self.elevation_provider.batch_get_elevation(lon_lat_list)
            
            for (_, _, trkpt), elevation in zip(self.trajectory, elevations):
                ET.SubElement(trkpt, "ele").text = str(elevation)

    def _add_extensions(self):
        """添加扩展信息，包括开始时间、结束时间、总距离和面积"""
        extensions = ET.SubElement(self.track, "extensions")
        ET.SubElement(extensions, "starttime").text = self.start_time.isoformat()
        ET.SubElement(extensions, "endtime").text = self.end_time.isoformat()
        
        total_distance = self._calculate_total_distance()
        ET.SubElement(extensions, "length").text = str(total_distance)
        
        area = self._calculate_area()
        ET.SubElement(extensions, "area").text = str(area)

    def _calculate_total_distance(self):
        """
        计算轨迹的总距离
        
        :return: 总距离（米）
        """
        if len(self.trajectory) < 2:
            return 0
        
        total_distance = 0
        for i in range(1, len(self.trajectory)):
            p1 = self.trajectory[i-1][0]
            p2 = self.trajectory[i][0]
            total_distance += p1.distance(p2)
        
        return total_distance

    def _calculate_area(self):
        """
        计算轨迹围成的多边形面积
        
        :return: 面积（平方米）
        """
        if len(self.trajectory) < 3:
            return 0
        
        points = [point[0] for point in self.trajectory]
        polygon = Polygon(points)
        return polygon.area