import socket
import time
import serial
import json
import os

# --- 設定項目 ---
SERIAL_PORT = 'COM3' 
BAUD_RATE = 1000000
HOST_IP = '100.107.207.27' # Tailscale IP
HOST_PORT = 5005
MOTOR_IDS = [1, 2, 3, 4, 5, 6]

CALIB_PATH = r"C:\Users\rsakai.CMI2014\.cache\huggingface\lerobot\calibration\teleoperators\so_leader\my_leader.json"

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

def read_feetech_position_fast(ser, motor_id):
    packet = bytes([0xFF, 0xFF, motor_id, 4, 0x02, 0x38, 2, (~(motor_id + 4 + 0x02 + 0x38 + 2)) & 0xFF])
    ser.write(packet)
    ser.flush()
    time.sleep(0.0005)
    if ser.in_waiting >= 8:
        res = ser.read(ser.in_waiting)
        for i in range(len(res) - 7):
            if res[i] == 0xFF and res[i+1] == 0xFF and res[i+2] == motor_id:
                return (res[i+6] << 8) | res[i+5]
    return None

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    calib = load_calibration_limits(CALIB_PATH, MOTOR_IDS)
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.01)
        print("【ローカル】ストレート正規化モードで起動しました。")
    except Exception as e:
        print(f"Error: {e}"); return

    try:
        while True:
            normalized_positions = []
            for m_id in MOTOR_IDS:
                raw_val = read_feetech_position_fast(ser, m_id)
                if raw_val is not None:
                    c = calib[m_id]
                    # 🚨 余計なガードやクリッピングはせず、公式キャリブレーションの比率のみで純粋に正規化
                    if c["max"] != c["min"]:
                        norm_val = -1.0 + 2.0 * (raw_val - c["min"]) / (c["max"] - c["min"])
                    else:
                        norm_val = 0.0
                    normalized_positions.append(norm_val)
                else:
                    break
            
            if len(normalized_positions) == len(MOTOR_IDS):
                message = ",".join(f"{x:.4f}" for x in normalized_positions)
                sock.sendto(message.encode('utf-8'), (HOST_IP, HOST_PORT))
                print(f"【送信中】{message}   ", end='\r')
                
            time.sleep(0.04) # ネット負荷を最適化する25Hz
    except KeyboardInterrupt: pass
    finally:
        ser.close(); sock.close()

if __name__ == '__main__': main()
