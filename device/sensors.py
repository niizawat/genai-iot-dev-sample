#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
センサーデータシミュレーションモジュールおよび実際のセンサー読み取りモジュール
"""

import random
import time
import json
import board
import busio
from datetime import datetime
import adafruit_tcs34725


class TCS34725ColorSensor:
    """
    TCS34725カラーセンサーからデータを読み取るクラス
    """

    def __init__(self):
        """
        コンストラクタ
        """
        # I2Cバスの初期化
        self.i2c = busio.I2C(board.SCL, board.SDA)
        # TCS34725センサーの初期化
        try:
            self.sensor = adafruit_tcs34725.TCS34725(self.i2c)
            # センサーの設定
            self.sensor.integration_time = 50  # ミリ秒
            self.sensor.gain = 4  # ゲイン設定 (1, 4, 16, 60)
            print("TCS34725カラーセンサーを初期化しました")
            self.initialized = True
        except Exception as e:
            print(f"TCS34725センサーの初期化に失敗しました: {str(e)}")
            self.initialized = False

    def read_color(self):
        """
        カラーセンサーから色データを読み取る
        
        Returns:
            dict: 色データ (RGB値、色温度、明るさ)
        """
        if not self.initialized:
            return {
                "r": 0, "g": 0, "b": 0,
                "color_temp": 0,
                "lux": 0
            }
            
        try:
            # RGB値の取得
            r, g, b, c = self.sensor.color_raw
            # 色温度の取得
            color_temp = self.sensor.color_temperature
            # 明るさの取得
            lux = self.sensor.lux
            
            return {
                "r": r, "g": g, "b": b,
                "color_temp": color_temp,
                "lux": lux
            }
        except Exception as e:
            print(f"カラーセンサーの読み取りに失敗しました: {str(e)}")
            return {
                "r": 0, "g": 0, "b": 0,
                "color_temp": 0,
                "lux": 0
            }


class SensorSimulator:
    """
    各種センサーデータをシミュレートするクラス
    """

    def __init__(self, config):
        """
        コンストラクタ
        
        Args:
            config (dict): 設定情報
        """
        self.device_config = config["device"]
        self.device_type = self.device_config["type"]
        self.location = self.device_config["location"]
        self.available_sensors = self.device_config["sensors"]
        
        # 各センサーの初期値と変動範囲
        self.sensor_ranges = {
            "temperature": {"min": 15.0, "max": 30.0, "current": 22.0, "unit": "°C"},
            "humidity": {"min": 30.0, "max": 80.0, "current": 50.0, "unit": "%"},
            "pressure": {"min": 990.0, "max": 1020.0, "current": 1013.0, "unit": "hPa"},
            "light": {"min": 0.0, "max": 1000.0, "current": 500.0, "unit": "lux"},
            "co2": {"min": 400.0, "max": 1500.0, "current": 600.0, "unit": "ppm"},
            "motion": {"min": 0, "max": 1, "current": 0, "unit": "boolean"}
        }
        
        # 利用可能なセンサーのみを保持
        self.sensors = {k: v for k, v in self.sensor_ranges.items() if k in self.available_sensors}
        
        print(f"センサーシミュレータを初期化しました。利用可能なセンサー: {', '.join(self.sensors.keys())}")

    def _update_sensor_value(self, sensor_name):
        """
        センサー値を自然に変動させる
        
        Args:
            sensor_name (str): センサー名
            
        Returns:
            float: 更新されたセンサー値
        """
        sensor = self.sensors[sensor_name]
        min_val = sensor["min"]
        max_val = sensor["max"]
        current = sensor["current"]
        
        # 特別な処理（モーションセンサーなど）
        if sensor_name == "motion":
            # 10%の確率で動きを検出
            new_value = 1 if random.random() < 0.1 else 0
        else:
            # 現在値から少しだけランダムに変動させる（-1.0〜+1.0の範囲）
            change = (random.random() * 2 - 1.0) * (max_val - min_val) * 0.02
            new_value = current + change
            
            # 最小値・最大値の範囲内に収める
            new_value = max(min_val, min(max_val, new_value))
            
            # 小数点以下2桁に丸める
            new_value = round(new_value, 2)
        
        # 現在値を更新
        self.sensors[sensor_name]["current"] = new_value
        
        return new_value

    def read_sensors(self):
        """
        全センサーの値を読み取る
        
        Returns:
            dict: センサー値のディクショナリ
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        readings = {
            "device_id": f"{self.device_type}_{self.location}",
            "timestamp": timestamp,
            "location": self.location,
            "readings": {}
        }
        
        # 各センサーの値を更新して取得
        for sensor_name in self.sensors:
            value = self._update_sensor_value(sensor_name)
            unit = self.sensors[sensor_name]["unit"]
            readings["readings"][sensor_name] = {
                "value": value,
                "unit": unit
            }
        
        return readings


class RealSensor:
    """
    実際のセンサーからデータを読み取るクラス
    """

    def __init__(self, config):
        """
        コンストラクタ
        
        Args:
            config (dict): 設定情報
        """
        self.device_config = config["device"]
        self.device_type = self.device_config["type"]
        self.location = self.device_config["location"]
        self.available_sensors = self.device_config["sensors"]
        
        # カラーセンサーの初期化
        self.color_sensor = None
        if "color" in self.available_sensors:
            self.color_sensor = TCS34725ColorSensor()
        
        print(f"実際のセンサーを初期化しました。利用可能なセンサー: "
              f"{', '.join(self.available_sensors)}")

    def read_sensors(self):
        """
        全センサーの値を読み取る
        
        Returns:
            dict: センサー値のディクショナリ
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        readings = {
            "device_id": f"{self.device_type}_{self.location}",
            "timestamp": timestamp,
            "location": self.location,
            "readings": {}
        }
        
        # カラーセンサーの値を読み取る
        if self.color_sensor and "color" in self.available_sensors:
            color_data = self.color_sensor.read_color()
            readings["readings"]["color"] = {
                "r": color_data["r"],
                "g": color_data["g"],
                "b": color_data["b"],
                "color_temp": color_data["color_temp"],
                "lux": color_data["lux"],
                "unit": "RGB"
            }
        
        return readings


# テスト用コード
if __name__ == "__main__":
    # テスト用の設定
    test_config = {
        "device": {
            "type": "raspberry_pi",
            "location": "test_room",
            "sampling_interval": 2,
            "sensors": ["color"]
        }
    }
    
    # 実際のセンサーを使用する場合
    try:
        sensor = RealSensor(test_config)
        # 5回センサー値を読み取ってみる
        for i in range(5):
            data = sensor.read_sensors()
            print(f"読み取り {i+1}:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            time.sleep(1)
    except Exception as e:
        print(f"実際のセンサーの使用中にエラーが発生しました: {str(e)}")
        
        # エラーが発生した場合はシミュレータを使用
        print("シミュレータに切り替えます...")
        sim_config = {
            "device": {
                "type": "dummy",
                "location": "test_room",
                "sampling_interval": 2,
                "sensors": ["temperature", "humidity", "pressure", "light", "motion"]
            }
        }
        simulator = SensorSimulator(sim_config)
        for i in range(5):
            data = simulator.read_sensors()
            print(f"シミュレータ読み取り {i+1}:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            time.sleep(1)
