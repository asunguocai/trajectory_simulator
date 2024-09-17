import random
import math
import arcpy
import datetime
from pyproj import Transformer
import xml.etree.ElementTree as ET
import os
import json
from elevation_provider import ElevationProvider, DefaultElevationProvider

class Person:
    """
    表示一个行走的人,包含体力系统、速度计算和偏航特性。

    属性:
        number (int): 人员编号
        max_speed (float): 最大行走速度(米/秒)
        min_speed (float): 最小行走速度(米/秒)
        max_stamina (float): 最大体力值
        stamina_consumption_base (float): 体力消耗基础值
        stamina_recovery_rate (float): 每秒恢复的体力值(休息时)
        walking_recovery_factor (float): 行走时恢复速度为休息时的比例
        min_stamina_to_walk (float): 恢复到该体力值才继续行走
        max_deviation_angle (float): 最大偏航角度(弧度)
        deviation_probability (float): 偏航概率
    """

    def __init__(self, 
                 number,
                 max_speed=3.0, 
                 min_speed=0.7, 
                 max_stamina=100, 
                 stamina_consumption_base=0.1,
                 stamina_recovery_rate=0.5,
                 walking_recovery_factor=0.2,
                 min_stamina_to_walk=40,
                 max_deviation_angle=math.radians(24),
                 deviation_probability=0.6):
        self.number = number
        self.max_speed = max_speed
        self.min_speed = min_speed
        self.max_stamina = max_stamina
        self.current_stamina = max_stamina
        self.stamina_consumption_base = stamina_consumption_base
        self.stamina_recovery_rate = stamina_recovery_rate
        self.walking_recovery_factor = walking_recovery_factor
        self.min_stamina_to_walk = min_stamina_to_walk
        self.max_deviation_angle = max_deviation_angle
        self.deviation_probability = deviation_probability
        self.current_deviation = 0  # 当前偏航角度

    def get_current_speed(self):
        """计算当前速度,基于当前体力值。"""
        stamina_factor = self.current_stamina / self.max_stamina
        return self.min_speed + (self.max_speed - self.min_speed) * stamina_factor

    def consume_stamina(self, distance, speed):
        """消耗体力,基于行走距离和速度。"""
        speed_factor = math.log(speed - self.min_speed + 1, self.max_speed - self.min_speed + 1)
        stamina_consumed = distance * self.stamina_consumption_base * (1 + speed_factor)
        self.current_stamina = max(0, self.current_stamina - stamina_consumed)
        return stamina_consumed

    def recover_stamina(self, time_seconds, is_walking=False):
        """恢复体力。"""
        recovery_rate = self.stamina_recovery_rate * (self.walking_recovery_factor if is_walking else 1)
        stamina_recovered = time_seconds * recovery_rate
        self.current_stamina = min(self.max_stamina, self.current_stamina + stamina_recovered)
        return stamina_recovered

    def needs_rest(self):
        """判断是否需要休息。"""
        return self.current_stamina < self.min_stamina_to_walk

    def rest_until_ready(self):
        """休息直到体力恢复到可以行走的水平。"""
        time_to_rest = (self.min_stamina_to_walk - self.current_stamina) / self.stamina_recovery_rate
        self.recover_stamina(time_to_rest)
        return time_to_rest

    def get_deviation_angle(self, current_position, target_position):
        """
        获取当前偏航角度,并在需要时进行纠正。

        算法逻辑:
        1. 计算理想方向向量和角度
        2. 根据偏航概率决定是否生成新的随机偏航
        3. 如果不生成新偏航,则对当前偏航进行纠正
        4. 返回最终的偏航角度

        参数:
            current_position (arcpy.Point): 当前位置
            target_position (arcpy.Point): 目标位置

        返回:
            float: 当前偏航角度(弧度)
        """
        # 计算理想方向向量
        ideal_vector = (target_position.X - current_position.X, target_position.Y - current_position.Y)
        # 计算理想角度
        ideal_angle = math.atan2(ideal_vector[1], ideal_vector[0])

        if random.random() < self.deviation_probability:
            # 生成新的随机偏航
            self.current_deviation = random.uniform(-self.max_deviation_angle, self.max_deviation_angle)
        else:
            # 对当前偏航进行纠正
            correction_strength = 0.5  # 纠正强度,可以根据需要调整
            self.current_deviation = self.current_deviation * (1 - correction_strength)

        # 返回最终角度(理想角度 + 偏航角度)
        return ideal_angle + self.current_deviation

