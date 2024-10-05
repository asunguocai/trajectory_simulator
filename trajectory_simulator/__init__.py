# 配置
from .config.config import Config

# GPS 相关
from .gps.gps_device import GPSDevice
from .gps.advanced_gps_device import AdvancedGPSDevice
from .gps.gps_device_factory import GPSDeviceFactory
from .gps.gps_observer import GPSObserver
from .gps.sampling_strategy import SamplingStrategy, SamplingStrategyFactory

# 人员相关
from .person.person import Person, PersonFactory, PersonObserver, MovementStrategy

# 观察者
from .observers.trajectory_observer import TrajectoryObserver
from .observers.console_trajectory_observer import ConsoleTrajectoryObserver
from .observers.gpx_trajectory_observer import GPXTrajectoryObserver

# 地形和高程
from .terrain.elevation_provider import ElevationProvider
from .terrain.arcgis_elevation_provider import ArcgisElevationProvider

# 主模拟器
from .trajectory_simulator import TrajectorySimulator

# 巡检任务
from .inspection_task import InspectionTask

# 版本信息
__version__ = "1.0.2"
