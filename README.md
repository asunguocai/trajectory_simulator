# 轨迹模拟器 (Trajectory Simulator)

轨迹模拟器是一个专门用于生成模拟巡检轨迹的Python包。它能够根据给定的面要素类，模拟生成对应的航迹数据，同时满足特定的要求，如覆盖面积、真实性和平滑度。这个工具特别适用于需要模拟人员在复杂环境中进行巡检的场景。

## 实现思路

1. 轨迹生成算法
   - 初始化：从多边形顶点中选择一个作为起点。
   - 路径规划：按顺序遍历多边形的顶点，将每对相邻顶点作为一段巡检路径。
   - 轨迹模拟：对于每段路径，模拟人员的行走过程，包括速度变化、方向偏离和GPS采样。
   - 验证轨迹：检查生成的轨迹是否有效（覆盖面积是否达到要求）。
   - 重试机制：如果轨迹无效，重新尝试生成，直到达到最大尝试次数。

2. GPS设备模拟
   - 信号强度变化：随机模拟信号强度的波动。
   - 精度变化：根据信号强度调整GPS定位精度。
   - 位置抖动：模拟GPS定位的微小抖动。

3. 高程数据集成
   - 使用ArcGIS的高程数据提供器，为轨迹点添加真实的高程信息。

## 主要特性

- 高度真实的人员移动模拟：考虑了复杂环境下的行走特性，包括速度变化、方向偏离和纠正。
- 精确的GPS设备模拟：模拟GPS信号强度和精度的动态变化，提供更真实的位置数据。
- 灵活的高程数据集成：支持多种高程数据提供者，包括ArcGIS高程数据。
- 多样化的输出格式：支持GPX等标准格式，便于与其他GIS工具集成。
- 可配置性强：通过JSON配置文件，可以灵活调整各种模拟参数。
- 观察者模式：支持自定义观察者，方便实时监控和记录模拟过程。

## 安装

使用pip安装：

```bash
pip install trajectory_simulator
```

## 快速开始

以下是一个基本的使用示例：

```python
from trajectory_simulator import TrajectorySimulator, Config
from shapely.geometry import Polygon, Point
import time

# 加载配置
config = Config()
config.load('config.json')

# 创建模拟器
simulator = TrajectorySimulator(config)

# 定义多边形区域
polygon = Polygon([(0, 0), (0, 100), (100, 100), (100, 0)])

# 设置起始时间和位置
start_time = time.time()
start_position = Point(0, 0)

# 执行模拟
trajectory = simulator.simulate(start_time, start_position, polygon)

print(f"生成的轨迹点数：{len(trajectory)}")
```

## 配置说明

配置文件（config.json）包含以下主要部分：

```json
{
  "simulation": {
    "time_step": 1.0,              // 模拟的时间步长（秒）
    "tolerance": 0.5,              // 轨迹生成的容差（米）
    "closing_distance": 0.2,       // 最后一条边距离终点的距离容差（米）
    "max_attempts": 3              // 最大模拟尝试次数
  },
  "gps": {
    "device_type": "advanced",     // GPS设备类型，目前支持"advanced"
    "initial_accuracy": 5.0,       // 初始GPS精度（米）
    "initial_signal_strength_min": 0.8,  // 初始最小信号强度（0-1）
    "initial_signal_strength_max": 1.0,  // 初始最大信号强度（0-1）
    "min_accuracy": 2.5,           // 最小GPS精度（米）
    "max_accuracy": 12.0,          // 最大GPS精度（米）
    "min_signal_strength": 0.2,    // 最小信号强度（0-1）
    "sampling_distance": 5.0,      // GPS采样距离（米）
    "coordinate_system": "EPSG:4510",  // 使用的坐标系统
    "time_unit": "second"          // 时间单位，可选"second"、"millisecond"、"minute"、"hour"
  },
  "person": {
    "movement_strategy": "realistic",  // 移动策略，可选"realistic"或"simple"
    "deviation_probability": 0.4,   // 偏航概率（0-1）
    "max_deviation_angle": 23,      // 最大偏航角度（度）
    "speed_range": [0.8, 1.5],      // 速度范围（米/秒）
    "correction_threshold": 5.0,    // 航向修正阈值（米）
    "correction_factor": 0.5        // 航向修正因子（0-1）
    // 注意：correction_factor越大，修正越强烈
  },
  "trajectory": {
    "area_threshold": 0.9           // 轨迹覆盖面积阈值（0-1）
    // 生成的轨迹面积与原多边形面积的比例需大于此值
  },
  "elevation": {
    "provider": "default"           // 高程数据提供者，可选"default"或"arcgis"
    // 如果选择"arcgis"，需要额外配置ArcGIS相关参数
  }
}
```

