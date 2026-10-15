# 兒童禁傳圖片測資（Wikimedia）

每類至少 20 張，來源為 Wikimedia Commons 可公開取得的檔案，**不是**色情網站、血腥論壇、真實偷拍或在世者的台灣身分證。

| 資料夾 | 對應 UI | 內容性質 |
| --- | --- | --- |
| `01-body` | 高度私密的身體影像 | 美術裸像／素描（成人藝術） |
| `02-violence` | 暴力或血腥內容 | 戰爭／戰鬥畫作 |
| `03-voyeur` | 偷拍或侵犯隱私 | 針孔／監視器／貓眼等裝置（非真實偷拍影像） |
| `04-document` | 證件與金融資料 | 信用卡、護照樣張、駕照 |
| `05-other` | 其他不適合兒童 | 菸酒、賭場廣告 |

評估：`python scripts/eval_image_corpus.py` → `EVAL.md`、`eval.csv`。
收集：`python scripts/collect_image_corpus.py`。
