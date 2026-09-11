import serial
import socket
import time

# --- 設定項目 ---
# SO-101が接続されているシリアルポート（環境に合わせて変更してください）
# Windowsの例: 'COM3', Linux/Macの例: '/dev/ttyUSB0'
SERIAL_PORT = 'COM3' 
BAUD_RATE = 115200

# ホストPC（Parsecの接続先）のIPアドレスとポート
HOST_IP = '100.107.207.27'  # ホストPCのIPアドレスに書き換えてください
HOST_PORT = 5005

def main():
    # UDPソケットの準備
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"Connecting to SO-101 on {SERIAL_PORT}...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    except Exception as e:
        print(f"Serial connection failed: {e}")
        return

    print(f"Forwarding data to {HOST_IP}:{HOST_PORT} via UDP. Press Ctrl+C to stop.")
    
    try:
        while True:
            if ser.in_waiting > 0:
                # SO-101からのシリアルデータを1行読み込む
                data = ser.readline()
                
                # そのままホストPCへUDP送信
                sock.sendto(data, (HOST_IP, HOST_PORT))
                
                # デバッグ用（不要ならコメントアウトしてください）
                print(f"Sent: {data.decode('utf-8', errors='ignore').strip()}")
                
            time.sleep(0.001)  # CPU負荷下げのための微小なウェイト
            
    except KeyboardInterrupt:
        print("\nStopping client...")
    finally:
        ser.close()
        sock.close()

if __name__ == '__main__':
    main()
