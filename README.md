# guidie-and-collect

> **Guide workers. Collect the data.**
> 一套「**邊引導現場作業員、邊自動產生 VLA 訓練資料**」的工業資料平台。

`guidie-and-collect`(簡稱 **G&C**)的核心假設:一套為了「引導完全沒經驗的人完成裝配工序」而打造的 MR 系統,**為了引導本來就必須即時追蹤** 〔工件姿態 + 工具姿態 + 目標點 + 完成事件〕——而這些訊號**恰好就是訓練 Vision-Language-Action (VLA) 模型所需的監督標籤**。

換句話說:**引導系統本身就是一條自動標註管線。** 影片只是其中一個 channel,真正值錢的是隨引導自動產生的結構化標籤(語言指令、步驟切段、姿態、成功/失敗、以及——關鍵的——力/接觸)。

---

## 願景(Vision)

做一個 **embodiment-agnostic(與機器人形態無關)的通用人類示範資料平台**:任何工廠只要用編輯器「**做好引導規劃**」,就能把自己獨特的工序流程,轉成標準格式、自動標註的訓練資料——用於訓練自家機器人,或作為資料商品授權/販售。

差異化護城河(對比 Open X-Embodiment、Ego-Exo4D 等公開資料集):
1. **力 / 接觸 channel** — 公開資料集多半沒有;對 contact-rich 的插接任務是決定成敗的關鍵。
2. **工業真實工件** — 金屬件、連接器、線束;被點名為「研究 vs 落地」的分水嶺。
3. **自動語言 / 步驟標註** — 引導腳本即標註 schema,省掉最貴的人工標註。

> 詳細的可行性研究與市場分析見 [`docs/`](docs/)。

---

## 這個 repo 現在有什麼

這是 **規劃 + 資料規格(data spec)階段** 的起點,先把「資料長什麼樣、怎麼自動標、怎麼匯出成 VLA 可訓練格式」釘死。MR/Unity 端與即時感知端(XMem / FoundationPose)在後續階段接入。

```
guidie-and-collect/
├── docs/                 # 研究、架構、資料規格、roadmap
├── schema/               # 資料與引導腳本的 JSON Schema + 範例
├── src/guidie_collect/   # Python 參考實作(schema、引導解析、驗證、LeRobot 匯出)
└── tests/                # 單元測試
```

## 快速開始

```bash
pip install -e .
pytest -q                                   # 跑測試

# 自動標註:raw capture + guidance plan -> 已標註的 master episode
python -m guidie_collect.autolabel \
    schema/examples/plug_insertion.plan.json \
    schema/examples/plug_insertion.capture.json -o ep_0002.episode.json

# 驗證 master(含力覺不變式 + 同意鏈)
python -m guidie_collect.validate \
    schema/examples/plug_insertion.episode.json \
    --plan schema/examples/plug_insertion.plan.json

# 匯出 LeRobot metadata(info.json / tasks / episodes / segments)
python -m guidie_collect.export_lerobot \
    schema/examples/plug_insertion.plan.json \
    schema/examples/plug_insertion.episode.json -o ./lerobot_ds

# 資料集 QA(力覺覆蓋率、成功率、驗證狀態)
python -m guidie_collect.report \
    schema/examples/plug_insertion.plan.json \
    schema/examples/plug_insertion.episode.json
```

完整流程:`raw capture → autolabel → master(驗證)→ LeRobot 匯出` / `QA 報告`。

## 狀態

🚧 早期 / 規劃與資料規格階段。歡迎對 `docs/05_DATA_SPEC.md` 的 schema 提意見——它是整個專案的地基。

## 授權

待定(TBD)。資料來源 / 同意 / 授權鏈是本專案的存亡關鍵,見 `docs/06_ROADMAP.md` 的治理章節。
