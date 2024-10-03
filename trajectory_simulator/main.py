from shapely.geometry import Polygon
from config import Config
from trajectory_simulator import TrajectorySimulator, ConsoleTrajectoryObserver, FileTrajectoryObserver
from trajectory_simulator import POSITION_KEY
from gpx_trajectory_observer import GPXTrajectoryObserver
import time
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Point

def plot_trajectory(polygon, trajectory):
    fig, ax = plt.subplots()
    
    # 绘制原多边形
    x, y = polygon.exterior.xy
    ax.plot(x, y, 'r-', linewidth=2, label='Original Polygon')
    
    # 绘制生成的航迹
    trajectory_line = LineString([(point[POSITION_KEY].x, point[POSITION_KEY].y) for point in trajectory])
    x, y = trajectory_line.xy
    ax.plot(x, y, 'b-', linewidth=1, label='Generated Trajectory')
    
    ax.set_aspect('equal', 'box')
    ax.legend()
    plt.title('Original Polygon vs Generated Trajectory')
    plt.savefig('trajectory_comparison.png')
    plt.close()


def main():
    """主函数，用于运行轨迹模拟"""
    # 加载配置
    config = Config()
    config.load('project/config.json')
    
    # 创建多个示例多边形
    polygons = [
        Polygon([
            (0, 0), (20, 10), (40, 5), (60, 15), (80, 10), (100, 0),
            (110, 20), (105, 40), (115, 60), (110, 80), (100, 100),
            (80, 95), (60, 105), (40, 95), (20, 105), (0, 100),
            (-10, 80), (-5, 60), (-15, 40), (-10, 20)
        ]),
        Polygon([
            (0, 0), (50, 0), (50, 50), (0, 50)
        ]),
        Polygon([
            (0, 0), (30, 0), (45, 30), (30, 60), (0, 60), (-15, 30)
        ])
    ]
    # 创建模拟器
    simulator = TrajectorySimulator(config)
    simulator.add_observer(ConsoleTrajectoryObserver())

    for i, polygon in enumerate(polygons):
        print(f"\n正在模拟多边形 {i+1}")
        # 添加观察者
        
        simulator.add_observer(FileTrajectoryObserver(f"trajectory_{i+1}.csv"))
        
        simulator.set_time(1625097600)
        simulator.set_position(Point(polygon.exterior.coords[0]))
        
        # 创建并添加GPX观察者
        gpx_config = {
            "creator": "ArcGIS Trajectory Simulator",
            "metadata_name": f"Simulated Inspection Trajectory {i+1}",
            "track_name": f"Inspection Route {i+1}",
            "metadata_description": f"A simulated trajectory for inspection tasks - Polygon {i+1}",
            "metadata_author": "Your Name or Organization"
        }
        gpx_observer = GPXTrajectoryObserver(f"output_trajectory_{i+1}.gpx", gpx_config, config)
        simulator.add_observer(gpx_observer)
        
        # 运行模拟
        trajectory = simulator.simulate(start_position=Point(polygon.exterior.coords[0]), start_time=1625097600, polygon=polygon)
        simulator.remove_observer(gpx_observer)
        # 绘制并保存轨迹对比图
        plot_trajectory(polygon, trajectory)
        print(f"航迹对比图已保存为 trajectory_comparison_{i+1}.png")

        print(f"生成的航迹包含 {len(trajectory)} 个点")
        print(f"航迹已保存到 trajectory_{i+1}.csv")

if __name__ == "__main__":
    main()