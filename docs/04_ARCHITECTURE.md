# 04 — 系統架構

G&C 拆成四個鬆耦合的子系統。核心設計原則:**引導腳本(guidance plan)即標註 schema**——同一份東西既驅動「給作業員看的引導」,也定義「自動產生的訓練標籤」。

```
┌─ 1. 引導腳本編輯器 (Authoring) ──────────────────────────────┐
│  工廠把自己的工序定義成任務圖:                                │
│  物件、步驟順序、目標點、成功判定(含 expected force)         │
│  輸出: guidance_plan.json  ← 這份就是「標註 schema」          │
└───────────────────────────────┬──────────────────────────────┘
                                 │ 載入
┌─ 2. MR 引導 + 擷取 Runtime ─────▼────────────────────────────┐
│  收集端 (現場)                    運算端 (工作站/GPU)         │
│  Meta Quest 3                      XMem(分割)               │
│   • Passthrough RGB(D)  ─串流──→   FoundationPose(6DoF)      │
│   • 手部 26 joints                 最近 Label 點 → 引導決策    │
│   • 頭部 6DoF             ←─AR──   (回送疊加畫面)            │
│  + 固定外部相機(抗遮擋)                                      │
│  + 力 / 接觸感測(關鍵)── 扭力扳手 / 插座力感測 / 觸覺手套     │
└───────────────────────────────┬──────────────────────────────┘
                                 │ 同步打包 (時間戳對齊 + 空間校正)
┌─ 3. 自動標註 + 匯出 Pipeline ───▼────────────────────────────┐
│  以 guidance_plan 為 schema:                                  │
│   • 語言指令 / 步驟切段(自動)                                │
│   • 成功 / 失敗 / 修正事件                                     │
│   • 對齊各 stream → 內部 master 格式 (embodiment-agnostic)     │
│  抽檢 UI(人工品管)→ 版本控管                                 │
│  匯出: LeRobot dataset(+ 可選 retargeted SKU)                │
└───────────────────────────────┬──────────────────────────────┘
                                 ▼
┌─ 4. 資料產品 / 訓練 (Consume) ───────────────────────────────┐
│  • 工廠自用:微調 SmolVLA / π0 / GR00T N1.5                    │
│  • 對外:授權 / 販售 embodiment-agnostic master + 衍生格式     │
└──────────────────────────────────────────────────────────────┘
```

## 兩層資料表示法

| 層 | 內容 | 用途 |
|---|---|---|
| **Master(本專案的主資產)** | embodiment-agnostic:egocentric RGB(D) + 手部 26 joints/MANO + 物件 6DoF + **force/contact** + 語言 + 步驟切段 + 事件 | 保留最完整資訊,可被任何買家 retarget;這是會賣的東西 |
| **Derived(衍生 SKU)** | retarget 到特定 embodiment(parallel-jaw / 常見靈巧手),匯出成 **LeRobot** | 直接可訓練;降低買家門檻 |

> 為何不直接只存 LeRobot?因為 LeRobot 綁定一個動作空間(某個 robot embodiment),會**犧牲通用性**。我們存更上游的 master,再匯出。詳見 `05_DATA_SPEC.md`。

## 本 repo 的範圍邊界

| 子系統 | 本 repo | 後續/外部 |
|---|---|---|
| 1 引導腳本 schema | ✅ `schema/guidance_plan.schema.json` | 編輯器 UI |
| 2 MR runtime | ❌(需 Quest/Unity 硬體) | Unity + Quest app |
| 2 即時感知 | ❌ | XMem / FoundationPose 整合 |
| 3 master schema + 驗證 + LeRobot 匯出 | ✅ `src/guidie_collect/` | 抽檢 UI |
| 4 訓練 | ❌ | 接 openpi / lerobot / GR00T |

本 repo 先把 **1 與 3 的「資料契約(data contract)」** 釘死——這是其他所有子系統共同依賴的地基。