class Team:
    """表示一个由多个Person组成的团队。"""

    def __init__(self, members):
        self.members = members

    def get_person_by_number(self, number):
        """根据编号获取Person对象。"""
        for person in self.members:
            if person.number == number:
                return person
        return None

    def get_random_person(self):
        """随机获取一个Person对象。"""
        return random.choice(self.members)

class TrajectorySimulator:
    """
    轨迹模拟器类,用于生成和管理模拟轨迹。

    属性:
        team (Team): 人员团队对象
        simulation_params (dict): 模拟参数
        input_crs (arcpy.SpatialReference): 输入坐标系
        output_crs (arcpy.SpatialReference): 输出坐标系(WGS84)
        transformer (Transformer): 坐标转换器
        elevation_provider (ElevationProvider): 高程提供者
    """

    def __init__(self, config_path=None, elevation_provider=None):
        """初始化轨迹模拟器。"""
        self.team, self.simulation_params = self._load_config(config_path)
        self.input_crs = None
        self.output_crs = arcpy.SpatialReference(4326)  # WGS84
        self.transformer = None
        self.elevation_provider = elevation_provider or DefaultElevationProvider()

    def _load_config(self, config_path=None):
        """从JSON文件加载配置。如果文件不存在或未提供,则使用默认配置。"""
        default_config = {
            "persons": [
                {
                    "number": 1, # 人员编号
                    "max_speed": 1.5, # 最大速度
                    "min_speed": 0.5, # 最小速度
                    "max_stamina": 100, # 最大体力
                    "stamina_consumption_base": 0.05, # 体力消耗基础值
                    "stamina_recovery_rate": 0.1, # 体力恢复率
                    "walking_recovery_factor": 0.3, # 行走时恢复速度为休息时的比例
                    "min_stamina_to_walk": 20, # 恢复到该体力值才继续行走
                    "max_deviation_angle": math.radians(15), # 最大偏航角度
                    "deviation_probability": 0.3 # 偏航概率 
                },
                {
                    "number": 2,
                    "max_speed": 1.8,
                    "min_speed": 0.6,
                    "max_stamina": 120,
                    "stamina_consumption_base": 0.04,
                    "stamina_recovery_rate": 0.12,
                    "walking_recovery_factor": 0.35,
                    "min_stamina_to_walk": 25,
                    "max_deviation_angle": math.radians(12),
                    "deviation_probability": 0.25
                },
                {
                    "number": 3, # 人员编号
                    "max_speed": 1.2, # 最大速度
                    "min_speed": 0.4, # 最小速度
                    "max_stamina": 100, # 最大体力
                    "stamina_consumption_base": 0.06, # 体力消耗基础值
                    "stamina_recovery_rate": 0.1, # 体力恢复率
                    "walking_recovery_factor": 0.3, # 行走时恢复速度为休息时的比例
                    "min_stamina_to_walk": 25, # 恢复到该体力值才继续行走
                    "max_deviation_angle": math.radians(18), # 最大偏航角度
                    "deviation_probability": 0.22 # 偏航概率 
                },
                {
                    "number": 4, # 人员编号
                    "max_speed": 1.7, # 最大速度
                    "min_speed": 0.8, # 最小速度
                    "max_stamina": 100, # 最大体力
                    "stamina_consumption_base": 0.055, # 体力消耗基础值
                    "stamina_recovery_rate": 0.15, # 体力恢复率
                    "walking_recovery_factor": 0.3, # 行走时恢复速度为休息时的比例
                    "min_stamina_to_walk": 20, # 恢复到该体力值才继续行走
                    "max_deviation_angle": math.radians(16), # 最大偏航角度
                    "deviation_probability": 0.3 # 偏航概率 
                },
            ],
            "simulation_params": {
                "sample_distance": 5, # 采样距离
                "simulate_backtrack": False, # 是否模拟回头
                "back_count": 2, # 最大回头次数
                "back_probability": 0.1, # 回头概率
                "max_retries": 40, # 最大重试次数
                "area_tolerance_min": 0.95, # 最小面积比率
                "area_tolerance_max": 1.00 # 最大面积比率
            }
        }

        if config_path:
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                print(f"已加载配置文件: {config_path}")
            except FileNotFoundError:
                print(f"配置文件 {config_path} 不存在，使用默认配置。")
                config = default_config
        else:
            print("未提供配置文件路径，使用默认配置。")
            config = default_config

        persons = [Person(**person_config) for person_config in config['persons']]
        team = Team(persons)
        
        return team, config['simulation_params']

    def simulate_trajectories(self, input_features, output_folder, output_name = "simulated_trajectories",person_num_field=None, start_time_field=None,  callback=None, callback_fields=None):
        """模拟多个多边形的航迹。"""
        arcpy.env.overwriteOutput = True

        output_features = os.path.join(output_folder, output_name)
        self._create_output_feature_class(output_folder, output_name, input_features)

        self.input_crs = arcpy.Describe(input_features).spatialReference
        self.transformer = Transformer.from_crs(self.input_crs.factoryCode, self.output_crs.factoryCode, always_xy=True)

        log_file = os.path.join(output_folder, "simulation_log.txt")

        fields = ['SHAPE@'] + (callback_fields if callback_fields else [])
        if person_num_field and person_num_field not in fields:
            fields.append(person_num_field)
        if start_time_field and start_time_field not in fields:
            fields.append(start_time_field)

        with arcpy.da.SearchCursor(input_features, fields) as search_cursor, \
             arcpy.da.InsertCursor(output_features, ['SHAPE@', 'START_TIME', 'END_TIME', 'TOTAL_DIST', 'PERSON_NUM', 'FEATURE_ID', 'AREA', 'ELEVATION']) as insert_cursor, \
             open(log_file, 'w') as log:
            for row in search_cursor:
                self._process_polygon(row, person_num_field, start_time_field, callback, insert_cursor, log, output_folder)

        print("航迹生成完成,结果保存在：", output_folder)
        return output_folder

    def _create_output_feature_class(self, output_folder, output_name, input_features):
        """创建输出要素类并添加必要的字段"""
        output_features = os.path.join(output_folder, output_name)
        print(output_features)
        arcpy.CreateFeatureclass_management(output_folder, output_name, 
                                            'POLYLINE', spatial_reference=arcpy.Describe(input_features).spatialReference)

        arcpy.AddField_management(output_features, "START_TIME", "DATE")
        arcpy.AddField_management(output_features, "END_TIME", "DATE")
        arcpy.AddField_management(output_features, "TOTAL_DIST", "DOUBLE")
        arcpy.AddField_management(output_features, "PERSON_NUM", "LONG")
        arcpy.AddField_management(output_features, "FEATURE_ID", "TEXT", field_length=50)
        arcpy.AddField_management(output_features, "AREA", "DOUBLE")
        arcpy.AddField_management(output_features, "ELEVATION", "DOUBLE")  # 新增高程字段

    def _process_polygon(self, row, person_num_field, start_time_field, callback, insert_cursor, log, output_folder):
        """
        处理单个多边形,生成轨迹并插入结果

        算法逻辑:
        1. 提取多边形和相关信息
        2. 选择执行轨迹的人员
        3. 解析起始时间
        4. 尝试生成满足条件的轨迹:
            a. 生成轨迹
            b. 检查生成的轨迹是否满足面积要求
            c. 如果满足要求,插入结果并创建GPX文件
            d. 如果不满足要求,重试直到达到最大重试次数
        5. 记录日志信息

        参数:
            row: 输入要素的一行数据
            person_num_field (str): 人员编号字段名
            start_time_field (str): 起始时间字段名
            callback (function): 用于生成特征ID的回调函数
            insert_cursor: 用于插入结果的游标
            log: 日志文件对象
            output_folder (str): 输出文件夹路径
        """
        polygon = row[0]
        original_area = polygon.area
        person = self._select_person(row, person_num_field)
        feature_id = callback(row[1:]) if callback else f"feature_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

        start_time = self._parse_start_time(row, start_time_field)
        if start_time is None:
            log.write(f"警告：无法解析多边形 {feature_id} 的起始时间,使用当前时间。\n")
            start_time = datetime.datetime.now()

        for attempt in range(self.simulation_params['max_retries']):
            trajectory, points_with_time, total_distance = self._generate_trajectory(
                polygon, 
                person, 
                sample_distance=self.simulation_params['sample_distance'],
                start_time=start_time,
                simulate_backtrack=self.simulation_params['simulate_backtrack'],
                back_count=self.simulation_params['back_count'],
                back_probability=self.simulation_params['back_probability']
            )
            if trajectory and len(points_with_time) >= 3:  # 确保至少有3个点
                try:
                    trajectory_polygon = arcpy.Polygon(arcpy.Array([p[0] for p in points_with_time]))
                    trajectory_area = trajectory_polygon.area
                    area_ratio = trajectory_area / original_area
                    log.write("-----------------------------------\n")
                    log.write(f"第{attempt+1}次尝试\n")
                    log.write(f"feature_id: {feature_id}\n")
                    log.write(f"轨迹面积: {trajectory_area}, 原始面积: {original_area}, 面积比率: {area_ratio}\n")
                    if self.simulation_params['area_tolerance_min'] <= area_ratio <= self.simulation_params['area_tolerance_max']:
                        # 只有在面积精度达到要求时，才添加高程信息
                        points_with_elevation = self._add_elevation_to_trajectory(points_with_time)
                        
                        # 插入结果
                        insert_cursor.insertRow([trajectory, points_with_elevation[0][1], points_with_elevation[-1][1], 
                                                 total_distance, person.number, feature_id, trajectory_area, points_with_elevation[0][2]])
                        
                        # 创建GPX文件和txt文件，传递重试次数
                        self._create_gpx(points_with_elevation, os.path.join(output_folder, f"{feature_id}.gpx"), 
                                         total_distance, trajectory_area, attempt + 1, area_ratio)
                        break
                    else:
                        log.write(f"面积比率 {area_ratio} 不在允许范围内，继续尝试。\n")
                except RuntimeError as e:
                    log.write(f"警告：无法为多边形 {feature_id} 创建轨迹多边形: {str(e)}\n")
                    continue
            else:
                log.write(f"警告：无法为多边形 {feature_id} 生成有效的航迹,点数不足或轨迹无效。\n")
                continue
        else:  # FOR-ELSE语法，当for循环正常执行完毕后，执行else语句
            log.write(f"错误：无法为多边形 {feature_id} 生成满足面积要求的航迹,已达到最大重试次数。\n")

    def _select_person(self, row, person_num_field):
        """选择执行轨迹的人员"""
        if person_num_field:
            person_num = row[row.index(person_num_field)]
            person = self.team.get_person_by_number(person_num)
            if not person:
                person = self.team.get_random_person()
        else:
            person = self.team.get_random_person()
        return person

    def _parse_start_time(self, row, start_time_field):
        """解析起始时间字段"""
        if start_time_field and start_time_field in row:
            time_str = row[row.index(start_time_field)]
            try:
                return datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ") # 将UTC时间字符串转换为datetime对象
            except ValueError:
                return None
        return None

    def _generate_trajectory(self, polygon, person:Person, sample_distance, start_time, simulate_backtrack, back_count, back_probability):
        """
        生成单个多边形的航迹。

        算法流程:
        1. 初始化:
           - 提取多边形的有效顶点
           - 初始化轨迹点列表、当前时间和总距离
           - 计算实际起点和终点，以模拟随机起点并保证航迹闭合

        2. 主循环 (遍历多边形的边):
           对于每条边 (从当前顶点到下一个顶点):
           a. 计算当前边的方向向量和长度
           b. 初始化当前点为边的起点
           c. 子循环 (在当前边上移动):
              - 检查是否需要休息，如需要则进行休息并添加休息点
              - 检查是否需要回头，如果需要则回头
              - 计算当前速度和偏航角度
              - 根据偏航角度调整移动方向
              - 计算新的位置点
              - 更新时间、距离和体力
              - 将新点添加到轨迹中
              - 如果到达边的终点，结束子循环

        3. 返回结果:
           - 创建轨迹线对象
           - 返回轨迹线对象、轨迹点列表和总距离

        参数:
        - polygon (arcpy.Polygon): 输入的多边形
        - person (Person): 行走的人物对象
        - sample_distance (float): 采样距离(米)
        - start_time (datetime): 起始时间
        - simulate_backtrack (bool): 是否模拟回头
        - back_count (int): 最大回头次数
        - back_probability (float): 回头概率

        返回:
        tuple: (航迹线对象, 航迹点列表, 总距离)
        """
        # 获取多边形的顶点
        vertices = polygon.getPart(0)[:-1]
        valid_vertices = [v for v in vertices if v]
        if len(valid_vertices) < 2:
            return None, None, 0

        trajectory = []
        current_time = start_time
        total_distance = 0
        
        speed = person.get_current_speed() # 获取当前速度
        # 计算实际起点（向后退一步,以模拟随机起点）
        start_point = valid_vertices[0]
        next_point = valid_vertices[1]
        vector_to_next = (next_point.X - start_point.X, next_point.Y - start_point.Y)
        vector_length = math.sqrt(vector_to_next[0]**2 + vector_to_next[1]**2)
        unit_vector = (vector_to_next[0] / vector_length, vector_to_next[1] / vector_length)
        actual_start = arcpy.Point(
            start_point.X - unit_vector[0] * speed,
            start_point.Y - unit_vector[1] * speed
        )

        # 计算实际终点（向前进一步,以模拟随机起点，并保证航迹闭合【不一定重合】）
        end_point_index = len(valid_vertices) - 1
        end_point = valid_vertices[end_point_index]
        while end_point_index > 0:
            if valid_vertices[end_point_index] == start_point:
                end_point = valid_vertices[end_point_index + 1]
            end_point_index -= 1

        vector_to_end = (end_point.X - start_point.X, end_point.Y - start_point.Y)
        vector_length = math.sqrt(vector_to_end[0]**2 + vector_to_end[1]**2)
        unit_vector = (vector_to_end[0] / vector_length, vector_to_end[1] / vector_length)
        actual_end = arcpy.Point(
            start_point.X - unit_vector[0] * speed,
            start_point.Y - unit_vector[1] * speed
        )

        # 将实际起点和终点添加到顶点列表
        valid_vertices = [actual_start] + valid_vertices + [actual_end]

        i = 0
        backtrack_count = 0

        while i < len(valid_vertices) - 1:
            point_a, point_b = valid_vertices[i], valid_vertices[i + 1]
            
            # 计算当前段的方向向量和长度
            direction_vector = (point_b.X - point_a.X, point_b.Y - point_a.Y)
            # 计算当前段的长度
            segment_distance = math.sqrt(direction_vector[0]**2 + direction_vector[1]**2)
            
            current_point = arcpy.Point(point_a.X, point_a.Y)  # 当前点的位置
            remaining_distance = segment_distance  # 当前段剩余的距离
            segment_trajectory = []

            while remaining_distance > 0:
                if person.needs_rest():
                    rest_time = person.rest_until_ready()
                    current_time += datetime.timedelta(seconds=rest_time)
                    segment_trajectory.append((current_point, current_time))
                    continue

                speed = person.get_current_speed()
                # 在每一步后检查是否需要局部回头
                next_step_point = point_b
                if simulate_backtrack and random.random() < back_probability and backtrack_count < back_count:
                    next_step_point = valid_vertices[i-1] if i > 0 else valid_vertices[0] # 回头， 如果是第一个点，则回头向起点
                    backtrack_count += 1
                angle_deviation = person.get_deviation_angle(current_point, next_step_point)
                
                rotated_vector = (
                    math.cos(angle_deviation) * direction_vector[0] - math.sin(angle_deviation) * direction_vector[1],
                    math.sin(angle_deviation) * direction_vector[0] + math.cos(angle_deviation) * direction_vector[1]
                )
                vector_length = math.sqrt(rotated_vector[0]**2 + rotated_vector[1]**2)
                unit_vector = (rotated_vector[0] / vector_length, rotated_vector[1] / vector_length)
                
                step_distance = min(sample_distance, remaining_distance)
                new_point = arcpy.Point(
                    current_point.X + step_distance * unit_vector[0],
                    current_point.Y + step_distance * unit_vector[1]
                )
                
                time_delta = datetime.timedelta(seconds=step_distance / speed)
                current_time += time_delta
                
                person.consume_stamina(step_distance, speed)
                person.recover_stamina(time_delta.total_seconds(), is_walking=True)
                
                segment_trajectory.append((new_point, current_time))
                current_point = new_point
                remaining_distance -= step_distance
                total_distance += step_distance

            trajectory.extend(segment_trajectory)
            i += 1


        return arcpy.Polyline(arcpy.Array([p[0] for p in trajectory])), trajectory, total_distance

    def _add_elevation_to_trajectory(self, trajectory):
        """
        为轨迹批量添加高程信息
        """
        # 提取所有点的坐标
        points = [point for point, time in trajectory]
        
        # 转换坐标并获取高程
        lon_lat_list = [self.transformer.transform(point.X, point.Y) for point in points]
        elevations = self.elevation_provider.batch_get_elevation(lon_lat_list)
        
        result = [(point, time, elevation) for (point, time), elevation in zip(trajectory, elevations)]

        return result

    def _create_gpx(self, points_with_time, output_gpx_path, total_distance, area, retry_count, area_ratio):
        """创建GPX文件并生成对应的txt信息文件"""
        gpx_trajectory = [(arcpy.Point(*self.transformer.transform(point.X, point.Y)), time, elevation) for point, time, elevation in points_with_time]
        self._create_gpx_file(gpx_trajectory, output_gpx_path, total_distance, area)
        
        # 创建对应的txt文件
        txt_path = output_gpx_path.replace('.gpx', '.txt')
        self._create_txt_info(points_with_time, txt_path, total_distance, area, retry_count, area_ratio)

    def _create_txt_info(self, points_with_time, output_txt_path, total_distance, area, retry_count, area_ratio):
        """创建包含航迹关键信息的txt文件"""
        start_point, start_time, start_elevation = points_with_time[0]
        end_point, end_time, end_elevation = points_with_time[-1]
        
        # 转换起点和终点坐标为经纬度
        start_lon, start_lat = self.transformer.transform(start_point.X, start_point.Y)
        end_lon, end_lat = self.transformer.transform(end_point.X, end_point.Y)
        
        elevations = [elevation for _, _, elevation in points_with_time]
        min_elevation = min(elevations)
        max_elevation = max(elevations)
        
        # 提取gpx文件名作为航迹名称
        trajectory_name = os.path.basename(output_txt_path).replace('.txt', '')
        
        with open(output_txt_path, 'w') as f:
            f.write(f"name={trajectory_name}\n")
            f.write(f"start_x={start_point.X}\n")
            f.write(f"start_y={start_point.Y}\n")
            f.write(f"start_lon={start_lon}\n")
            f.write(f"start_lat={start_lat}\n")
            f.write(f"end_x={end_point.X}\n")
            f.write(f"end_y={end_point.Y}\n")
            f.write(f"end_lon={end_lon}\n")
            f.write(f"end_lat={end_lat}\n")
            f.write(f"min_elevation={min_elevation}\n")
            f.write(f"max_elevation={max_elevation}\n")
            f.write(f"start_time={start_time.strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
            f.write(f"end_time={end_time.strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
            f.write(f"total_distance={total_distance}\n")
            f.write(f"area={area}\n")
            f.write(f"area_ratio={area_ratio:.4f}\n")  # 添加面积精度，保留4位小数
            f.write(f"retry_count={retry_count}\n")  # 添加重试次数

    @staticmethod
    def _create_gpx_file(trajectory, output_gpx_path, total_distance, area):
        """为单个轨迹创建GPX文件。"""
        gpx = ET.Element("gpx", version="1.1", creator="ArcGIS Trajectory Simulator")
        # 元数据，用于GIS Office显示
        metadata = ET.SubElement(gpx, "metadata")
        name = ET.SubElement(metadata, "name")
        name.text = "Simulated Trajectory"
        
        trk = ET.SubElement(gpx, "trk")
        trk_name = ET.SubElement(trk, "name")
        trk_name.text = "Simulated Track"
        
        trkseg = ET.SubElement(trk, "trkseg")
        
        for point, time, elevation in trajectory:
            trkpt = ET.SubElement(trkseg, "trkpt", lat=str(point.Y), lon=str(point.X))
            ele = ET.SubElement(trkpt, "ele")
            ele.text = str(elevation)
            time_elem = ET.SubElement(trkpt, "time")
            time_elem.text = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        extensions = ET.SubElement(trk, "extensions")
        starttime = ET.SubElement(extensions, "starttime")
        starttime.text = trajectory[0][1].strftime("%Y-%m-%dT%H:%M:%SZ")
        endtime = ET.SubElement(extensions, "endtime")
        endtime.text = trajectory[-1][1].strftime("%Y-%m-%dT%H:%M:%SZ")
        length = ET.SubElement(extensions, "length")
        length.text = str(total_distance)
        area_elem = ET.SubElement(extensions, "area")
        area_elem.text = str(area)

        tree = ET.ElementTree(gpx)
        tree.write(output_gpx_path, encoding="utf-8", xml_declaration=True)

# 使用示例
if __name__ == "__main__":
    config_path = r"path\to\config.json"
    input_features = r"path\to\input\features"
    output_folder = r"path\to\output\folder"
    
    # 创建自定义的高程提供者（如果需要）
    # custom_elevation_provider = YourCustomElevationProvider()
    
    # 使用默认高程提供者
    simulator = TrajectorySimulator(config_path)
    
    # 或使用自定义高程提供者
    # simulator = TrajectorySimulator(config_path, elevation_provider=custom_elevation_provider)
    
    index_dict = {}
    def naming_callback(row):
        key = f"{row[1]}_{row[2]}"
        if key not in index_dict:
            index_dict[key] = 0
        index = index_dict[key]
        index_dict[key] += 1
        return f"{key}_{index}"
    
    callback_fields = ['林场', '林班']
    
    simulator.simulate_trajectories(input_features, output_folder, 
                                    person_num_field='PERSON_NUM',
                                    start_time_field='START_TIME',
                                    callback=naming_callback, 
                                    callback_fields=callback_fields)