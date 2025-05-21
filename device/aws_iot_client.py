#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AWS IoT Core接続クライアントモジュール
"""

import json
import time
import logging
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from AWSIoTPythonSDK.exception.AWSIoTExceptions import connectTimeoutException


class AWSIoTClient:
    """
    AWS IoT Coreとの接続を管理するクラス
    """

    def __init__(self, config):
        """
        コンストラクタ
        
        Args:
            config (dict): 設定情報
        """
        self.aws_config = config["aws_iot"]
        self.log_config = config["logging"]
        
        # ロガーの設定
        self._setup_logging()
        
        # MQTTクライアントの初期化
        self.client_id = self.aws_config["client_id"]
        self.endpoint = self.aws_config["endpoint"]
        self.port = self.aws_config["port"]
        self.topic = self.aws_config["topic"]
        self.shadow_topic = self.aws_config["shadow_topic"]
        self.thing_name = self.aws_config["thing_name"]
        
        self.mqtt_client = self._setup_mqtt_client()
        self.connected = False
        
        self.logger.info(f"AWS IoTクライアントを初期化しました。エンドポイント: {self.endpoint}")

    def _setup_logging(self):
        """
        ロギングの設定
        """
        self.logger = logging.getLogger("AWSIoTClient")
        level = getattr(logging, self.log_config["level"])
        self.logger.setLevel(level)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(self.log_config["format"])
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)

    def _setup_mqtt_client(self):
        """
        MQTTクライアントの設定
        
        Returns:
            AWSIoTMQTTClient: 設定済みのMQTTクライアント
        """
        mqtt_client = AWSIoTMQTTClient(self.client_id)
        mqtt_client.configureEndpoint(self.endpoint, self.port)
        
        # 証明書の設定
        mqtt_client.configureCredentials(
            self.aws_config["ca_path"],
            self.aws_config["private_key_path"],
            self.aws_config["cert_path"]
        )
        
        # MQTT接続パラメータの設定
        mqtt_client.configureAutoReconnectBackoffTime(1, 32, 20)
        mqtt_client.configureOfflinePublishQueueing(-1)  # 無制限のキューイング
        mqtt_client.configureDrainingFrequency(2)  # 2Hzでのドレイニング
        mqtt_client.configureConnectDisconnectTimeout(10)  # 10秒のタイムアウト
        mqtt_client.configureMQTTOperationTimeout(20)  # 20秒のタイムアウト（5秒から増加）
        
        return mqtt_client

    def connect(self, max_retries=5):
        """
        AWS IoT Coreに接続する
        
        Args:
            max_retries (int): 最大再試行回数
            
        Returns:
            bool: 接続成功の場合True、失敗の場合False
        """
        if self.connected:
            self.logger.info("すでに接続されています")
            return True
            
        retry_count = 0
        while retry_count < max_retries:
            try:
                self.logger.info(f"AWS IoT Coreに接続しています... (試行 {retry_count + 1}/{max_retries})")
                self.mqtt_client.connect()
                self.connected = True
                self.logger.info("AWS IoT Coreに接続しました")
                return True
            except connectTimeoutException:
                retry_count += 1
                self.logger.warning(f"接続タイムアウト。再試行中... ({retry_count}/{max_retries})")
                time.sleep(2)  # 再試行前に少し待機
            except Exception as e:
                self.logger.error(f"接続エラー: {str(e)}")
                return False
                
        self.logger.error(f"最大再試行回数 ({max_retries}) に達しました。接続に失敗しました。")
        return False

    def disconnect(self):
        """
        AWS IoT Coreから切断する
        """
        if self.connected:
            self.mqtt_client.disconnect()
            self.connected = False
            self.logger.info("AWS IoT Coreから切断しました")

    def publish_data(self, data):
        """
        データをAWS IoT Coreに送信する
        
        Args:
            data (dict): 送信するデータ
            
        Returns:
            bool: 送信成功の場合True、失敗の場合False
        """
        if not self.connected:
            self.logger.warning("接続されていません。送信をスキップします。")
            return False
            
        try:
            payload = json.dumps(data)
            self.mqtt_client.publish(self.topic, payload, 1)
            self.logger.debug(f"データを送信しました: {payload[:100]}...")
            return True
        except Exception as e:
            self.logger.error(f"送信エラー: {str(e)}")
            return False

    def update_shadow(self, state):
        """
        デバイスシャドウを更新する
        
        Args:
            state (dict): 更新する状態
            
        Returns:
            bool: 更新成功の場合True、失敗の場合False
        """
        if not self.connected:
            self.logger.warning("接続されていません。シャドウ更新をスキップします。")
            return False
            
        try:
            shadow_payload = {
                "state": {
                    "reported": state
                }
            }
            payload = json.dumps(shadow_payload)
            self.mqtt_client.publish(self.shadow_topic, payload, 1)
            self.logger.debug("デバイスシャドウを更新しました")
            return True
        except Exception as e:
            self.logger.error(f"シャドウ更新エラー: {str(e)}")
            return False

    def subscribe_to_shadow_delta(self, callback, max_retries=3):
        """
        シャドウのデルタ更新を購読する
        
        Args:
            callback (function): コールバック関数
            max_retries (int): 最大再試行回数
            
        Returns:
            bool: 購読成功の場合True、失敗の場合False
        """
        if not self.connected:
            self.logger.warning("接続されていません。購読をスキップします。")
            return False
            
        delta_topic = f"$aws/things/{self.thing_name}/shadow/update/delta"
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                self.logger.info(f"トピック {delta_topic} を購読しています... (試行 {retry_count + 1}/{max_retries})")
                self.mqtt_client.subscribe(delta_topic, 1, callback)
                self.logger.info(f"トピック {delta_topic} を購読しました")
                return True
            except Exception as e:
                retry_count += 1
                self.logger.warning(f"購読エラー: {str(e)}。再試行中... ({retry_count}/{max_retries})")
                time.sleep(2)  # 再試行前に少し待機
        
        self.logger.error(f"最大再試行回数 ({max_retries}) に達しました。購読に失敗しました。")
        return False


# テスト用コード
if __name__ == "__main__":
    import os
    
    # 現在のディレクトリを取得
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # テスト用の設定
    test_config = {
        "aws_iot": {
            "endpoint": "test-endpoint.iot.ap-northeast-1.amazonaws.com",
            "port": 8883,
            "client_id": "test_device",
            "thing_name": "test_device",
            "topic": "device/test",
            "shadow_topic": "$aws/things/test_device/shadow/update",
            "cert_path": os.path.join(current_dir, "certs/certificate.pem.crt"),
            "private_key_path": os.path.join(current_dir, "certs/private.pem.key"),
            "ca_path": os.path.join(current_dir, "certs/AmazonRootCA1.pem")
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }
    
    # 注意: このテストは実際の証明書がないと失敗します
    print("注意: このテストは実際の証明書がないと失敗します")
    print("テスト目的のみで、実際の接続は行いません")
