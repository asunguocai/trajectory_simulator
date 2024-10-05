from abc import ABC, abstractmethod
from typing import Dict

class GPSObserver(ABC):
    @abstractmethod
    def on_gps_update(self, data: Dict):
        """
        当 GPS 数据更新时调用
        
        :param data: 更新的 GPS 数据
        """
        pass

    @abstractmethod
    def on_gps_start_recording(self):
        """
        当 GPS 开始记录时调用
        """
        pass

    @abstractmethod
    def on_gps_stop_recording(self):
        """
        当 GPS 停止记录时调用
        """
        pass

    @abstractmethod
    def on_gps_pause_recording(self):
        """
        当 GPS 暂停记录时调用
        """
        pass

    @abstractmethod
    def on_gps_resume_recording(self):
        """
        当 GPS 恢复记录时调用
        """
        pass