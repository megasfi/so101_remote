import socket
import serial
import time
from lerobot.configs.robot_config import FeetechMotorsBusConfig
from lerobot.motors.feetech.feetech import FeetechMotorsBus

LISTEN_IP = '0.0.0.0'
LISTEN_PORT = 5005
FOLLOWER_PORT = 'COM4'
MOTOR_IDS = [1, 2, 3, 4, 5, 6]

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, LISTEN_PORT))
    
    print("【ホスト】LeRobot構成でフォロワーアームを初期化中...")
    try:
        motors_dict = {f"joint_{idx}": [m_id, "sts3215"] for idx, m_id in enumerate(MOTOR_IDS)}
        config = FeetechMotorsBusConfig(port=FOLLOWER_PORT, motors=motors_dict)
        
        # 🚨【ホスト側のキャリブレーションファイルをロード】
        config.calibration_path = "~/.cache/lerobot/calibration/my_follower/calibration_info.json"
        
        robot = FeetechMotorsBus(config)
        robot.connect()
        print("【ホスト】フォロワーアーム（校正適用済）の接続に成功！")
    except Exception as e:
        print(f"接続失敗: {e}")
        return

    print("【運行中】超低遅延・キャリブレーション連動モードでデータ受付中...")

    try:
        while True:
            data, _ = sock.recvfrom(1024)
            try:
                message = data.decode('utf-8').strip()
                if not message:
                    continue
                
                # 届いた正規化データ（-1.0 〜 1.0）をパース
                normalized_joints = {f"joint_{idx}": float(x) for idx, x in enumerate(message.split(','))}
                
                if len(normalized_joints) == len(MOTOR_IDS):
                    # 🚨【魔法の1行】LeRobotの内部関数「sync_write」に正規化データをそのまま渡します
                    # クラス内部の「_unnormalize」が働き、6番サーボには自動的に2047〜3503の範囲に変換された安全な生値が書き込まれます
                    ser.reset_input_buffer() # フリーズ防止に低レイヤのバッファクリアだけ残す
                    robot.sync_write("Goal_Position", normalized_joints)
                    
                    print(f"Applied (Normalized): {list(normalized_joints.values())}   ", end='\r')
            except Exception as e:
                print(f"\nエラー: {e}")
    except KeyboardInterrupt:
        pass
    finally:
        robot.disconnect()
        sock.close()

if __name__ == '__main__':
    main()
