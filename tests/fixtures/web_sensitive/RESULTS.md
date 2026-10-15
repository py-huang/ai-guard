# 網路公開圖分類測試結果

來源以 Wikimedia Commons 為主。不下載真實國民身分證、色情、血腥或偷拍原圖。
第 1、2、3、5 類用同一張向日葵公開圖加上中文關鍵字，只驗證 OCR 攔截路徑。

| id | 預期類別 | 是否攔截 | 系統原因 | 實體 | 與預期相符 | OCR 摘要 |
| --- | --- | --- | --- | --- | --- | --- |
| card_cvc2_visa | document | False | — | PERSON | 否 | AUTHORIZEOSIGNATURE.KOTVAUOUNLESSIGNEO Jme 1234 Uapxosacedhutyecttotrtrmandcooesrcerstkhwnoyrd Tnacedrerarathepropsrtycaisiuxr,esdrntdrreoumkduponreqnt. |
| card_cvc2_visa_new | document | False | — | URL | 否 | AUTHORIZEOISICNATURE HOTVALIOUHLRJIGNEO 123 Uaxosyacedhutectltotrtxrmandcodoeesrcerstkhnoyrd Tnacedrerarathcprcpsrtyeraisiuxr.esdrntdrreourkduponreqsnt. |
| card_sogexia_mastercard | document | True | document | CREDIT_CARD, IMAGE_DOCUMENT, PERSON, TW_ID | 是 | SOGEXIA Sogvia Blub 5591 4134 5678 9123 5591 VALIO THRU/EXPIRE FIN 00/00 JEAN DUPONT mastercard. |
| card_visa_logo | document | False | — | — | 否 | TESCO Bank Credit card. 518b 5212 345b 7891 WAUOFSON VALIDENO 07/20 07/24 MR JACK COHEN |
| card_visa_climat | document | None | HTTP Error 429: Too many requests (f061ab2) | — | 否 | — |
| cards_credit_debit_pile | document | None | HTTP Error 404: Not Found | — | 否 | — |
| tw_passports_2021 | document | True | document | IMAGE_DOCUMENT, TW_ID | 是 | 中华民国 中华民园 中华民 外文護照 公榜護照 汉照 TAIWAN TAIWAN TAIWAN DOPLOMATICPASSPORT OFFICLALPASSPORT PASSPORT |
| id_chiang_1965_historical | document | False | — | FACE, PERSON | 否 | 民中 陽士林口第。〇0一 浙江年化 前二年十月百 游中正 蒋宋美费 蒋 中民五四年四月十日 豪灣省瑞明山管理局级 王氏 次男 日本士官學校 Y10000001 注意事项 型 山 |
| control_sunflower | 不應攔（對照） | None | HTTP Error 404: Not Found | — | 否 | — |
| overlay_body_keyword | body | True | body | FACE, IMAGE_BODY | 是 | 裸照 |
| overlay_violence_keyword | violence | True | violence | FACE, IMAGE_VIOLENCE | 是 | 超血腥屁體特寫 |
| overlay_voyeur_keyword | voyeur | True | voyeur | FACE, IMAGE_VOYEUR | 是 | 偷拍 |
| overlay_other_keyword | other | True | other | FACE, IMAGE_OTHER | 是 | 色情 |
