# -*- coding: utf-8 -*-

import arcpy
import os
import datetime
from trajectory_simulators import TrajectorySimulator
from arcgis_elevation_provider import ArcgisElevationProvider

class Toolbox(object):
    def __init__(self):
        """定义工具箱（工具箱的名称是.pyt文件的名称）。"""
        self.label = "航迹模拟工具箱"
        self.alias = "TrajectorySimulationToolbox"

        # 与此工具箱关联的工具类列表
        self.tools = [TrajectorySimulationTool]

class TrajectorySimulationTool(object):
    def __init__(self):
        """定义工具（工具名称是类的名称）。"""
        self.label = "航迹模拟工具"
        self.description = "模拟多个多边形区域内的人员航迹"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """定义工具参数。"""
        # 输入多边形要素类
        input_features = arcpy.Parameter(
            displayName="输入多边形要素类",
            name="input_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        input_features.filter.list = ["Polygon"]
        input_features.description = "包含模拟区域的多边形要素类"

        # 输出文件夹
        output_folder = arcpy.Parameter(
            displayName="输出文件夹",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")
        output_folder.description = "存储模拟结果的文件夹路径"

        # 输出要素类名称
        output_name = arcpy.Parameter(
            displayName="输出要素类名称",
            name="output_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        output_name.value = "simulated_trajectories"
        output_name.description = "模拟生成的轨迹要素类的名称"

        # 人员编号字段
        person_num_field = arcpy.Parameter(
            displayName="人员编号字段",
            name="person_num_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        person_num_field.parameterDependencies = [input_features.name]
        person_num_field.description = "包含人员编号的字段（如果有）"

        # 起始时间字段
        start_time_field = arcpy.Parameter(
            displayName="起始时间字段",
            name="start_time_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        start_time_field.parameterDependencies = [input_features.name]
        start_time_field.description = "包含起始时间的字段（如果有）"

        # 配置文件路径
        config_path = arcpy.Parameter(
            displayName="配置文件路径",
            name="config_path",
            datatype="DEFile",
            parameterType="Optional",
            direction="Input")
        config_path.filter.list = ["json"]
        config_path.description = "模拟参数的JSON配置文件路径"

        # DEM文件路径列表
        dem_paths = arcpy.Parameter(
            displayName="DEM数据",
            name="dem_paths",
            datatype=["DEFile"],
            parameterType="Optional",
            direction="Input",
            multiValue=True)
        dem_paths.description = "用于提供高程信息的DEM数据（可选多个）"

        # 回调字段列表
        callback_fields = arcpy.Parameter(
            displayName="查询字段",
            name="callback_fields",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True)
        callback_fields.filter.list = [f.name for f in arcpy.ListFields(input_features.value)] if input_features.value else []
        callback_fields.description = "用于生成轨迹名称的所需的字段列表"

        # 回调函数代码
        callback_code = arcpy.Parameter(
            displayName="回调函数代码",
            name="callback_code",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        callback_code.description = "用于生成轨迹名称的Python回调函数代码"

        # 设置默认回调函数代码
        default_callback = """
def naming_callback(row, callback_fields):
    index_dict = getattr(naming_callback, 'index_dict', {})
    field_values = [str(row[callback_fields.index(field)]) for field in callback_fields]
    key = "_".join(field_values)
    if key not in index_dict:
        index_dict[key] = 0
    index = index_dict[key]
    index_dict[key] += 1
    naming_callback.index_dict = index_dict
    return f"{key}_{index}"
"""
        callback_code.value = default_callback

        params = [input_features, output_folder, output_name, person_num_field, start_time_field, config_path, dem_paths, callback_fields, callback_code]

        # 添加参数分组
        input_features.category = "输入数据"
        output_folder.category = "输出设置"
        output_name.category = "输出设置"
        person_num_field.category = "字段设置"
        start_time_field.category = "字段设置"
        config_path.category = "高级设置"
        dem_paths.category = "高级设置"
        callback_fields.category = "回调设置"
        callback_code.category = "回调设置"

        return params

    def isLicensed(self):
        """设置工具是否可以执行。"""
        return True

    def updateParameters(self, parameters):
        """在内部验证执行之前修改参数的值和属性。每当参数被更改时，都会调用此方法。"""
        if parameters[0].altered:
            parameters[7].filter.list = [f.name for f in arcpy.ListFields(parameters[0].value)]
    
        # 验证回调函数代码
        if parameters[8].altered:
            try:
                callback_namespace = {}
                exec(parameters[8].value, callback_namespace)
                if 'naming_callback' not in callback_namespace or not callable(callback_namespace['naming_callback']):
                    parameters[8].setErrorMessage("回调函数代码必须定义一个名为 'naming_callback' 的可调用函数")
                else:
                    # 检查函数是否接受两个参数
                    import inspect
                    sig = inspect.signature(callback_namespace['naming_callback'])
                    if len(sig.parameters) != 2:
                        parameters[8].setErrorMessage("naming_callback 函数必须接受两个参数：row 和 callback_fields")
                    else:
                        parameters[8].clearMessage()
            except SyntaxError as e:
                parameters[8].setErrorMessage(f"回调函数代码存在语法错误: {str(e)}")
            except Exception as e:
                parameters[8].setErrorMessage(f"回调函数代码存在错误: {str(e)}")

        return

    def updateMessages(self, parameters):
        """修改每个工具参数的内部验证消息。此方法在内部验证之后调用。"""
        return

    def execute(self, parameters, messages):
        """工具的源代码。"""
        # 获取参数值
        input_features = parameters[0].valueAsText
        output_folder = parameters[1].valueAsText
        output_name = parameters[2].valueAsText
        person_num_field = parameters[3].valueAsText
        start_time_field = parameters[4].valueAsText
        config_path = parameters[5].valueAsText
        dem_paths = parameters[6].valueAsText
        callback_fields = parameters[7].valueAsText.split(';')
        callback_code = parameters[8].valueAsText

        # 如果提供了DEM数据，创建ArcgisElevationProvider
        if dem_paths:
            dem_path_list = dem_paths.split(';')
            # 处理栅格图层
            dem_path_list = [arcpy.Describe(path).catalogPath if arcpy.Exists(path) else path for path in dem_path_list]
            elevation_provider = ArcgisElevationProvider(dem_path_list)
        else:
            elevation_provider = None

        # 创建TrajectorySimulator实例
        simulator = TrajectorySimulator(config_path, elevation_provider)

        # 创建回调函数
        # 创建一个新的命名空间来执行回调函数代码
        callback_namespace = {}
        exec(callback_code, callback_namespace)

        # 从命名空间中获取 naming_callback 函数
        naming_callback = callback_namespace.get('naming_callback')

        if not naming_callback or not callable(naming_callback):
            arcpy.AddError("回调函数 'naming_callback' 未定义或不可调用")
            return

        # 包装回调函数，以传递 callback_fields
        def wrapped_callback(row):
            return naming_callback(row, callback_fields)

        try:
            # 执行轨迹模拟
            simulator.simulate_trajectories(
                input_features,
                output_folder,
                output_name,
                person_num_field=person_num_field,
                start_time_field=start_time_field,
                callback=wrapped_callback,
                callback_fields=callback_fields
            )

            # 输出结果信息
            arcpy.AddMessage(f"航迹模拟完成，结果保存在：{output_folder}\{output_name}")
        except Exception as e:
            arcpy.AddError(f"执行过程中发生错误：{str(e)}")
            arcpy.AddMessage("错误详情：")
            import traceback
            arcpy.AddMessage(traceback.format_exc())

    def postExecute(self, parameters):
        """此方法在输出被处理并添加到显示后执行。"""
        return