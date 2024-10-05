from ..config.config import Config
from .gps_device import GPSDevice
from .advanced_gps_device import AdvancedGPSDevice

class GPSDeviceFactory:
    """GPS设备工厂类"""

    @staticmethod
    def create_gps_device(config: Config) -> GPSDevice:
        """
        创建GPS设备实例
        
        :param config: 配置对象
        :return: GPS设备实例
        """
        device_type = config.get(Config.GPS_DEVICE_TYPE_KEY, "advanced")
        if device_type == "advanced":
            return AdvancedGPSDevice(config)
        else:
            raise ValueError(f"Unknown GPS device type: {device_type}")