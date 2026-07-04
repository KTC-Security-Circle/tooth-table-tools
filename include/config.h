#pragma once

// ── TB6600 ピン割り当て ────────────────────────────────────
#define PIN_STEP 8   // PUL+ へ接続
#define PIN_DIR  9   // DIR+ へ接続
#define PIN_ENA  10   // ENA+ へ接続（LOW = 有効）

// ── モーター初期値 ────────────────────────────────────────
#define DEFAULT_MAX_SPEED    1000.0f  // steps/sec
#define DEFAULT_ACCELERATION  500.0f  // steps/sec²
#define DEFAULT_STEPS         2400     // 1回の移動量（steps）

// ── 将来のスキャナー同期用 ────────────────────────────────
// スキャナー完了信号を受け取るピン（デジタル入力 / 割り込み）
#define PIN_SCAN_DONE 5
