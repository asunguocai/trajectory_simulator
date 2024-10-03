import json
import os
from typing import Dict, Any, Union, List, Tuple
import time
from .elevation_provider import ElevationProvider

class Config:
    """
    配置类，使用单例模式确保全局只有一个配置实例。
    可以从 JSON 文件或 JSON 字符串加载配置。
    """

    _instance = None

    # 模拟相关配置
    TOLERANCE_KEY = "simulation.tolerance"
    CLOSING_DISTANCE_KEY = "simulation.closing_distance" # 最后一条边距离终点的距离容差
    TIME_STEP_KEY = "simulation.time_step"  # 新增

    # GPS设备相关配置
    GPS_DEVICE_TYPE_KEY = "gps.device_type"
    GPS_INITIAL_ACCURACY_KEY = "gps.initial_accuracy"
    GPS_INITIAL_SIGNAL_STRENGTH_MIN_KEY = "gps.initial_signal_strength_min"
    GPS_INITIAL_SIGNAL_STRENGTH_MAX_KEY = "gps.initial_signal_strength_max"
    GPS_MIN_ACCURACY_KEY = "gps.min_accuracy"
    GPS_MAX_ACCURACY_KEY = "gps.max_accuracy"
    GPS_MIN_SIGNAL_STRENGTH_KEY = "gps.min_signal_strength"
    GPS_SAMPLING_DISTANCE_KEY = "gps.sampling_distance"

    # 人员移动策略
    PERSON_MOVEMENT_STRATEGY_KEY = "person.movement_strategy"

    # 人员移动相关配置
    PERSON_DEVIATION_PROBABILITY_KEY = "person.deviation_probability"
    PERSON_MAX_DEVIATION_ANGLE_KEY = "person.max_deviation_angle"
    PERSON_SPEED_RANGE_KEY = "person.speed_range"
    PERSON_CORRECTION_THRESHOLD_KEY = "person.correction_threshold"
    PERSON_CORRECTION_FACTOR_KEY = "person.correction_factor"

    # 轨迹模拟相关配置
    TRAJECTORY_AREA_THRESHOLD_KEY = "trajectory.area_threshold"

    # 添加新的配置键常量
    MAX_SIMULATION_ATTEMPTS_KEY = "simulation.max_attempts"
    GPX_OUTPUT_PATH_KEY = "gpx_output_path"
    ELEVATION_PROVIDER_KEY = "elevation.provider"
    ELEVATION_PROVIDER_PARAMS_KEY = "elevation.provider_params"

    # 添加新的配置键
    GPS_COORDINATE_SYSTEM_KEY = "gps.coordinate_system"
    GPS_TO_WGS84_TRANSFORMER_KEY = "gps.to_wgs84_transformer"
    GPS_TIME_UNIT_KEY = "gps.time_unit"

    def __new__(cls):
        """
        实现单例模式，确保只有一个 Config 实例。
        """
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._config = {}
        return cls._instance

    def load(self, source: Union[str, None] = None):
        """
        加载配置。
        如果 source 是文件路径，则从文件加载；
        如果 source 是 JSON 字符串，则直接解析；
        如果 source 为 None，则保持当前配置不变。

        :param source: 配置源，可以是文件路径、JSON 字符串或 None
        """
        if source is None:
            return

        if os.path.isfile(source):
            self._load_from_file(source)
        else:
            self._load_from_string(source)

    def _load_from_file(self, file_path: str):
        """
        从 JSON 文件加载配置。

        :param file_path: JSON 文件的路径
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self._config.update(json.load(f))
            print(f"配置已从文件 {file_path} 加载")
        except FileNotFoundError:
            print(f"错误: 找不到文件 {file_path}")
        except json.JSONDecodeError:
            print(f"错误: {file_path} 不是有效的 JSON 文件")

    def _load_from_string(self, json_string: str):
        """
        从 JSON 字符串加载配置。

        :param json_string: JSON 格式的配置字符串
        """
        try:
            self._config.update(json.loads(json_string))
        except json.JSONDecodeError:
            print("错误: 提供的字符串不是有效的 JSON")

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值。如果键不存在，则返回默认值。

        可配置的信息及其作用：
        - simulation.initial_time: 模拟开始的初始时间（float，单位：秒）
        - simulation.initial_position.x: 初始位置的X坐标（float）
        - simulation.initial_position.y: 初始位置的Y坐标（float）
        - gps.device_type: GPS设备类型，目前只支持"advanced"（string）
        - gps.initial_accuracy: GPS初始精度（float，单位：米）
        - gps.initial_signal_strength_min: GPS初始最小信号强度（float，范围：0-1）
        - gps.initial_signal_strength_max: GPS初始最大信号强度（float，范围：0-1）
        - gps.min_accuracy: GPS最小精度（float，单位：米）
        - gps.max_accuracy: GPS最大精度（float，单位：米）
        - gps.min_signal_strength: GPS最小信号强度（float，范围：0-1）
        - person.movement_strategy: 人员移动策略，可选"simple"或"advanced"（string）
        - simulation.max_attempts: 模拟轨迹生成的最大尝试次数（int）

        :param key: 配置键
        :param default: 默认值
        :return: 配置值或默认值
        """
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any):
        """
        设置配置值。

        :param key: 配置键
        :param value: 配置值
        """
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        config[keys[-1]] = value

    def __getitem__(self, key: str) -> Any:
        """
        允许使用字典语法访问配置。

        :param key: 配置键
        :return: 配置值
        :raises KeyError: 如果键不存在
        """
        return self.get(key)

    def __setitem__(self, key: str, value: Any):
        """
        允许使用字典语法设置配置。

        :param key: 配置键
        :param value: 配置值
        """
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        """
        检查配置是否包含某个键。

        :param key: 配置键
        :return: 是否包含该键
        """
        return self.get(key) is not None

    def __str__(self) -> str:
        """
        返回配置的字符串表示。

        :return: JSON 格式的配置字符串
        """
        return json.dumps(self._config, indent=2, ensure_ascii=False)

    def save(self, file_path: str):
        """
        将当前配置保存到 JSON 文件。

        :param file_path: 保存的文件路径
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            print(f"配置已保存到文件 {file_path}")
        except Exception as e:
            print(f"保存配置时发生错误: {e}")

    def get_elevation_provider(self) -> ElevationProvider:
        provider_type = self.get(self.ELEVATION_PROVIDER_KEY, "default")
        provider_params = self.get(self.ELEVATION_PROVIDER_PARAMS_KEY, {})

        if provider_type == "arcgis":
            from .arcgis_elevation_provider import ArcgisElevationProvider
            return ArcgisElevationProvider(provider_params.get("dem_path_list", []))
        else:
            # 默认使用一个简单的高程提供者，总是返回0米高程
            class DefaultElevationProvider(ElevationProvider):
                def get_elevation(self, lon: float, lat: float) -> float:
                    return 0.0
                def batch_get_elevation(self, lon_lat_list: List[Tuple[float, float]]) -> List[float]:
                    return [0.0] * len(lon_lat_list)
            return DefaultElevationProvider()

    def get_coordinate_system(self):
        return self.get(self.GPS_COORDINATE_SYSTEM_KEY, "EPSG:4510")

    def get_time_unit(self):
        """获取时间单位，默认为秒"""
        return self.get(self.GPS_TIME_UNIT_KEY, "second")