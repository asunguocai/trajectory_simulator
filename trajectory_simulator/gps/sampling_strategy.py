from abc import ABC, abstractmethod
from ..config.config import Config

class SamplingStrategy(ABC):
    @abstractmethod
    def should_sample(self, gps_device) -> bool:
        pass

class DistanceSamplingStrategy(SamplingStrategy):
    def __init__(self, sampling_distance: float):
        self.sampling_distance = sampling_distance

    def should_sample(self, gps_device) -> bool:
        current_distance = gps_device.position.distance(gps_device.last_sampled_position)
        return current_distance >= self.sampling_distance

class TimeSamplingStrategy(SamplingStrategy):
    def __init__(self, sampling_interval: float):
        self.sampling_interval = sampling_interval
        self.last_sample_time = 0

    def should_sample(self, gps_device) -> bool:
        current_time = gps_device.current_time
        if current_time - self.last_sample_time >= self.sampling_interval:
            self.last_sample_time = current_time
            return True
        return False

class HybridSamplingStrategy(SamplingStrategy):
    def __init__(self, distance_strategy: DistanceSamplingStrategy, time_strategy: TimeSamplingStrategy):
        self.distance_strategy = distance_strategy
        self.time_strategy = time_strategy

    def should_sample(self, gps_device) -> bool:
        return self.distance_strategy.should_sample(gps_device) or self.time_strategy.should_sample(gps_device)

class SamplingStrategyFactory:
    @staticmethod
    def create_sampling_strategy(config: Config) -> SamplingStrategy:
        strategy_type = config.get(Config.GPS_SAMPLING_STRATEGY_KEY, "distance")
        if strategy_type == "distance":
            sampling_distance = config.get(Config.GPS_SAMPLING_DISTANCE_KEY, 5.0)
            return DistanceSamplingStrategy(sampling_distance)
        elif strategy_type == "time":
            sampling_interval = config.get(Config.GPS_SAMPLING_INTERVAL_KEY, 1.0)
            return TimeSamplingStrategy(sampling_interval)
        elif strategy_type == "hybrid":
            sampling_distance = config.get(Config.GPS_SAMPLING_DISTANCE_KEY, 5.0)
            sampling_interval = config.get(Config.GPS_SAMPLING_INTERVAL_KEY, 1.0)
            return HybridSamplingStrategy(
                DistanceSamplingStrategy(sampling_distance),
                TimeSamplingStrategy(sampling_interval)
            )
        else:
            raise ValueError(f"Unknown sampling strategy: {strategy_type}")