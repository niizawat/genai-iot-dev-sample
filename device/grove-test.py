#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TCS34725カラーセンサーのテストスクリプト
"""

import time
import board
import busio
import adafruit_tcs34725


def main():
    """
    メイン関数
    """
    print("TCS34725カラーセンサーのテストを開始します...")
    
    # I2Cバスの初期化
    i2c = busio.I2C(board.SCL, board.SDA)
    
    try:
        # TCS34725センサーの初期化
        sensor = adafruit_tcs34725.TCS34725(i2c)
        
        # センサーの設定
        sensor.integration_time = 50  # ミリ秒
        sensor.gain = 4  # ゲイン設定 (1, 4, 16, 60)
        
        print("TCS34725カラーセンサーを初期化しました")
        print("10回の読み取りを行います...")
        
        # 10回の読み取りを行う
        for i in range(10):
            # RGB値の取得
            r, g, b, c = sensor.color_raw
            
            # 色温度の取得
            color_temp = sensor.color_temperature
            
            # 明るさの取得
            lux = sensor.lux
            
            # RGB値の正規化（0-255の範囲に変換）
            max_val = max(r, g, b, 1)  # ゼロ除算を防ぐ
            r_norm = int(r / max_val * 255) if max_val > 0 else 0
            g_norm = int(g / max_val * 255) if max_val > 0 else 0
            b_norm = int(b / max_val * 255) if max_val > 0 else 0
            
            # 16進数のカラーコード
            hex_color = "#{:02X}{:02X}{:02X}".format(r_norm, g_norm, b_norm)
            
            # 結果の表示
            print(f"\n読み取り {i+1}:")
            print(f"生のRGB値: R={r}, G={g}, B={b}, C={c}")
            print(f"正規化RGB値: R={r_norm}, G={g_norm}, B={b_norm}")
            print(f"カラーコード: {hex_color}")
            print(f"色温度: {color_temp}K")
            print(f"明るさ: {lux} lux")
            
            # 1秒待機
            time.sleep(1)
            
        print("\nテストが完了しました")
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")


if __name__ == "__main__":
    main()
