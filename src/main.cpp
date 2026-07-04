#include <Arduino.h>
#include <AccelStepper.h>
#include "config.h"

// ── グローバル ────────────────────────────────────────────────────────────────
AccelStepper stepper(AccelStepper::DRIVER, PIN_STEP, PIN_DIR);

float g_maxSpeed = DEFAULT_MAX_SPEED;
float g_accel    = DEFAULT_ACCELERATION;
int   g_steps    = DEFAULT_STEPS;

static String         serialBuf  = "";
static unsigned long  lastStatus = 0;
static const unsigned long STATUS_INTERVAL = 200;  // ms

// ── スキャナー同期フック（将来実装） ─────────────────────────────────────────
// 例: attachInterrupt(digitalPinToInterrupt(PIN_SCAN_DONE), onScanComplete, RISING);
void onScanComplete() {
    stepper.move(g_steps);
}

// ── ユーティリティ ────────────────────────────────────────────────────────────
static String getParam(const String& line, const String& key) {
    String search = key + '=';
    int idx = line.indexOf(search);
    if (idx < 0) return "";
    idx += search.length();
    int end = line.indexOf('&', idx);
    return (end < 0) ? line.substring(idx) : line.substring(idx, end);
}

// ── コマンド処理（Serial受信行を解析） ────────────────────────────────────────
static void handleCmd(const String& line) {
    String spd = getParam(line, "speed");
    String acc = getParam(line, "accel");
    String stp = getParam(line, "steps");

    if (spd.length()) { g_maxSpeed = spd.toFloat(); stepper.setMaxSpeed(g_maxSpeed); }
    if (acc.length()) { g_accel    = acc.toFloat(); stepper.setAcceleration(g_accel); }
    if (stp.length())   g_steps    = stp.toInt();

    String action = getParam(line, "action");
    if      (action == "fwd")  stepper.move(g_steps);
    else if (action == "rev")  stepper.move(-g_steps);
    else if (action == "stop") stepper.stop();
    else if (action == "home") stepper.setCurrentPosition(0);
}

// ── Serial 受信（ノンブロッキング） ──────────────────────────────────────────
static void readSerial() {
    while (Serial.available()) {
        char c = (char)Serial.read();
        if (c == '\n') {
            serialBuf.trim();
            if (serialBuf.length() > 0) handleCmd(serialBuf);
            serialBuf = "";
        } else {
            serialBuf += c;
        }
    }
}

// ── ステータス送信（JSON 1行） ────────────────────────────────────────────────
static void sendStatus() {
    Serial.print(F("{\"pos\":"));      Serial.print(stepper.currentPosition());
    Serial.print(F(",\"running\":"));  Serial.print(stepper.isRunning() ? F("true") : F("false"));
    Serial.print(F(",\"cur_speed\":")); Serial.print(stepper.speed(), 1);
    Serial.print(F(",\"max_speed\":")); Serial.print(g_maxSpeed, 0);
    Serial.print(F(",\"accel\":"));    Serial.print(g_accel, 0);
    Serial.print(F(",\"steps\":"));    Serial.print(g_steps);
    Serial.println(F("}"));
}

// ── セットアップ ──────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);

    // TB6600 有効化（共通アノード配線: ＋端子=5V固定、ピンは帰線）
    // HIGH → 電位差なし → 電流なし → ENA非アクティブ → モーター励磁
    pinMode(PIN_ENA, OUTPUT);
    digitalWrite(PIN_ENA, HIGH);

    stepper.setMaxSpeed(g_maxSpeed);
    stepper.setAcceleration(g_accel);
    // 共通アノード配線では STEP/DIR の論理が反転するため両方を逆転させる
    stepper.setPinsInverted(true, true, false);
}

// ── メインループ ──────────────────────────────────────────────────────────────
void loop() {
    stepper.run();  // 台形プロファイルに従いステップパルスを出力

    readSerial();

    if (millis() - lastStatus >= STATUS_INTERVAL) {
        lastStatus = millis();
        sendStatus();
    }
}
