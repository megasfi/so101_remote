import socket
import serial
import time
import json
import os
import threading
import queue

# --- 設定項目 ---
LISTEN_IP = '0.0.0.0'
LISTEN_PORT = 5005
FOLLOWER_PORT = 'COM4' 
BAUD_RATE = 1000000
MOTOR_IDS = [1, 2, 3, 4, 5, 6]

CALIB_PATH = r"C:\Users\CMISNOW03\.cache\huggingface\lerobot\calibration\robots\so_follower\my_follower.json"

position_queue = queue.Queue(maxsize=1)
running = True

def load_calibration_limits(path, motor_ids):
    if not os.path.exists(path): return None
    with open(path, 'r') as f: data = json.load(f)
    calib_map = {}
    joint_names = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
    for idx, m_id in enumerate(motor_ids):
        if idx >= len(joint_names): break
        j_name = joint_names[idx]
        if j_name in data:
            calib_map[m_id] = {
                "min": float(data[j_name]["range_min"]),
                "max": float(data[j_name]["range_max"])
            }
    return calib_map

def write_single_servo_position(ser, motor_id, position):
    """
    🚨【遅延解決のコア関数】
    SYNC WRITE（一括）を完全に廃止し、指定したサーボへ単発のWRITEパケットを
    最高速度（1Mbps）でダイレクトに送り込みます。
    """
    reg_start = 0x2A  # Goal_Positionレジスタ
    pos = max(0, min(4095, int(position)))
    
    low_byte = pos & 0xFF
    high_byte = (pos >> 8) & 0xFF
    
    length = 5
    inst = 0x03  # WRITE コマンド
    
    # チェックサムの計算
    checksum = (~(motor_id + length + inst + reg_start + low_byte + high_byte)) & 0xFF
    packet = bytes([0xFF, 0xFF, motor_id, length, inst, reg_start, low_byte, high_byte, checksum])
    
    ser.write(packet)

def robot_control_loop(ser, calib):
    """ 100Hzでロボットを滑らかに駆動し続ける独立スレッド """
    global position_queue, running
    
    current_positions = [2048.0] * 6
    target_raw_positions = [2048.0] * 6
    
    # 🚨 個別WRITE化によって基板側の渋滞が消えるため、
    # 追従スピードの上限を 12.0 から 25.0（約2倍の俊敏さ）へ引き上げます！
    MAX_STEP_PER_10MS = 25.0 
    
    print("【システム】遅延吸収追従スレッド（100Hz）が起動しました。")
    while running:
        try:
            target_raw_positions = position_queue.get_nowait()
        except queue.Empty:
            pass

        for i in range(len(MOTOR_IDS)):
            diff = float(target_raw_positions[i]) - current_positions[i]
            if abs(diff) > MAX_STEP_PER_10MS:
                step = MAX_STEP_PER_10MS if diff > 0 else -MAX_STEP_PER_10MS
            else:
                step = diff
            current_positions[i] += step
            
        int_positions = [int(x) for x in current_positions]
        
        # 🚨【全関節個別WRITEの超高速連射】
        # 1Mbpsの帯域を活かし、1番から6番のモーターへ1ミリ秒以下の隙間で連続パケットを叩き込みます。
        ser.reset_input_buffer()
        for idx, m_id in enumerate(MOTOR_IDS):
            write_single_servo_position(ser, m_id, int_positions[idx])
            
        ser.flush()  # すべてのパケットを一気に物理送信
        
        time.sleep(0.01)

def main():
    global position_queue, running
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, LISTEN_PORT))
    
    calib = load_calibration_limits(CALIB_PATH, MOTOR_IDS)
    if not calib: print("校正ロード失敗"); return
    print("⭕【成功】公式キャリブレーションデータを正常にロードしました。")

    try:
        ser = serial.Serial(FOLLOWER_PORT, BAUD_RATE, timeout=0)
        ser.set_buffer_size(rx_size=128, tx_size=128)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        print("【シリアル直通】ポートのクリーンオープンに成功しました。")
        
        # 全サーボのステータス返信を完全にシャットダウン
        print("【通信最適化】すべてのサーボのステータス返信を禁止に設定中...")
        for m_id in MOTOR_IDS:
            packet_mute = bytes([0xFF, 0xFF, m_id, 4, 0x03, 0x13, 0x00, (~(m_id + 4 + 0x03 + 0x13 + 0x00)) & 0xFF])
            ser.write(packet_mute)
            ser.flush()
            time.sleep(0.005)
            
        print("【ホスト】全関節独立WRITE・超低遅延モードで起動しました。")
    except Exception as e:
        print(f"Error: {e}"); return

    t = threading.Thread(target=robot_control_loop, args=(ser, calib))
    t.daemon = True
    t.start()

    try:
        while True:
            data, _ = sock.recvfrom(1024)
            try:
                message = data.decode('utf-8').strip()
                if not message: continue
                normalized_vals = [float(x) for x in message.split(',')]
                
                if len(normalized_vals) == len(MOTOR_IDS):
                    new_raw_positions = []
                    for idx, (m_id, norm_val) in enumerate(zip(MOTOR_IDS, normalized_vals)):
                        # 🚨手動反転を完全に撤廃し、公式キャリブレーションの方向をストレートに信じます
                        c = calib[m_id]
                        raw_val = int(c["min"] + (norm_val + 1.0) / 2.0 * (c["max"] - c["min"]))
                        new_raw_positions.append(raw_val)
                                           
                    if position_queue.full():
                        try: position_queue.get_nowait()
                        except queue.Empty: pass
                    position_queue.put_nowait(new_raw_positions)
                    
                    print(f"Applied (All Individual): {new_raw_positions}       ", end='\r')
            except: pass
    except KeyboardInterrupt: pass
    finally:
        running = False
        t.join(timeout=1.0)
        ser.close(); sock.close()
        print("\n安全に終了しました。")

if __name__ == '__main__': main()
