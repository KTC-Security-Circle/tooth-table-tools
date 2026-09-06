#!/usr/bin/env python3
"""
Tooth Turntable - 角度指定シリアル送信ツール
角度(度)をステップ数に変換し、`move=<符号付きステップ数>` をArduinoへ直接送信する。

使い方:
  python scripts/turntable.py 45          # 45度分だけ正転
  python scripts/turntable.py -90         # 90度分だけ逆転
  python scripts/turntable.py 45 --port /dev/ttyACM0
"""

import argparse
import json
import sys
import time

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("pyserial が見つかりません。  pip install pyserial  を実行してください。")
    sys.exit(1)

# ── 設定 ──────────────────────────────────────────────────────────────────────
BAUD_RATE = 115200
ARDUINO_VID = 0x2341   # Arduino SA
ARDUINO_PID = 0x0069   # Uno R4 WiFi

# ── 角度→ステップ変換（config.h のハードウェア定数と合わせる） ─────────────────
MOTOR_STEPS_PER_REV = 200    # モーター基本ステップ角 1.8°/step
MICROSTEPPING = 16           # TB6600 側のマイクロステップ設定
GEAR_RATIO = 1.0             # ターンテーブル出力1回転あたりのモーター回転数（減速比）
STEPS_PER_DEGREE = MOTOR_STEPS_PER_REV * MICROSTEPPING * GEAR_RATIO / 360.0


def angle_to_steps(degrees: float) -> int:
    """角度(度、符号で方向)を符号付きステップ数に変換する。"""
    return round(degrees * STEPS_PER_DEGREE)


def find_port():
    ports = list(serial.tools.list_ports.comports())
    # Uno R4 WiFi の VID:PID で優先検索
    for p in ports:
        if p.vid == ARDUINO_VID and p.pid == ARDUINO_PID:
            return p.device
    # Arduino VID 全般でフォールバック
    for p in ports:
        if p.vid == ARDUINO_VID:
            return p.device
    # 最後の手段: 最初のポート
    return ports[0].device if ports else None


def send_move(ser: "serial.Serial", steps: int, speed: float | None = None, accel: float | None = None) -> None:
    """`move=` コマンドをシリアルへ送信する。speed/accel は同じ行にまとめて送る。"""
    parts = []
    if speed is not None:
        parts.append(f"speed={speed}")
    if accel is not None:
        parts.append(f"accel={accel}")
    parts.append(f"move={steps}")
    line = "&".join(parts) + "\n"
    ser.write(line.encode())


def wait_for_move_completion(ser: "serial.Serial") -> None:
    """Wait for a firmware status transition from running to idle.

    An idle status received before a running status is deliberately ignored: it
    may be a status left over from before the command was accepted.
    """
    observed_running = False

    while True:
        raw_line = ser.readline()
        if not raw_line:
            continue

        try:
            text = raw_line.decode("utf-8").strip() if isinstance(raw_line, bytes) else str(raw_line).strip()
            status = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Invalid firmware status JSON: {raw_line!r}") from exc

        if not isinstance(status, dict) or not isinstance(status.get("running"), bool):
            raise RuntimeError(
                "Firmware status is missing a boolean 'running' field: "
                f"{text!r}"
            )

        if status["running"]:
            observed_running = True
        elif observed_running:
            return


def main():
    parser = argparse.ArgumentParser(prog="turntable", description="角度指定でターンテーブルを回転させる")
    parser.add_argument("angle", type=float, help="回転角度(度)。符号で方向を指定")
    parser.add_argument("--port", help="シリアルポート（省略時は自動検出）")
    parser.add_argument("--speed", type=float, help="速度 (steps/sec)")
    parser.add_argument("--accel", type=float, help="加速度 (steps/sec^2)")
    args = parser.parse_args()

    port = args.port or find_port()
    if port is None:
        print("Arduinoが見つかりません。USBケーブルを確認してください。")
        sys.exit(1)

    steps = angle_to_steps(args.angle)
    print(f"シリアルポート: {port} ({BAUD_RATE} bps)")
    print(f"{args.angle} 度 -> {steps} steps")

    with serial.Serial(port, BAUD_RATE, timeout=1) as ser:
        time.sleep(2)  # Uno R4 のDTRリセット待ち（直後の送信は失われるため）
        send_move(ser, steps, speed=args.speed, accel=args.accel)
        wait_for_move_completion(ser)

    print("送信完了")


if __name__ == "__main__":
    main()
