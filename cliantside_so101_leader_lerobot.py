import socket
import time
import serial

# --- 設定項目 ---
SERIAL_PORT = 'COM3' 
BAUD_RATE = 1000000  # 1Mbps

HOST_IP = '100.107.207.27'
HOST_PORT = 5005

# SO-101アームのモーターID（1番〜6番）
MOTOR_IDS =

def read_feetech_position(ser, motor_id):
    """
    Feetechサーボから現在位置を1つ読み出し、
    後ろのステータス/チェックサムを完全に分離して位置(0-4095)のみを返す
    """
    # 読み出しパケット送信
    length = 4
    inst = 0x02
    reg_start = 0x38
    reg_len = 2
    
    checksum = ~(motor_id + length + inst + reg_start + reg_len) & 0xFF
    packet = bytes([0xFF, 0xFF, motor_id, length, inst, reg_start, reg_len, checksum])
    
    # バッファを一度綺麗にしてから送信
    ser.reset_input_buffer()
    ser.write(packet)
    ser.flush()
    
    time.sleep(0.001)  # サーボの応答待ち
    
    # 応答パケット(通常8バイト)を確認
    if ser.in_waiting >= 8:
        response = ser.read(ser.in_waiting)
        
        # パケットのヘッダー(0xFF, 0xFF, ID)を正しく探索
        for i in range(len(response) - 7):
            if response[i] == 0xFF and response[i+1] == 0xFF and response[i+2] == motor_id:
                # 🚨【重要修正】response[i+5]と[i+6]が純粋な位置データ(リトルエンディアン)
                # response[i+7]以降に続くステータスやチェックサムの残骸は完全に無視します
                low_byte = response[i+5]
                high_byte = response[i+6]
                
                position = (high_byte << 8) | low_byte
                
                # 正常なSTS3215の範囲（0〜4095）に収まっているかチェック
                if 0 <= position <= 4095:
                    return position
    return None

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"【シリアル直通】リーダーアームに接続中 ({SERIAL_PORT} @ 1Mbps)...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.05)
        print("【シリアル直通】ポートのオープンに成功しました！")
    except Exception as e:
        print(f"【エラー】ポートを開けませんでした: {e}")
        sock.close()
        return

    print(f"データ転送を開始します ➡️ {HOST_IP}:{HOST_PORT}")
    
    try:
        while True:
            angles = []
            for motor_id in MOTOR_IDS:
                pos = read_feetech_position(ser, motor_id)
                if pos is not None:
                    angles.append(pos)
                else:
                    # 応答がないサーボがあれば、その周期はスキップしてバッファクリア
                    break
            
            # 指定したモーターの数（例：6個）と完全に一致するときのみ送信
            if len(angles) == len(MOTOR_IDS):
                message = ",".join(map(str, angles))
                sock.sendto(message.encode('utf-8'), (HOST_IP, HOST_PORT))
                # 画面には純粋な配列だけがきれいに表示されます
                print(f"【送信成功】生データ: {message}                    ", end='\r')
            else:
                print(f"【警告】サーボ通信同期中... 取得数: {len(angles)}/{len(MOTOR_IDS)}", end='\r')
                
            time.sleep(0.02)  # 50Hz周期
            
    except KeyboardInterrupt:
        print("\nStopping client...")
    finally:
        ser.close()
        sock.close()

if __name__ == '__main__':
    main()