### 参数说明

1. simulation
   - time_step: 控制模拟的精度，较小的值会增加计算量但提高精度。
   - tolerance: 允许轨迹与多边形边界的最大偏差。
   - closing_distance: 结束模拟时，与起点的最大允许距离。
   - max_attempts: 生成有效轨迹的最大尝试次数。

2. gps
   - device_type: 目前仅支持"advanced"，未来可能添加其他类型。
   - initial_accuracy 到 max_accuracy: 控制GPS精度的范围。
   - initial_signal_strength_min/max 和 min_signal_strength: 控制GPS信号强度的范围。
   - sampling_distance: 控制GPS点的采样间隔。
   - coordinate_system: 指定使用的坐标系统，确保与输入数据一致。
   - time_unit: 指定时间单位，影响速度和时间步长的解释。

3. person
   - movement_strategy: "realistic"考虑更多现实因素，"simple"为简化模型。
   - deviation_probability: 控制偏航频率。
   - max_deviation_angle: 控制偏航程度。
   - speed_range: 设定人员移动速度的范围。
   - correction_threshold: 当偏离路径超过此距离时触发修正。
   - correction_factor: 控制修正的强度。

4. trajectory
   - area_threshold: 确保生成的轨迹充分覆盖原始多边形区域。

5. elevation
   - provider: 选择高程数据的来源。"default"为平面（高程为0），"arcgis"使用ArcGIS数据。

注意：这些参数会显著影响模拟的结果和性能。根据具体需求和场景调整这些参数可以获得更好的模拟效果。

## 添加自定义观察者

要添加自定义观察者，需要继承TrajectoryObserver类并实现相应的方法。例如：

```python
from trajectory_simulator import TrajectoryObserver

class CustomObserver(TrajectoryObserver):
    def on_start_recording(self):
        print("开始记录")

    def on_stop_recording(self):
        print("停止记录")

    def on_data_update(self, data: Dict):
        print(f"新数据点: {data}")

    def on_pause_recording(self):
        print("暂停记录")

    def on_resume_recording(self):
        print("恢复记录")

# 使用自定义观察者
custom_observer = CustomObserver()
simulator.add_observer(custom_observer)
```

## 高级用法

### 自定义高程数据提供者

如果需要使用自定义的高程数据源，可以实现ElevationProvider接口：

```python
from trajectory_simulator import ElevationProvider
from typing import List, Tuple

class CustomElevationProvider(ElevationProvider):
    def get_elevation(self, lon: float, lat: float) -> float:
        # 实现您的高程获取逻辑
        pass

    def batch_get_elevation(self, lon_lat_list: List[Tuple[float, float]]) -> List[float]:
        # 实现批量高程获取逻辑
        pass

# 在配置中使用自定义高程提供者
config.set("elevation.provider", "custom")
config.set("elevation.provider_params", {"your_custom_param": "value"})
```

### 自定义人员移动策略

可以通过创建新的移动策略来自定义人员的移动行为：

```python
from trajectory_simulator import MovementStrategy, Config, Point

class CustomMovementStrategy(MovementStrategy):
    def move(self, gps_position: Point, target: Point, elapsed_time: float, config: Config) -> Point:
        # 实现您的自定义移动逻辑
        pass

# 在Person类中使用自定义移动策略
person.movement_strategy = CustomMovementStrategy()
```

## 注意事项

- 确保输入的多边形数据坐标系统与配置文件中指定的坐标系统一致。
- 高程数据的精度和覆盖范围会影响生成轨迹的真实性。
- 对于大型或复杂的巡检区域，可能需要增加模拟尝试次数或调整其他参数。

## 故障排除

1. 轨迹生成失败：
   - 检查配置文件参数是否合理
   - 验证输入多边形的有效性
   - 增加模拟尝试次数

2. 生成的轨迹不够真实：
   - 调整人员移动参数
   - 使用更精确的高程数据
   - 增加GPS模拟的复杂度

3. 性能问题：
   - 减小时间步长
   - 使用更高效的高程数据提供者
   - 优化观察者实现
   - 增加采样距离
   - 航迹生成完后，统一添加高程数据

## 贡献

欢迎各种形式的贡献，包括但不限于：

- 报告问题和提出建议
- 提交改进代码的拉取请求
- 完善文档和示例
- 添加新功能或优化现有功能

在提交大的改动之前，请先开issue讨论您想要改变的内容。

## 许可证

本项目采用MIT许可证。详情请见LICENSE文件。