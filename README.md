# tooth-turntable

Arduino (Uno R4 WiFi) 製ターンテーブルのステッパーモーター制御ファームウェアと、角度を指定して回転させる Python CLI のセット。

- **ファームウェア** (`src/main.cpp`): AccelStepper で TB6600 ドライバ経由のステッパーを制御。シリアル経由で `move=`, `speed=`, `accel=`, `action=` コマンドを受け付け、JSON でステータスを返す。
- **CLI** (`scripts/turntable.py`): 角度(度)をステップ数に変換し、`move=` コマンドをシリアルで送信する。Uno R4 WiFi を USB の VID/PID から自動検出。

## 必要なもの

- [PlatformIO Core CLI](https://docs.platformio.org/en/latest/core/installation/index.html) (`pio` コマンド)
- [uv](https://docs.astral.sh/uv/) (Python 依存関係・実行環境の管理)
- ハードウェア: Arduino Uno R4 WiFi、TB6600 ステッパードライバ（配線は `include/config.h` のピン定義を参照: `PIN_STEP=8`, `PIN_DIR=9`, `PIN_ENA=10`）

## Quickstart

```sh
# Python 依存関係をインストール
make sync

# ファームウェアをビルド
make build

# Arduino へ書き込み
make upload

# シリアルモニタを開く（動作確認用）
make monitor

# 45度正転させる（別ターミナルから）
make move ANGLE=45

# -90度（逆転）
make move ANGLE=-90

# テスト・lint
make test
make lint

# CLI を単体実行ファイルにコンパイル（Nuitka）
make compile

# 上記を一通りまとめて実行（firmware build + compile + test + lint）
make all
```

すべてのターゲットは `make help` で一覧表示できます。

## シリアルプロトコル

CLI は改行区切りで `key=value` を `&` 連結して送信します。

```
move=1067&speed=1000&accel=500
```

- `move=<符号付きステップ数>` — 相対移動量（負の値で逆転）
- `speed=<steps/sec>` — 省略可、速度
- `accel=<steps/sec^2>` — 省略可、加速度

角度からステップ数への変換は `scripts/turntable.py` の `STEPS_PER_DEGREE`（モーター基本ステップ角・マイクロステップ設定・減速比から算出）に従います。
