#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
IoTデバイスメインスクリプト
"""

import os
import sys
import json
import time
import signal
import logging
import argparse
from datetime import datetime

# 自作モジュールのインポート
from sensors import SensorSimulator, RealSensor
from aws_iot_client import AWSIoTClient


class IoTDevice:
    """
    IoTデバイスのメインクラス
    """

    def __init__(self, config_path, config=None):
        """
        コンストラクタ
        
        Args:
            config_path (str): 設定ファイルのパス
            config (dict, optional): 設定情報。指定しない場合はファイルから読み込む
        """
        # 設定の読み込み
        self.config = config if config is not None else self._load_config(config_path)
        
        # ロギングの設定
        self._setup_logging()
        
        # 終了フラグ
        self.running = False
        
        # センサーの初期化
        # デバイスタイプに基づいて実際のセンサーかシミュレータを選択
        if self.config["device"]["type"] == "raspberry_pi":
            try:
                self.logger.info("実際のセンサーを使用します")
                self.sensor = RealSensor(self.config)
            except Exception as e:
                self.logger.warning(f"実際のセンサーの初期化に失敗しました: {str(e)}")
                self.logger.info("シミュレータに切り替えます")
                self.sensor = SensorSimulator(self.config)
        else:
            self.logger.info("シミュレータを使用します")
            self.sensor = SensorSimulator(self.config)
        
        # AWS IoTクライアントの初期化
        self.aws_iot_client = AWSIoTClient(self.config)
        
        # サンプリング間隔（秒）
        self.sampling_interval = self.config["device"]["sampling_interval"]
        
        # デバイス情報
        self.device_type = self.config["device"]["type"]
        self.location = self.config["device"]["location"]
        self.device_id = f"{self.device_type}_{self.location}"
        
        self.logger.info(f"IoTデバイスを初期化しました。デバイスID: {self.device_id}")

    def _load_config(self, config_path):
        """
        設定ファイルを読み込む
        
        Args:
            config_path (str): 設定ファイルのパス
            
        Returns:
            dict: 設定情報
        """
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"設定ファイルの読み込みに失敗しました: {str(e)}")
            sys.exit(1)

    def _setup_logging(self):
        """
        ロギングの設定
        """
        self.logger = logging.getLogger("IoTDevice")
        level = getattr(logging, self.config["logging"]["level"])
        self.logger.setLevel(level)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(self.config["logging"]["format"])
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)

    def _shadow_delta_callback(self, client, userdata, message):
        """
        シャドウデルタ更新のコールバック
        
        Args:
            client: MQTTクライアント
            userdata: ユーザーデータ
            message: 受信メッセージ
        """
        try:
            payload = json.loads(message.payload.decode('utf-8'))
            delta = payload.get('state', {})
            self.logger.info(f"シャドウデルタを受信しました: {delta}")
            
            # ここでデルタに基づいてデバイスの状態を更新する処理を実装
            # 例: 設定の更新など
            
        except Exception as e:
            self.logger.error(f"シャドウデルタの処理中にエラーが発生しました: {str(e)}")

    def start(self):
        """
        デバイスの動作を開始する
        """
        # シグナルハンドラの設定
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # AWS IoT Coreに接続
        if not self.aws_iot_client.connect():
            self.logger.error("AWS IoT Coreへの接続に失敗しました。終了します。")
            return
            
        # シャドウデルタの購読
        if not self.aws_iot_client.subscribe_to_shadow_delta(self._shadow_delta_callback):
            self.logger.warning("シャドウデルタの購読に失敗しましたが、処理を続行します。")
        
        # デバイス情報をシャドウに報告
        device_info = {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "location": self.location,
            "firmware_version": "1.0.0",
            "available_sensors": self.config["device"]["sensors"],
            "sampling_interval": self.sampling_interval,
            "last_boot": datetime.utcnow().isoformat() + "Z"
        }
        self.aws_iot_client.update_shadow(device_info)
        
        # メインループ
        self.running = True
        self.logger.info("データ送信を開始します...")
        
        try:
            while self.running:
                # センサーデータの読み取り
                sensor_data = self.sensor.read_sensors()
                
                # データの送信
                if self.aws_iot_client.publish_data(sensor_data):
                    self.logger.info(f"データを送信しました: {sensor_data['timestamp']}")
                
                # シャドウの更新（最新のセンサー値）
                shadow_state = {
                    "last_update": sensor_data["timestamp"],
                    "readings": sensor_data["readings"]
                }
                self.aws_iot_client.update_shadow(shadow_state)
                
                # 次のサンプリングまで待機
                time.sleep(self.sampling_interval)
                
        except Exception as e:
            self.logger.error(f"実行中にエラーが発生しました: {str(e)}")
        finally:
            self.stop()

    def stop(self):
        """
        デバイスの動作を停止する
        """
        self.running = False
        self.logger.info("デバイスを停止しています...")
        
        # AWS IoT Coreから切断
        self.aws_iot_client.disconnect()
        
        self.logger.info("デバイスを停止しました")

    def _signal_handler(self, sig, frame):
        """
        シグナルハンドラ
        
        Args:
            sig: シグナル番号
            frame: フレーム
        """
        self.logger.info(f"シグナル {sig} を受信しました。停止します...")
        self.stop()


def main():
    """
    メイン関数
    """
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='IoTデバイスシミュレータ')
    parser.add_argument('-c', '--config', default='config.json',
                        help='設定ファイルのパス (デフォルト: config.json)')
    parser.add_argument('-t', '--thing-name',
                        help='AWS IoT Thing名 (指定しない場合は設定ファイルの値を使用)')
    args = parser.parse_args()
    
    # 設定ファイルのパスを解決
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, args.config)
    
    # 設定ファイルを読み込む
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Thing名が指定された場合は設定を更新
    if args.thing_name:
        print(f"Thing名を '{args.thing_name}' に設定します")
        config['aws_iot']['client_id'] = args.thing_name
        config['aws_iot']['thing_name'] = args.thing_name
        config['aws_iot']['topic'] = f"device/{args.thing_name}/data"
        config['aws_iot']['shadow_topic'] = f"$aws/things/{args.thing_name}/shadow/update"
    
    # デバイスの初期化と開始
    device = IoTDevice(config_path, config)
    device.start()


if __name__ == "__main__":
    main()
