# 05 — 資料規格(Data Spec)

這是整個專案的**地基**。兩個 schema:

1. **Guidance Plan**(`schema/guidance_plan.schema.json`)— 工廠編寫的工序定義,**同時就是標註 schema**。
2. **Episode**(`schema/episode.schema.json`)— 一次作業錄製產生的 embodiment-agnostic master 資料。

設計原則(來自 `02_RESEARCH_VLA.md`):
- **Embodiment-agnostic master**:存最上游的人類表示法,不綁機器人形態。
- **Force/contact 是一等公民**:對插接任務是護城河,schema 必須原生支援。
- **引導腳本即標註**:語言指令、步驟切段、成功判定都從 guidance plan 來,自動產生。
- **可匯出 LeRobot**:master 經 retarget/扁平化後可輸出成 LeRobot dataset。

---

## Guidance Plan(引導腳本 = 標註 schema)

```jsonc
{
  "plan_id": "plug_insertion_v1",
  "version": "1.0.0",
  "task_name": "依序插接前面板連接器",
  "language": "zh-TW",
  "objects": [
    { "object_id": "harness",  "name": "線束",   "model_ref": "models/harness.obj" },
    { "object_id": "panel",    "name": "前面板", "model_ref": "models/panel.obj" }
  ],
  "steps": [
    {
      "step_id": "s1",
      "order": 1,
      "type": "insert",                       // insert | fasten | place | route | inspect
      "instruction": "把電源接頭插入 J1 插座",   // 自動成為語言標籤
      "target": { "object_id": "panel", "point_id": "J1" },
      "success_criterion": {
        "type": "force_threshold",            // force_threshold | pose_match | manual_confirm | click_detected
        "force_n": 35.0,                      // 預期插入力(用於自動判定 + 力覺標籤)
        "tolerance_mm": 1.0
      }
    }
  ]
}
```

`success_criterion.type` 決定該步驟「完成」如何自動判定,也決定要收哪種 channel:
- `force_threshold` / `click_detected` → **需要力/接觸 channel**(插接任務預設)。
- `pose_match` → 由 FoundationPose 6DoF 判定。
- `manual_confirm` → 作業員按 Enter(沿用 PDF 系統的互動)。

---

## Episode(master 資料,一次作業一筆)

```jsonc
{
  "episode_id": "ep_0001",
  "plan_id": "plug_insertion_v1",
  "plan_version": "1.0.0",
  "meta": {
    "site_id": "site_A_hashed",             // 去識別化
    "operator_id": "op_017_hashed",         // 去識別化
    "consent_ref": "consent/2026-06-15.json",
    "recorded_at": "2026-06-15T08:00:00Z",
    "device": { "headset": "Quest3", "horizonos": "v83", "external_cam": "RealSense_D435i" },
    "calibration_ref": "calib/site_A_2026-06-15.json"
  },
  "streams": {
    "egocentric_rgb":  { "uri": "ep_0001/ego_rgb.mp4",  "fps": 30, "resolution": [1280, 960] },
    "egocentric_depth":{ "uri": "ep_0001/ego_depth.mp4", "fps": 30 },
    "external_rgb":    { "uri": "ep_0001/ext_rgb.mp4",  "fps": 30 },
    "head_pose":       { "uri": "ep_0001/head_pose.parquet" },   // SE(3) per frame
    "hand_pose":       { "uri": "ep_0001/hand_pose.parquet",     // 26 joints L/R (+ 可選 MANO)
                         "representation": "joints26", "hands": ["left", "right"] },
    "object_poses":    { "uri": "ep_0001/object_poses.parquet",  // 每個 tracked object 6DoF
                         "objects": ["harness", "panel"] },
    "force":           { "uri": "ep_0001/force.parquet",         // 護城河 channel
                         "sources": [
                           { "source_id": "socket_J1", "type": "force_1d", "unit": "N" },
                           { "source_id": "wrench",    "type": "torque",   "unit": "Nm" }
                         ] }
  },
  "steps": [                                  // 自動切段 + 標籤(由 guidance plan + events 產生)
    {
      "step_id": "s1",
      "instruction": "把電源接頭插入 J1 插座",
      "t_start": 2.40, "t_end": 6.85,
      "outcome": "success",                   // success | fail | corrected
      "peak_force_n": 36.2
    }
  ],
  "events": [                                 // 離散事件(對時用)
    { "t": 2.40, "type": "step_start",   "step_id": "s1" },
    { "t": 6.85, "type": "step_success", "step_id": "s1" }
  ]
}
```

