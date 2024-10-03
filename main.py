from shapely.geometry import Polygon
from project.config import Config
from project.trajectory_simulator import TrajectorySimulator, ConsoleTrajectoryObserver, FileTrajectoryObserver

def main():
    """主函数，用于运行轨迹模拟"""
    # 加载配置
    config = Config()
    config.load("config.json")
    
    # 创建示例多边形
    polygon = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
    
    # 创建模拟器
    simulator = TrajectorySimulator(config, polygon)
    
    # 添加观察者
    simulator.add_observer(ConsoleTrajectoryObserver())
    simulator.add_observer(FileTrajectoryObserver("trajectory.csv"))
    
    # 运行模拟
    trajectory = simulator.simulate()
    
    print(f"生成的航迹包含 {len(trajectory)} 个点")
    print("航迹已保存到 trajectory.csv")

if __name__ == "__main__":
    main()