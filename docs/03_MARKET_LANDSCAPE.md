# 03 — 市場 / 競品分析(2026 年中)

> 整理自 4 個角度的 deep research。數字多來自二手報導/搜尋摘錄(多數一手頁面 403),屬 directional,引用前建議再核。

## 大結論

1. **「資料是瓶頸」已是業界共識**:Jim Fan(NVIDIA)、Sergey Levine(Physical Intelligence)、Ken Goldberg(「10 萬年資料缺口」)、Figure、Bessemer 一致。全球機器人操作資料僅約 **30 萬小時**,vs 網路影片約 10 億小時(Bessemer 估未來兩年機器人資料花費 >$30 億)。
2. **「為機器人收資料」已是一個有資金的新賽道**:Mecka($60M)、Encord($60M Series C,服務 Physical Intelligence/Dyna)、Generalist GEN-0(27 萬小時、每週 +1 萬)、Build AI(Egocentric-10K→1M)、Sensei(YC,$300 外骨骼)、OMGrab、PrismaX、Teleo……
3. **但有兩塊白地(white space)**——正是本專案的定位:
   - **「引導 + 為 AI 收集」的合流**:沒有人把「給作業員真實價值的引導」與「收機器人訓練資料」做成同一個產品。
   - **「工業 contact-rich 人類示範資料當商品」**:被點名為文獻缺口,且 >90% 線束/連接器裝配仍是手工 → 幾乎沒有現存資料;也是合成資料最難偽造的一塊。

## 三個 cluster 與它們的盲點

### A. 工作指引 / Connected Worker(有錄資料,但只給人看)
Taqtile Manifest、PTC Vuforia Expert Capture、MS Dynamics 365 Guides(**2026/12 退場**,HoloLens 2 已停產)、Augmentir、Tulip、LightGuide、Scope AR。
- 都會錄第一視角影片 / 執行資料,但**目的是產生人類指引、產線品質、人因分析**,沒有人定位成機器人/VLA 訓練語料。
- 最接近「引導+擷取」的是 **Retrocausal**(Assembly Copilot:即時引導 + 數位化整個流程),但資料產品仍是人看的 analytics。

### B. 機器人資料收集 / 販售(只收,不引導)
| 公司 | 模式 | 訊號 |
|---|---|---|
| Mecka AI | 賣人類動作資料(體感+iPhone),客戶 1X | $60M,自稱 "Scale AI of robotics data" |
| Encord | Physical AI 資料基建,服務 PI/Dyna | $60M Series C,>5PB |
| Sensei (YC) | 群眾外包 + $300 外骨骼臂 | "Scale AI for robotics" |
| Generalist AI | GEN-0,UMI 手持夾爪,純人類採集 | 27 萬小時,每週 +1 萬,提出 scaling law |
| Build AI | 自製頭戴相機,工廠第一視角 | Egocentric-10K(1 萬小時)→ 目標 100 萬(2026/4) |
| OMGrab / Genesis AI / X² / PrismaX / Teleo | 頭帶相機 / 資料手套 / UMI / teleop | 各自募資中 |
- 共同點:**只記錄,不在現場引導作業員完成有價值的工序**;且絕大多數是**純影像 / kinematic,沒有力覺**。

### C. 公開資料集(免費基準線,我們必須贏過它的「specificity」)
Apple **EgoDex**(829 小時、68 關節、Vision Pro)、Meta **Ego-Exo4D**(1,286 小時)、**AgiBot World**(~100 萬軌跡,開源)、DROID、RoboMIND、Open X-Embodiment(~240 萬軌跡)。
- 大多 lab/kitchen/home;**工業 contact-rich 嚴重不足**;**幾乎都沒有力/觸覺**。

## 競爭定位:G&C 的護城河 = 三者交集

```
          引導即標註                工業 contact-rich
       (real operator ROI)          (連接器/線束/金屬)
                \                       /
                 \         ★ G&C       /
                  \  (沒有人同時佔三者) /
                   \--------+---------/
                            |
                       力 / 接觸 channel
                  (vs 純影像競品的差異化)
```

- vs **A 類**(工作指引):我們把擷取**重新定位為機器人訓練語料**,並用引導腳本**自動標註**。
- vs **B 類**(資料收集):我們**不比小時數**(打不過 Generalist/Build AI 的量),而是用**力覺 + 引導自動標籤 + 工業真實工件**做差異化;而且引導本身對工廠有獨立 ROI(新手上線、品質),收資料是順帶。
- vs **C 類**(公開集):我們贏在 specificity——工業工件 + 力覺 + 步驟語言標註。

## 風險(誠實版)

1. **合成資料替代**:NVIDIA DreamGen/Cosmos、world models 明確要降低真實 teleop 需求,資源雄厚、進步快。**但 sim2real 在接觸動力學/摩擦/可變形(線束)最弱**——正好是我們的niche,這是相對防禦點。
2. **量的軍備競賽**:Generalist / Build AI 在純量上狂奔。→ 不要跟。守差異化。
3. **大廠囤資料**:Figure 把自有 field data 當護城河,可能不買。→ 買家更可能是缺資料的 VLA 新cre構、手臂 OEM、系統整合商、以及工廠自用。
4. **隱私/法遵是高牆也是護城河**:GDPR Art.9(生物特徵需明確同意且須具名「AI 訓練」用途)、EU AI Act、台灣 PDPA;勞雇關係下「同意」易被認定不自由。誰先把同意鏈/去識別化做對,誰就有進入障礙保護。

## 定價參考(directional)
- 高品質 teleop 資料:~$340/hr(2024)→ ~$136/hr(Q4 2025)。
- 語言/任務標註:人工 $0.25–1.00/episode;VLM 輔助 $0.05–0.10/episode。
- Marketplace:SVRC 每 episode 自訂價,低至 ~¥4。
→ 我們的「引導自動標註」直接吃掉標註成本;「力覺 + 工業工件」支撐高於商品價的定價。
