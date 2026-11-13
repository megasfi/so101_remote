import socket
import serial
import time

LISTEN_IP = '0.0.0.0'
LISTEN_PORT = 5005
FOLLOWER_PORT = 'COM4'  # 環境に合わせて変更
BAUD_RATE = 1000000     # 1Mbps
MOTOR_IDS = [1, 2, 3, 4, 5, 6]

def read_servo_status(ser, motor_id):
    """ 指定したサーボから「現在位置」と「エラー」を読み出す """
    reg_start = 0x38
    reg_len = 2
    length = 4
    inst = 0x02  # READ
    checksum = ~(motor_id + length + inst + reg_start + reg_len) & 0xFF
    packet = bytes([0xFF, 0xFF, motor_id, length, inst, reg_start, reg_len, checksum])
    
    ser.write(packet)
    ser.flush()
    time.sleep(0.001)
    
    if ser.in_waiting >= 8:
        res = ser.read(ser.in_waiting)
        for i in range(len(res) - 7):
            if res[i] == 0xFF and res[i+1] == 0xFF and res[i+2] == motor_id:
                error_code = res[i+4]
                pos = (res[i+6] << 8) | res[i+5]
                return pos, error_code
    return None, None

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, LISTEN_PORT))
    
    try:
        ser = serial.Serial(FOLLOWER_PORT, BAUD_RATE, timeout=0.02)
        ser.reset_input_buffer()
        print("【検証モード】フォロワーポートのオープンに成功。")
    except Exception as e:
        print(f"Error: {e}")
        return

    print("【検証中】手元のグリッパー（爪）を『全開』と『全閉』に動かして数値を観察してください。")

    try:
        while True:
            data, _ = sock.recvfrom(1024)
            try:
                message = data.decode('utf-8').strip()
                if not message:
                    continue
                joints = [int(x) for x in message.split(',')]
                
                if len(joints) == len(MOTOR_IDS):
                    # 🚨【超重要】実機へは書き込まず、読み出しのみを行って安全に数値を比較します
                    ser.reset_input_buffer()
                    
                    # 手元のリーダーアームの6番目（インデックス5）の数値
                    leader_gripper = joints
                    
                    # 実機フォロワーアームの6番サーボの「現実の生データ」
                    follower_gripper, err = read_servo_status(ser, 6)
                    
                    print(f"手元（リーダー）の爪: {leader_gripper}  ||  実機（フォロワー）の爪: {follower_gripper} (Err:{err})        ", end='\r')
            except:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        sock.close()

if __name__ == '__main__':
    main()
