# IoTデバイスサンプル実装

このディレクトリには、アーキテクチャ図に基づいたIoTデバイス側の実装サンプルが含まれています。

## 概要

このサンプルコードは、以下の機能を実装しています：

1. ダミーセンサーデータの生成（温度、湿度、気圧など）
2. AWS IoT Core へのMQTT接続
3. 定期的なデータ送信
4. デバイスシャドウの更新と同期

## ファイル構成

- `device.py`: メインスクリプト
- `sensors.py`: ダミーセンサーデータ生成モジュール
- `aws_iot_client.py`: AWS IoT接続モジュール
- `config.json`: デバイス設定ファイル
- `setup_aws_iot.py`: AWS IoT Core Thing作成スクリプト

## 前提条件

- Python 3.7以上
- AWS CLIがインストールされ、適切に設定されていること
- AWS IoT Coreへのアクセス権限を持つIAMユーザー

## インストール方法

必要なパッケージをインストールします：

```bash
# 依存パッケージを一括インストール
pip install -r requirements.txt

# または個別にインストール
pip install AWSIoTPythonSDK boto3 python-dotenv requests
```

## AWS IoT Coreのセットアップ

### 自動セットアップ（推奨）

以下のコマンドを実行して、AWS IoT CoreにThingを作成し、必要な証明書を取得します：

```bash
# デフォルト設定でセットアップ
python setup_aws_iot.py

# Thing名を指定してセットアップ
python setup_aws_iot.py --thing-name my_iot_device

# リージョンを指定してセットアップ
python setup_aws_iot.py --region us-east-1
```

このスクリプトは以下の処理を行います：

1. AWS IoT CoreにThingを作成
2. 証明書と鍵を生成
3. ポリシーを作成し、証明書にアタッチ
4. 証明書をThingにアタッチ
5. Amazon Root CA証明書をダウンロード
6. **AWS IoTエンドポイントを取得して設定ファイルに反映**
7. 設定ファイル（config.json）を自動的に更新

すべての証明書と鍵は `certs` ディレクトリに保存されます。

### 手動セットアップ

自動セットアップができない場合や、既存のThingを使用する場合は、以下の手順で設定します。

#### AWS IoTエンドポイントの取得

AWS IoTエンドポイントは、以下のいずれかの方法で取得できます：

**AWS CLIを使用する方法：**

```bash
# ATS エンドポイントを取得（推奨）
aws iot describe-endpoint --endpoint-type iot:Data-ATS

# レガシーエンドポイントを取得
aws iot describe-endpoint --endpoint-type iot:Data
```

**AWS Management Consoleを使用する方法：**

1. AWS Management Consoleにログイン
2. AWS IoT Coreのサービスページに移動
3. 左側のメニューから「設定」を選択
4. 「デバイスデータエンドポイント」セクションに表示されているエンドポイントをコピー

#### 設定ファイルの更新

取得したエンドポイントを `config.json` ファイルの `aws_iot.endpoint` に設定します：

```json
{
    "aws_iot": {
        "endpoint": "YOUR_ENDPOINT_HERE.iot.YOUR_REGION.amazonaws.com",
        ...
    },
    ...
}
```

#### 証明書の取得

AWS IoT Coreで証明書を作成し、以下のファイルをダウンロードして `certs` ディレクトリに配置します：

1. デバイス証明書 → `certs/certificate.pem.crt`
2. 秘密鍵 → `certs/private.pem.key`
3. Amazon Root CA → `certs/AmazonRootCA1.pem`（[ダウンロードリンク](https://www.amazontrust.com/repository/AmazonRootCA1.pem)）

## 実行方法

セットアップが完了したら、以下のコマンドでデバイスを起動します：

```bash
# デフォルト設定で実行
python device.py

# Thing名を指定して実行
python device.py --thing-name my_iot_device

# 設定ファイルとThing名を指定して実行
python device.py --config my_config.json --thing-name my_iot_device
```

Thing名をコマンドライン引数で指定すると、設定ファイルの値を上書きして使用します。これにより、同じ設定ファイルを使用して異なるThingとして動作させることができます。

## Raspberry Piでの実行

Raspberry Piで実行する場合は、以下の手順でセットアップします：

```bash
# 必要なパッケージをインストール
sudo apt-get update
sudo apt-get install python3-pip

# 依存パッケージをインストール
sudo pip3 install -r requirements.txt

# または個別にインストール
sudo pip3 install AWSIoTPythonSDK boto3 python-dotenv requests
```

## ハードウェア接続

### TCS34725カラーセンサーの接続

TCS34725カラーセンサーはI2C接続を使用します。以下に回路図を示します：

```
+---------------------+                 +----------------------+
|                     |                 |                      |
|   Raspberry Pi      |                 |   TCS34725           |
|                     |                 |   カラーセンサー      |
|                     |                 |                      |
|  +3.3V/5V  o--------+-----------------o  VIN                |
|                     |                 |                      |
|  GND       o--------+-----------------o  GND                |
|                     |                 |                      |
|  GPIO2/SDA o--------+-----------------o  SDA                |
|                     |                 |                      |
|  GPIO3/SCL o--------+-----------------o  SCL                |
|                     |                 |                      |
+---------------------+                 +----------------------+
```

#### 接続の詳細

1. **電源接続**:
   - Raspberry PiのVCC (3.3Vまたは5V) → TCS34725のVIN
   - Raspberry PiのGND → TCS34725のGND

2. **I2C接続**:
   - Raspberry PiのGPIO2 (SDA) → TCS34725のSDA
   - Raspberry PiのGPIO3 (SCL) → TCS34725のSCL

#### 注意点

- Raspberry Piで使用する場合、I2Cインターフェースを有効にする必要があります。
  ```bash
  sudo raspi-config
  ```
  から「Interface Options」→「I2C」を選択して有効化してください。

- プルアップ抵抗は通常TCS34725モジュール上に実装されていますが、長いケーブルを使用する場合や信号が不安定な場合は、SDAとSCLラインに4.7kΩのプルアップ抵抗を追加することを検討してください。

- 実際のセンサーモジュールによっては、追加のピン（INT：割り込み出力など）がある場合がありますが、このコードでは使用されていないため省略しています。

## トラブルシューティング

接続エラーが発生した場合は、以下を確認してください：

1. 証明書と秘密鍵が正しく配置されているか
2. AWS IoTポリシーが適切に設定されているか
3. ネットワーク接続が正常か
4. AWS認証情報（~/.aws/credentials）が正しく設定されているか

### サブスクライブタイムアウトエラーの対処方法

シャドウデルタの購読時に以下のようなエラーが発生する場合：

```
Subscribe timed out
AWSIoTPythonSDK.exception.AWSIoTExceptions.subscribeTimeoutException
```

以下の対処方法を試してください：

1. **AWS IoTポリシーの確認**：
   - シャドウ関連のトピックに対する権限が正しく設定されているか確認
   - 特に `$aws/things/{thing_name}/shadow/update/delta` トピックに対するサブスクライブ権限とレシーブ権限が必要

2. **ネットワーク接続の確認**：
   - AWS IoTエンドポイントへの接続が安定しているか確認
   - ファイアウォールやプロキシの設定を確認

3. **既存のポリシーを更新**：
   - 既存のポリシーを使用している場合は、`setup_aws_iot.py` を再実行して新しいポリシーを作成するか、AWS Management Consoleでポリシーを手動で更新

4. **タイムアウト設定の調整**：
   - 低速なネットワーク環境では、タイムアウト値を増やすことで解決する場合があります
   - `aws_iot_client.py` の `configureMQTTOperationTimeout` の値を調整（デフォルトは20秒）
