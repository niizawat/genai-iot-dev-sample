#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AWS IoT Core Thing作成スクリプト
"""

import os
import json
import boto3
import argparse
import requests
from botocore.exceptions import ClientError


class AWSIoTSetup:
    """
    AWS IoT Core Thing作成と証明書のダウンロードを行うクラス
    """

    def __init__(self, thing_name, region, policy_name=None):
        """
        コンストラクタ
        
        Args:
            thing_name (str): 作成するThingの名前
            region (str): AWSリージョン
            policy_name (str, optional): ポリシー名（指定しない場合はThing名 + _policyが使用される）
        """
        self.thing_name = thing_name
        self.region = region
        self.policy_name = policy_name or f"{thing_name}_policy"
        
        # AWS IoTクライアントの初期化
        self.iot_client = boto3.client('iot', region_name=region)
        
        # 証明書保存先ディレクトリ
        self.cert_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certs')
        
        # ディレクトリが存在しない場合は作成
        if not os.path.exists(self.cert_dir):
            os.makedirs(self.cert_dir)
            
        print(f"AWS IoT Setup: リージョン {region} で Thing '{thing_name}' を作成します")

    def create_thing(self):
        """
        AWS IoT Core上にThingを作成する
        
        Returns:
            dict: 作成されたThingの情報
        """
        try:
            # Thingが既に存在するか確認
            try:
                self.iot_client.describe_thing(thingName=self.thing_name)
                print(f"Thing '{self.thing_name}' は既に存在します")
                return {"thingName": self.thing_name}
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
            
            # Thingを作成
            response = self.iot_client.create_thing(thingName=self.thing_name)
            print(f"Thing '{self.thing_name}' を作成しました")
            return response
            
        except Exception as e:
            print(f"Thingの作成中にエラーが発生しました: {str(e)}")
            raise

    def create_keys_and_certificate(self):
        """
        証明書と鍵を作成する
        
        Returns:
            dict: 証明書と鍵の情報
        """
        try:
            # 証明書と鍵を作成
            response = self.iot_client.create_keys_and_certificate(setAsActive=True)
            
            cert_id = response['certificateId']
            cert_arn = response['certificateArn']
            cert_pem = response['certificatePem']
            private_key = response['keyPair']['PrivateKey']
            
            # 証明書と鍵をファイルに保存
            cert_path = os.path.join(self.cert_dir, 'certificate.pem.crt')
            key_path = os.path.join(self.cert_dir, 'private.pem.key')
            
            with open(cert_path, 'w') as f:
                f.write(cert_pem)
                
            with open(key_path, 'w') as f:
                f.write(private_key)
                
            print(f"証明書と鍵を作成し、{self.cert_dir}に保存しました")
            print(f"証明書ID: {cert_id}")
            
            return {
                'certificateId': cert_id,
                'certificateArn': cert_arn,
                'certificatePath': cert_path,
                'privateKeyPath': key_path
            }
            
        except Exception as e:
            print(f"証明書と鍵の作成中にエラーが発生しました: {str(e)}")
            raise

    def create_policy(self):
        """
        IoTポリシーを作成する
        
        Returns:
            dict: 作成されたポリシーの情報
        """
        try:
            # ポリシーが既に存在するか確認
            try:
                self.iot_client.get_policy(policyName=self.policy_name)
                print(f"ポリシー '{self.policy_name}' は既に存在します")
                return {"policyName": self.policy_name}
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
            
            # ポリシードキュメントの作成
            policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "iot:Connect",
                        "Resource": f"arn:aws:iot:{self.region}:*:client/{self.thing_name}"
                    },
                    {
                        "Effect": "Allow",
                        "Action": "iot:Subscribe",
                        "Resource": [
                            f"arn:aws:iot:{self.region}:*:topicfilter/device/*",
                            f"arn:aws:iot:{self.region}:*:topicfilter/$aws/things/{self.thing_name}/shadow/update/delta",
                            f"arn:aws:iot:{self.region}:*:topicfilter/$aws/things/{self.thing_name}/shadow/get/accepted",
                            f"arn:aws:iot:{self.region}:*:topicfilter/$aws/things/{self.thing_name}/shadow/update/accepted"
                        ]
                    },
                    {
                        "Effect": "Allow",
                        "Action": "iot:Receive",
                        "Resource": [
                            f"arn:aws:iot:{self.region}:*:topic/device/*",
                            f"arn:aws:iot:{self.region}:*:topic/$aws/things/{self.thing_name}/shadow/update/delta",
                            f"arn:aws:iot:{self.region}:*:topic/$aws/things/{self.thing_name}/shadow/get/accepted",
                            f"arn:aws:iot:{self.region}:*:topic/$aws/things/{self.thing_name}/shadow/update/accepted"
                        ]
                    },
                    {
                        "Effect": "Allow",
                        "Action": "iot:Publish",
                        "Resource": [
                            f"arn:aws:iot:{self.region}:*:topic/device/*",
                            f"arn:aws:iot:{self.region}:*:topic/$aws/things/{self.thing_name}/shadow/update",
                            f"arn:aws:iot:{self.region}:*:topic/$aws/things/{self.thing_name}/shadow/get"
                        ]
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "iot:GetThingShadow",
                            "iot:UpdateThingShadow",
                            "iot:DeleteThingShadow"
                        ],
                        "Resource": f"arn:aws:iot:{self.region}:*:thing/{self.thing_name}"
                    }
                ]
            }
            
            # ポリシーを作成
            response = self.iot_client.create_policy(
                policyName=self.policy_name,
                policyDocument=json.dumps(policy_document)
            )
            
            print(f"ポリシー '{self.policy_name}' を作成しました")
            return response
            
        except Exception as e:
            print(f"ポリシーの作成中にエラーが発生しました: {str(e)}")
            raise

    def attach_policy_to_certificate(self, certificate_arn):
        """
        ポリシーを証明書にアタッチする
        
        Args:
            certificate_arn (str): 証明書のARN
        """
        try:
            self.iot_client.attach_policy(
                policyName=self.policy_name,
                target=certificate_arn
            )
            print(f"ポリシー '{self.policy_name}' を証明書にアタッチしました")
            
        except Exception as e:
            print(f"ポリシーのアタッチ中にエラーが発生しました: {str(e)}")
            raise

    def attach_certificate_to_thing(self, certificate_arn):
        """
        証明書をThingにアタッチする
        
        Args:
            certificate_arn (str): 証明書のARN
        """
        try:
            self.iot_client.attach_thing_principal(
                thingName=self.thing_name,
                principal=certificate_arn
            )
            print(f"証明書を Thing '{self.thing_name}' にアタッチしました")
            
        except Exception as e:
            print(f"証明書のアタッチ中にエラーが発生しました: {str(e)}")
            raise

    def download_root_ca(self):
        """
        Amazon Root CA証明書をダウンロードする
        
        Returns:
            str: 保存したファイルのパス
        """
        try:
            # Amazon Root CA 1をダウンロード
            url = "https://www.amazontrust.com/repository/AmazonRootCA1.pem"
            response = requests.get(url)
            
            if response.status_code == 200:
                ca_path = os.path.join(self.cert_dir, 'AmazonRootCA1.pem')
                
                with open(ca_path, 'w') as f:
                    f.write(response.text)
                    
                print(f"Amazon Root CA証明書をダウンロードし、{ca_path}に保存しました")
                return ca_path
            else:
                raise Exception(f"ダウンロード失敗: ステータスコード {response.status_code}")
                
        except Exception as e:
            print(f"Root CA証明書のダウンロード中にエラーが発生しました: {str(e)}")
            raise

    def get_endpoint(self):
        """
        AWS IoTのエンドポイントを取得する
        
        Returns:
            str: エンドポイントのアドレス
        """
        try:
            response = self.iot_client.describe_endpoint(endpointType='iot:Data-ATS')
            endpoint = response['endpointAddress']
            print(f"AWS IoTエンドポイント: {endpoint}")
            return endpoint
            
        except Exception as e:
            print(f"エンドポイントの取得中にエラーが発生しました: {str(e)}")
            raise

    def update_config_file(self, endpoint):
        """
        設定ファイルを更新する
        
        Args:
            endpoint (str): AWS IoTエンドポイント
        """
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
            
            # 設定ファイルを読み込む
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # AWS IoT設定を更新
            config['aws_iot']['endpoint'] = endpoint
            config['aws_iot']['client_id'] = self.thing_name
            config['aws_iot']['thing_name'] = self.thing_name
            config['aws_iot']['topic'] = f"device/{self.thing_name}/data"
            config['aws_iot']['shadow_topic'] = f"$aws/things/{self.thing_name}/shadow/update"
            
            # 更新した設定を保存
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
                
            print(f"設定ファイル {config_path} を更新しました")
            
        except Exception as e:
            print(f"設定ファイルの更新中にエラーが発生しました: {str(e)}")
            raise

    def setup(self):
        """
        セットアップ処理を実行する
        """
        try:
            # Thingを作成
            thing = self.create_thing()
            
            # 証明書と鍵を作成
            cert = self.create_keys_and_certificate()
            
            # ポリシーを作成
            policy = self.create_policy()
            
            # ポリシーを証明書にアタッチ
            self.attach_policy_to_certificate(cert['certificateArn'])
            
            # 証明書をThingにアタッチ
            self.attach_certificate_to_thing(cert['certificateArn'])
            
            # Root CA証明書をダウンロード
            self.download_root_ca()
            
            # エンドポイントを取得
            endpoint = self.get_endpoint()
            
            # 設定ファイルを更新
            self.update_config_file(endpoint)
            
            print("\nセットアップが完了しました！")
            print(f"Thing名: {self.thing_name}")
            print(f"証明書と鍵は {self.cert_dir} に保存されています")
            print(f"設定ファイルは自動的に更新されました")
            print("\n以下のコマンドでIoTデバイスを起動できます:")
            print(f"python device.py")
            
        except Exception as e:
            print(f"セットアップ中にエラーが発生しました: {str(e)}")
            raise


def main():
    """
    メイン関数
    """
    parser = argparse.ArgumentParser(description='AWS IoT Core Thing作成スクリプト')
    parser.add_argument('--thing-name', default='iot_device_sample',
                        help='作成するThingの名前 (デフォルト: iot_device_sample)')
    parser.add_argument('--region', default='ap-northeast-1',
                        help='AWSリージョン (デフォルト: ap-northeast-1)')
    parser.add_argument('--policy-name',
                        help='ポリシー名 (指定しない場合はThing名 + _policyが使用される)')
    
    args = parser.parse_args()
    
    # セットアップの実行
    setup = AWSIoTSetup(args.thing_name, args.region, args.policy_name)
    setup.setup()


if __name__ == "__main__":
    main()
