import serial
import time

FOLLOWER_PORT = 'COM4'  # 環境に合わせて変更
BAUD_RATE = 1000000     # 1Mbps

def read_register(ser, motor_id, reg_start, reg_len):
    """ 指定したレジスタのアドレスからデータを読み出す """
    length = 4
    inst = 0x02  # READ
    checksum = ~(motor_id + length + inst + reg_start + reg_len) & 0xFF
    packet = bytes([0xFF, 0xFF, motor_id, length, inst, reg_start, reg_len, checksum])
    
    ser.reset_input_buffer()
    ser.write(packet)
    ser.flush()
    time.sleep(0.005)
    
    if ser.in_waiting >= 8:
        res = ser.read(ser.in_waiting)
        for i in range(len(res) - 7):
            if res[i] == 0xFF and res[i+1] == 0xFF and res[i+2] == motor_id:
                if reg_len == 2:
                    return (res[i+6] << 8) | res[i+5]
                return res[i+5]
    return None

def main():
    print(f"【スキャン開始】ポート {FOLLOWER_PORT} に接続されたFeetechサーボを探索中...")
    try:
        ser = serial.Serial(FOLLOWER_PORT, BAUD_RATE, timeout=0.05)
    except Exception as e:
        print(f"エラー: ポートを開けませんでした: {e}")
        return

    # ID 1番から15番までを総当たりでチェック
    found_any = False
    for m_id in range(1, 16):
        # アドレス0x38（現在位置）が返ってくるかチェックして、サーボの存在確認
        pos = read_register(ser, m_id, 0x38, 2)
        
        if pos is not None:
            found_any = True
            # サーボが存在したら、そのサーボの「最小制限（0x09）」と「最大制限（0x0B）」を読み出す
            min_limit = read_register(ser, m_id, 0x09, 2)
            max_limit = read_register(ser, m_id, 0x0B, 2)
            
            print(f" Found Servo [ ID: {m_id} ]")
            print(f"   - 現在位置 : {pos}")
            print(f"   - 最小可動域限制 (Min Limit): {min_limit}")
            print(f"   - 最大可動域限制 (Max Limit): {max_limit}")
            print("-" * 40)
            
    if not found_any:
        print("警告: サーボが1つも見つかりませんでした。12V電源や配線、ポート番号を確認してください。")
        
    ser.close()

if __name__ == '__main__':
    main()
