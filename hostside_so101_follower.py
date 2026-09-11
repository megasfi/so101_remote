import socket

# --- 設定項目 ---
# クライアントからのデータを受け取るポート（クライアント側と一致させる）
LISTEN_IP = '0.0.0.0'  # すべてのネットワークインターフェースから受け取る
LISTEN_PORT = 5005

def main():
    # UDPソケットの準備とバインド
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, LISTEN_PORT))
    
    print(f"Listening for SO-101 data on port {LISTEN_PORT}...")
    print("Waiting for data... Press Ctrl+C to stop.")

    try:
        while True:
            # データを受信 (バッファサイズは1024バイトで十分)
            data, addr = sock.recvfrom(1024)
            
            # バイトデータを文字列にデコード
            try:
                message = data.decode('utf-8').strip()
                
                # --- ここにLeRobotやロボット制御への流し込み処理を書く ---
                # 例: 解析して関節角度のリストにするなど
                # parse_so101_data(message)
                
                # デバッグ表示
                print(f"Received from {addr}: {message}")
                
            except UnicodeDecodeError:
                # バイナリデータなどのパース失敗対策
                print(f"Received raw bytes: {data}")

    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        sock.close()

if __name__ == '__main__':
    main()
