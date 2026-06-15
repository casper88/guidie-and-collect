# 06 — Roadmap

> 核心紀律:在**燒錢擴廠之前**,先用最小規模證明一句話——
> **「加我們的人類資料,買家需要的機器人 demo 數量減少 X 倍。」**
> 這句話(連同它的數字)就是整個商業模式能不能賣的試金石。

## Phase 0 — 資料契約(本 PR 所在階段)
- [x] VLA 可行性研究(`02_RESEARCH_VLA.md`)
- [x] 市場/競品分析(`03_MARKET_LANDSCAPE.md`)
- [x] 重新定位專案目的與流程(`01_VISION.md`)
- [x] 系統架構(`04_ARCHITECTURE.md`)
- [x] Master + Guidance Plan schema(`schema/`, `src/guidie_collect/`)
- [x] 驗證器 + LeRobot metadata 匯出(info/tasks/episodes/segments)+ 測試

## Phase 1 — 引導 MVP(沿用 PDF 既有系統)
- [ ] XMem + FoundationPose + RealSense 跑通單一插接任務
- [ ] Quest 3 當顯示(Passthrough Camera API 已可用)
- [ ] 驗證:完全沒經驗的人能否照引導完成插接
- [ ] 引導腳本編輯器最小版(輸出 `guidance_plan.json`)

## Phase 2 — 擷取管線(從第一天就含力)
- [ ] 同步記錄:egocentric RGB(D)、手部 26 joints、物件 6DoF、**力/接觸**、事件、時間戳
- [ ] 力/接觸 channel 硬體選型(插座力感測 / 觸覺手套 / 扭力扳手)
- [ ] 外部固定相機(抗手部遮擋)
- [ ] 多感測器對時 + 空間校正工具
- [ ] 寫成 Episode master 格式 → 過驗證器

## Phase 3 — 自動標註 + 閉環驗證(最關鍵的里程碑)
- [x] 由 guidance plan 自動產語言指令 + 步驟切段 + 成功判定 + 峰值力(`autolabel.py`)
- [ ] 抽檢 UI(人工品管)
- [ ] **A/B 實驗:有力覺 vs 無力覺**,各收一小批
- [ ] 微調 SmolVLA / π0,在便宜手臂(SO-101)量「達同樣成功率所需機器人 demo 數」
- [ ] 產出試金石數字(資料效率倍數)

## Phase 4 — 規模化 + 治理
- [ ] 多工人、多站、多零件
- [ ] 衍生 SKU:retarget 到 parallel-jaw / 常見靈巧手
- [ ] 資料版本控管(LeRobot Hub / 內部)

## 治理(Governance)— 賣資料的存亡關鍵
賣/授權資料給多個買家時,以下從加分項變成存亡項:
- [ ] **同意鏈(consent chain)**:每位作業員的錄製同意,去識別化(臉部模糊、ID hash);schema 已硬性要求 `meta.consent_ref`。
- [ ] **資料來源證明(provenance)**:買家(尤其大型機器人公司)會要求乾淨的來源/授權證明。
- [ ] **工廠 IP 授權**:工序、零件可能是機密;與工廠的資料權利歸屬要白紙黑字。
- [ ] **法遵**:台灣個資法(PDPA)/ 跨境買家可能涉 GDPR、生物特徵資料。
- [ ] **資安**:加密儲存、存取稽核(對標 Retrocausal 的 ISO 27001 / 臉部模糊)。

## 已知風險
- 純裸手→機器人轉移仍研究等級(見 `02`);因此定位為「省 demo 的乘數」而非「即插即用策略」。
- 合成/模擬資料(Isaac、world models)可能部分替代真實資料需求 → 見 `03_MARKET_LANDSCAPE.md` 的替代風險評估。
- 競品 Build AI(Egocentric-10K)已在純量上狂奔 → 我們的差異化必須是 **力覺 + 引導標註 + 工業工件**,不是比小時數。
