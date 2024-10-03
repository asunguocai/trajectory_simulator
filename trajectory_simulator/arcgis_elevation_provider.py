from .elevation_provider import ElevationProvider
import arcpy
import arcpy.sa as sa
import os
import re

class ArcgisElevationProvider(ElevationProvider):
    """
    使用多个本地DEM数据获取高程的提供者类
    """
    def __init__(self, dem_path_list):
        """
        初始化ArcgisElevationProvider

        参数:
            dem_path_list (list): DEM文件路径列表
        """
        self.dem_dict = {}
        self.dem_bounds = {}
        for dem_path in dem_path_list:
            raster = arcpy.Raster(dem_path)
            self.dem_dict[dem_path] = raster
            
            # 获取DEM的经纬度范围
            extent = raster.extent
            self.dem_bounds[dem_path] = {
                "min_lon": extent.XMin,
                "max_lon": extent.XMax,
                "min_lat": extent.YMin,
                "max_lat": extent.YMax
            }
        
        self.spatial_reference = arcpy.SpatialReference(4326)  # WGS84

    def _get_applicable_dem(self, lon, lat):
        """
        根据给定的经纬度获取适用的DEM

        参数:
            lon (float): 经度
            lat (float): 纬度

        返回:
            arcpy.Raster: 适用的DEM栅格对象，如果没有找到则返回None
        """
        for dem_path, bounds in self.dem_bounds.items():
            if (bounds['min_lon'] <= lon <= bounds['max_lon'] and
                bounds['min_lat'] <= lat <= bounds['max_lat']):
                return self.dem_dict[dem_path]
        return None
    
    def batch_get_elevation(self, lon_lat_list):
        # 创建临时点要素类
        temp_workspace = arcpy.env.scratchGDB
        temp_points = os.path.join(temp_workspace, "temp_points")
        arcpy.CreateFeatureclass_management(temp_workspace, "temp_points", "POINT", spatial_reference=self.spatial_reference)
        
        arcpy.AddField_management(temp_points, "PointID", "LONG")
        arcpy.AddField_management(temp_points, "X", "DOUBLE")
        arcpy.AddField_management(temp_points, "Y", "DOUBLE")
        arcpy.AddField_management(temp_points, "ELEVATION", "DOUBLE")

        # 添加点要素
        with arcpy.da.InsertCursor(temp_points, ["SHAPE@", "PointID", "X", "Y"]) as cursor:
            for i, (lon, lat) in enumerate(lon_lat_list):
                point = arcpy.Point(lon, lat)
                cursor.insertRow([point, i, lon, lat])

        try:
            # 为每个DEM准备单独的字段名
            field_names = [f"ELEVATION_{i}" for i in range(len(self.dem_dict))]
            in_rasters = [[dem_path, field_name] for dem_path, field_name in zip(self.dem_dict.keys(), field_names)]

            # 使用ExtractMultiValuesToPoints一次性提取所有DEM的高程值
            sa.ExtractMultiValuesToPoints(temp_points, in_rasters, "BILINEAR")

            # 读取高程值
            elevations = [0.0] * len(lon_lat_list)
            with arcpy.da.SearchCursor(temp_points, ["PointID"] + field_names) as cursor:
                for row in cursor:
                    point_id = row[0]
                    # 找到第一个非None的高程值
                    elevation = next((e for e in row[1:] if e is not None), 0.0)
                    elevations[point_id] = int(elevation) # 取整即可

        except RuntimeError as e:
            print(f"提取高程值时出错: {str(e)}")
            elevations = [0.0] * len(lon_lat_list)

        finally:
            # 删除临时点要素类
            arcpy.Delete_management(temp_points)
        return elevations

    def get_elevation(self, lon, lat):
        """
        获取给定WGS84经纬度的高程

        参数:
            lon (float): 经度
            lat (float): 纬度

        返回:
            float: 高程值（米）
        """
        return self.batch_get_elevation([(lon, lat)])[0]
