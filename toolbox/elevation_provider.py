class ElevationProvider:
    """
    高程提供者基类，用于获取给定WGS84经纬度的高程
    """
    def get_elevation(self, lon, lat):
        """
        获取给定WGS84经纬度的高程
        
        参数:
            lon (float): 经度
            lat (float): 纬度
        
        返回:
            float: 高程值（米）
        """
        raise NotImplementedError("This method should be implemented by subclasses")
    
    def batch_get_elevation(self, lon_lat_list):
        """
        批量获取给定WGS84经纬度的高程
        
        参数:
            lon_lat_list (list): 包含经度和纬度的列表，如：[(lon1, lat1), (lon2, lat2), ...]
        
        返回:
            list: 高程值列表，如：[elevation1, elevation2, ...]
        """
        return [self.get_elevation(lon, lat) for lon, lat in lon_lat_list]

class DefaultElevationProvider(ElevationProvider):
    """
    默认高程提供者，始终返回0米高程
    """
    def get_elevation(self, lon, lat):
        return 0.0
    
    def batch_get_elevation(self, lon_lat_list):
        return [0.0] * len(lon_lat_list)