### 時間軸契約
- 所有 stream 與 events 共用**同一個 episode 時鐘**(秒,float,從 0 起)。
- 連續訊號存 Parquet(每列一個 timestamp);影像存 MP4(靠 fps + 起始時間戳對齊)。這與 LeRobot 的「Parquet + MP4」一致,降低匯出阻抗。

### 為何這樣設計可匯出 LeRobot
LeRobot = 每 timestep 一列(action/observation/proprio)+ 影像 MP4。匯出器(`export_lerobot.py`)把上面的 master 在一個固定取樣率上 resample,並把選定的「動作來源」(例如手腕 6DoF + 夾爪寬度,或 retarget 後的關節角)填入 LeRobot 的 `action` 欄,影像填 observation,force/contact 填額外 feature。

**目前已實作**:寫出 LeRobot 風格(v2.1)的 `meta/` 目錄——`info.json`(feature schema + 總數)、`tasks.jsonl`(語言任務,直接取自 guidance plan)、`episodes.jsonl`(每集長度/任務),以及 G&C 擴充的 `segments.jsonl`(保留逐步語言切段,這是差異化)。
**尚未實作**:解碼 MP4 / 寫出每 timestep 的資料 Parquet——需實際擷取的二進位檔與 pin 定的 `lerobot` 版本。

```bash
python -m guidie_collect.export_lerobot <plan.json> <episode.json>... -o <out_dir>
```

---

## Raw Capture → 自動標註 → Master(引導即標註的執行)

MR runtime 吐出的是 **raw capture**(尚未標註):stream 參照 + 一串離散事件
(`step_start` / `step_success` / `step_fail` / `correction`),以及 force 取樣
(實務在 Parquet,範例/測試允許 inline 在 `force_samples`)。`autolabel` 把它
+ guidance plan **自動**轉成上面的 master `steps`,無需人工標註:

| 標籤 | 來源 |
|---|---|
| 切段 `t_start`/`t_end` | start 與 terminal 事件配對 |
| 語言 `instruction` | 從 plan step 複製 |
| `outcome`(success/fail/corrected) | terminal 事件;有 `correction` → `corrected` |
| `peak_force_n` | 僅 `force_threshold` 步驟,取該目標點 force 視窗內 max |value| |

```bash
python -m guidie_collect.autolabel \
    schema/examples/plug_insertion.plan.json \
    schema/examples/plug_insertion.capture.json -o ep_0002.episode.json
```

> 產出的 episode **刻意不含** `force_samples`,以符合 `episode.schema.json`
> (master 透過 `streams.force.uri` 指向 Parquet,而非內嵌取樣)。
> 範例輸入見 `schema/examples/plug_insertion.capture.json`。

## 不變式(驗證器會檢查)
1. episode 的 `plan_id` 必須存在對應 guidance plan(契約一致)。
2. 每個 `steps[].step_id` 必須出現在 guidance plan 的 steps 裡。
3. `t_start < t_end`,且落在 episode 時長內;steps 不重疊(除非標記為 `corrected` 的重試)。
4. 若任一 step 的 success_criterion 是 `force_threshold`/`click_detected`,則 episode **必須**有 `force` stream(否則該資料對插接任務價值大減 → 驗證警告)。
5. `meta.consent_ref` 必填(治理硬性要求)。

> 不變式 4 把「力覺是護城河」這個結論直接寫進資料契約:沒有力覺的插接資料會被標記為低價值。
