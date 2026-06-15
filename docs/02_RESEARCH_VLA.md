# 02 — VLA 可行性研究:人類示範資料 → retargeting → 微調 VLA

> 整理自 2025–2026 文獻的 deep research。**所有數字均為原文自報(as-reported)**,跨論文不可直接比較,且多為作者自建 benchmark、小 N(~10–20 次/任務)評估,印成正式文件前建議再核對原始 PDF。部分為 2026 年極新預印本(arXiv 26xx.x),屬 preliminary。

## 一句話結論

用「引導+收集」蒐集人類示範資料,當作 VLA 的 **pretraining / co-training** 來**提升資料效率,是可落地的**;但用純「影像 + 手部 kinematic」資料**直接得到可部署的插接策略,仍是研究等級**。而插接(connector insertion)恰好是 vision-only + 純運動學資料**最弱**的任務——因此資料的價值關鍵在於有沒有抓到 **力 / 接觸**。

## 可行度判斷

| 目標 | 2026 年中狀態 |
|---|---|
| 人類資料當 pretraining/co-training 提升 VLA 資料效率 | ✅ 可落地 |
| 人手 → 夾爪/機械手 retargeting | ✅ 工程成熟(開源工具) |
| 純「影像+手追」→ 直接部署插接策略(無機器人資料) | ❌ 研究等級 |
| 賣「通用人類資料集」 | 🟡 可行,但須含力覺 + 工業工件 + 自動標註 |

## 關鍵實證發現

### 1. Retargeting 已是成熟工程(且開源)
- `dex-retargeting`(MIT, `pip install`):三種優化器,輸出機器手關節角。 <https://github.com/dexsuite/dex-retargeting>
- UMI(手持夾爪):EE 6DoF + 夾爪寬度,Diffusion Policy,跨機器人 100%→90%。 <https://arxiv.org/abs/2402.10329>
- DexUMI(外骨骼):兩種機械手平均 **86%**,收資料快 **3.2×**。 <https://arxiv.org/abs/2505.21864>
- DexCap(手套+SLAM):LEAP 手 IK,~30 分鐘人類資料可學策略。 <https://dex-cap.github.io/>
- ⚠️ retargeting 轉的是**運動學**,不含接觸力。

### 2. 人類資料的價值在「資料效率」,不是單獨可用
- EgoMimic 共訓 **+34–228%**(未見環境 +51%)。 <https://egomimic.github.io/>
- 人類預訓練平均 **+40%** finetune 提升(MotionTrans);GR00T 用 10% 資料達 4× 效果;LAPA 用 30× 更少算力超過 OpenVLA。 <https://arxiv.org/abs/2410.11758>
- ⚠️ **關鍵負面結果**:EgoVLA 不微調機器人 = **0% zero-shot**;純人類影片廣泛轉移平均僅 ~20%(MotionTrans)。 <https://arxiv.org/abs/2507.12440>
- ➡️ 人類資料是「省機器人 demo」的乘數,不是「免機器人 demo」的替代品。

### 3. Embodiment gap:裸手轉移仍是研究等級
- 每筆 demo 約 **8 個百分點**精度懲罰;要 **~3 倍**人類 demo 才追平 teleop(Phantom)。 <https://arxiv.org/abs/2503.00779>
- 最有效縮小 gap 的是「用硬體讓人類介面對齊機器人」(UMI ~70%、DexUMI 86%),而非直接消除視覺差。
- 產業現況:人形機器人仍以 **teleoperation** 為主要資料管線。 <https://www.bain.com/insights/humanoid-robots-from-demos-to-deployment-technology-report-2025/>

### 4. 插接任務是 contact-rich,vision-only 不夠(本專案任務命門)
- NIST 連接器基準:**±1mm 誤差就一致性失敗**。 <https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=935275>
- 加力覺的實測:privileged 策略 96.74%→**98.96%**;視覺策略 93.23%→**96.09%**;**ForceVLA** 平均 **+23.2%**、插頭最高 **80%**;**CRAFT**(力覺課程微調 π0)**+35 個百分點**。 <https://arxiv.org/abs/2505.22159>
- ⚠️ 標準手部追蹤/mocap **抓不到接觸力**(DexCap 明確省略觸覺)。補法:FeelTheForce 觸覺手套零機器人資料達 **77%**;或儀器化工具(如扭力扳手扭矩)、DexUMI/DEXOP 外骨骼。 <https://feel-the-force-ftf.github.io/>

### 5. 實務工具鏈現成(含一個重要綠燈)
- **資料格式**:**LeRobot(HuggingFace)是收斂點**——openpi(π0)、GR00T N1.5、SmolVLA 都吃它;RLDS/OXE 屬 OpenVLA/Octo 舊棧。**別自創格式。**
- **可微調 base VLA**:SmolVLA(450M,單張消費級 GPU)、π0/π0.5(openpi, Apache-2.0, LoRA ~22.5GB)、GR00T N1.5(3B,可降到 RTX 4090)、OpenVLA-OFT(7B)。
- 🟢 **Quest 3 原始相機已可用**:Passthrough Camera Access API 正式可上架——前置雙 4MP RGB,1280×960@30fps(v83 有 1280×1280),需 HorizonOS v74+,自 ~v76(2025 春)Store app 可發佈。 <https://github.com/xrdevrob/QuestCameraKit> · <https://www.uploadvr.com/quest-passthrough-camera-api-now-shippable-on-store/>

## 對本專案的設計含義(directly drives the data spec)

1. **主資產要 embodiment-agnostic**:保留人類標準表示法(手部 26 joints / MANO + 物件 6DoF + 影像 + 語言),retargeting 留給下游/買家。
2. **力 / 接觸 channel 是護城河,不是可選項**——尤其對插接任務。資料 schema 必須一等公民地容納 force/contact。見 `05_DATA_SPEC.md`。
3. **誠實的價值主張 = 「省 demo 的乘數」**,不是「即插即用策略」。MVP 要證明的數字:「加我們的人類資料,買家需要的機器人 demo 數量減少 X 倍」。

## 來源(節錄)

retargeting:dex-retargeting / AnyTeleop(2307.04577)、UMI(2402.10329)、DexUMI(2505.21864)、DexCap、Bunny-VisionPro(2407.03162)、EgoMimic(2410.24221)、EgoVLA(2507.12440)、R+X(2407.12957)。
human-data→VLA:Phantom(2503.00779)、H2R(2505.11920)、LAPA(2410.11758)、GR00T N1.5(2503.14734)、RynnVLA-001(2509.15212)、VITRA、In-N-On(2511.15704)、Open X-Embodiment(2310.08864)。
contact-rich:InsertionNet 2.0(2203.01153)、ForceVLA(2505.22159)、CRAFT、FMB(2401.08553)、REASSEMBLE(2502.05086)、FeelTheForce(2506.01944)、NIST ATB。
工具鏈:LeRobot、openpi、GR00T N1.5、SmolVLA(2506.01844)、OpenVLA-OFT(2502.19645)、QuestCameraKit。
