from abc import ABC, abstractmethod
from typing import List, Tuple

class ElevationProvider(ABC):
    @abstractmethod
    def get_elevation(self, lon: float, lat: float) -> float:
        """
        获取给定经纬度的高程
        
        :param lon: 经度
        :param lat: 纬度
        :return: 高程值（米）
        """
        pass

    @abstractmethod
    def batch_get_elevation(self, lon_lat_list: List[Tuple[float, float]]) -> List[float]:
        """
        批量获取给定经纬度列表的高程
        
        :param lon_lat_list: 经纬度列表，每个元素为(lon, lat)元组
        :return: 高程值列表（米）
        """
        pass