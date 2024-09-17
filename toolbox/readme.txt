配置文件参考 cofig.json:
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