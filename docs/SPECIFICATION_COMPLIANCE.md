# PMDA XML仕様準拠性分析と実装計画

## ドキュメント情報

- **作成日**: 2025年12月5日
- **参照仕様**: 医療用医薬品添付文書情報の電子ファイル作成の手引き（暫定版第1版）
- **発行元**: 日本製薬工業協会（JPMA）
- **発行日**: 2019年5月

---

## 1. 公式仕様の概要

### 1.1 仕様の背景

- **目的**: SGML形式からXML形式への移行（2019年4月～）
- **対象**: 医療用医薬品の添付文書情報
- **名前空間**: `http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0`
- **ドキュメント特性**: ドキュメント中心型XML（階層構造、混合コンテンツ、再帰的セクション）

### 1.2 対象医薬品分類

1. 医薬品（一般的な医療用医薬品）
2. ワクチン・トキソイド
3. 抗毒素・検査用生物学的製剤
4. 血液製剤

### 1.3 主要セクション（仕様書ページ25-29参照）

#### 必須項目（○印）

| セクション | 要素名 | 照合元 | 説明 |
|----------|--------|-------|------|
| 製品名 | ApprovalBrandName | - | 承認された製品名 |
| 一般名 | GenericName | - | 有効成分の一般名 |
| 組成・性状 | Composition | - | 成分・添加物・剤形 |
| 効能又は効果 | IndicationsOrEfficacy | T | 適応症 |
| 用法及び用量 | InfoDoseAdmin | T | 投与方法と用量 |
| 製造販売業者 | NameAddressManufact | - | 製造販売会社情報 |

#### 任意項目（状況に応じて記載）

| セクション | 要素名 | 照合元 | 説明 |
|----------|--------|-------|------|
| 警告 | Warnings | S | 重大な警告情報 |
| 禁忌 | ContraIndications | S | 使用禁忌 |
| 重要な基本的注意 | ImportantPrecautions | S | 基本的な注意事項 |
| 副作用 | AdverseEvents | S | 副作用情報 |
| 相互作用 | Interactions | S | 薬物相互作用 |
| 妊婦・授乳婦 | PrecautionsForPregnancyLactation | S | 妊娠・授乳中の注意 |
| 小児 | PediatricUse | S | 小児への投与 |
| 高齢者 | PrecautionsForElderlyUse | S | 高齢者への投与 |
| 薬物動態 | Pharmacokinetics | - | 吸収・分布・代謝・排泄 |
| 保管方法 | Storage / StorageMethod | T | 保管条件 |

**照合元データ区分**:
- **S**: 使用上の注意に関する照合元データ
- **T**: 取扱い上の注意に関する照合元データ

---

## 2. 現在の実装状況

### 2.1 パーサー実装

#### ファイル: `src/parse_xml_data_lxml.py`

**長所**:
- ✅ lxmlを使用（仕様のドキュメント中心型XMLに適合）
- ✅ 名前空間を正しく定義・使用
- ✅ XPathによる要素抽出（仕様推奨）
- ✅ 混合コンテンツ対応（`itertext()`, `extract_all_text()`）
- ✅ 階層構造保持（`extract_structured_text()`）
- ✅ テーブル処理（Markdown変換）
- ✅ 配合薬対応（複数`Detail/Lang`要素の結合）

**現在の抽出フィールド**:
```python
medicine_data = {
    "product_name": ApprovalBrandName,
    "generic_name": GenericName (配合薬対応),
    "manufacturer": NameAddressManufact,
    "revision_date": PreparationOrRevision[@id="今回"],
    "jsc_code": SccjNo,
    "indications": IndicationsOrEfficacy,
    "dosage": InfoDoseAdmin,
    "contraindications": ContraIndications,
    "side_effects": AdverseEvents,
    "warnings": Warnings,
    "important_precautions": ImportantPrecautions,
    "efficacy_precautions": EfficacyRelatedPrecautions,
    "pregnancy_precautions": PrecautionsForPregnancyLactation,
    "pediatric_precautions": PediatricUse,
    "elderly_precautions": PrecautionsForElderlyUse,
    "other_precautions": OtherPrecautions,
    "pharmacokinetics": Pharmacokinetics,
    "storage": Storage | StorageMethod,
    "source_file": ファイル名,
}
```

### 2.2 データベーススキーマ

#### レガシースキーマ (`pmda.sqlite`)

**テーブル**:
1. `medicines` - 医薬品情報（フラット構造、21列）
2. `interactions` - 薬物相互作用

**課題**:
- 製品バリエーション（10mg錠、50mg錠など）が別レコードとして重複
- 規格情報（剤形、含量）が文字列に埋め込まれ、構造化検索が困難

#### 改善スキーマ (`pmda_v2.sqlite`)

**テーブル**:
1. `medicines` - 医薬品情報（成分単位）
2. `specifications` - 規格情報（剤形・含量単位）
3. `interactions` - 薬物相互作用

**改善点**:
- ✅ 規格分離による情報重複削減
- ✅ 剤形・含量による構造化検索
- ✅ 1つの有効成分に複数の規格を関連付け

---

## 3. 仕様準拠性評価

### 3.1 準拠している点

| 項目 | 実装状況 | 詳細 |
|-----|---------|------|
| **名前空間** | ✅ 完全準拠 | `NAMESPACES = {'p': '...'}`で正しく定義 |
| **XPath使用** | ✅ 完全準拠 | 仕様推奨のXPath方式を採用 |
| **ドキュメント中心** | ✅ 完全準拠 | lxml + 階層構造保持 |
| **必須項目** | ✅ 完全準拠 | 製品名、一般名、組成、効能、用法、製造業者を抽出 |
| **任意項目** | ✅ ほぼ完全 | 警告、禁忌、副作用、相互作用など主要項目を抽出 |
| **配合薬対応** | ✅ 完全準拠 | 複数`Detail/Lang`要素を結合処理 |
| **テーブル処理** | ✅ 準拠 | Markdown形式に変換して保存 |

### 3.2 不足している点

#### 3.2.1 抽出されていないフィールド（仕様書ページ25-29参照）

| 仕様上の要素 | 説明 | 重要度 | 実装状況 |
|------------|------|-------|---------|
| **Composition** | 組成・性状（成分、添加物、剤形） | 高 | ❌ 未実装 |
| **Precautions** | 使用上の注意（包括セクション） | 中 | △ 部分実装 |
| **ClinicalStudies** | 臨床成績 | 中 | ❌ 未実装 |
| **NonClinicalStudies** | 薬効薬理 | 低 | ❌ 未実装 |
| **PharmaceuticalRegu** | 規制区分 | 中 | ❌ 未実装 |
| **PackageInfo** | 包装情報 | 低 | ❌ 未実装 |
| **Literature** | 文献情報 | 低 | ❌ 未実装 |
| **Remarks** | 備考 | 低 | ❌ 未実装 |
| **Overdosage** | 過量投与 | 中 | ❌ 未実装 |
| **ReconstitutionOrDilutionMethod** | 調製方法 | 低 | ❌ 未実装 |

#### 3.2.2 メタデータの不足

| 項目 | 説明 | 実装状況 |
|-----|------|---------|
| **承認番号** | 医薬品の承認番号 | ❌ 未実装 |
| **販売開始年月** | 販売開始日 | ❌ 未実装 |
| **効能追加年月** | 効能追加の日付 | ❌ 未実装 |
| **再審査終了日** | 再審査期間終了日 | ❌ 未実装 |
| **照合元データ区分** | S/T区分 | ❌ 未実装 |

#### 3.2.3 XML構造情報の損失

| 項目 | 説明 | 実装状況 |
|-----|------|---------|
| **参照関係** | セクション間の相互参照 | ❌ 未実装 |
| **引用文献ID** | 文献への参照 | ❌ 未実装 |
| **注釈** | 補足注釈 | ❌ 未実装 |
| **見出し構造** | 階層的な見出し | △ 部分的に保持 |

---

## 4. 改善計画

### 4.1 フェーズ1: 重要フィールドの追加（優先度: 高）

#### 4.1.1 組成・性状（Composition）の抽出

**理由**:
- 仕様上の必須項目
- 成分量、添加物、剤形の詳細情報を含む
- 医薬品の物理的特性の理解に不可欠

**実装方針**:
```python
# 組成・性状セクション全体を抽出
composition_elem = root.xpath('.//p:Composition', namespaces=NAMESPACES)
if composition_elem:
    medicine_data["composition"] = extract_structured_text(composition_elem[0])
```

**データベーススキーマ変更**:
```sql
ALTER TABLE medicines ADD COLUMN composition TEXT;
```

#### 4.1.2 規制区分（PharmaceuticalRegu）の抽出

**理由**:
- 処方箋医薬品、要指示医薬品などの区分
- 取扱い上の重要情報

**実装方針**:
```python
# 規制区分
regu_elem = root.xpath('.//p:PharmaceuticalRegu', namespaces=NAMESPACES)
if regu_elem:
    medicine_data["regulatory_class"] = extract_all_text(regu_elem[0])
```

**データベーススキーマ変更**:
```sql
ALTER TABLE medicines ADD COLUMN regulatory_class TEXT;
```

#### 4.1.3 過量投与（Overdosage）の抽出

**理由**:
- 医療安全上の重要情報
- 緊急時対応に必要

**実装方針**:
```python
# 過量投与
overdosage_elem = root.xpath('.//p:Overdosage', namespaces=NAMESPACES)
if overdosage_elem:
    medicine_data["overdosage"] = extract_structured_text(overdosage_elem[0])
```

**データベーススキーマ変更**:
```sql
ALTER TABLE medicines ADD COLUMN overdosage TEXT;
```

### 4.2 フェーズ2: メタデータの強化（優先度: 中）

#### 4.2.1 承認情報の抽出

**実装方針**:
```python
# 承認番号
approval_num = root.xpath('.//p:ApprovalNo/text()', namespaces=NAMESPACES)
if approval_num:
    medicine_data["approval_number"] = approval_num[0].strip()

# 販売開始年月
marketing_start = root.xpath('.//p:StartOfMarketing/p:YearMonth/text()',
                             namespaces=NAMESPACES)
if marketing_start:
    medicine_data["marketing_start_date"] = marketing_start[0]

# 効能追加年月
efficacy_addition = root.xpath('.//p:EfficacyAddition/p:YearMonth/text()',
                               namespaces=NAMESPACES)
if efficacy_addition:
    medicine_data["efficacy_addition_date"] = efficacy_addition[0]
```

**データベーススキーマ変更**:
```sql
ALTER TABLE medicines ADD COLUMN approval_number TEXT;
ALTER TABLE medicines ADD COLUMN marketing_start_date TEXT;
ALTER TABLE medicines ADD COLUMN efficacy_addition_date TEXT;
```

#### 4.2.2 照合元データ区分の記録

**理由**:
- 仕様上、各セクションにはS（使用上の注意）/T（取扱い上の注意）の区分がある
- データの性質を理解するのに有用

**実装方針**:
- 新しいテーブル `section_metadata` を作成
- セクションごとに照合元区分を記録

```sql
CREATE TABLE section_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_id INTEGER,
    section_name TEXT,
    reference_category TEXT,  -- 'S' or 'T'
    FOREIGN KEY (medicine_id) REFERENCES medicines(id)
);
```

### 4.3 フェーズ3: 追加情報の抽出（優先度: 低）

#### 4.3.1 臨床成績・薬効薬理

**実装方針**:
```python
# 臨床成績
clinical_elem = root.xpath('.//p:ClinicalStudies', namespaces=NAMESPACES)
if clinical_elem:
    medicine_data["clinical_studies"] = extract_structured_text(clinical_elem[0])

# 薬効薬理
nonclinical_elem = root.xpath('.//p:NonClinicalStudies', namespaces=NAMESPACES)
if nonclinical_elem:
    medicine_data["nonclinical_studies"] = extract_structured_text(nonclinical_elem[0])
```

#### 4.3.2 包装情報

**実装方針**:
```python
# 包装情報
package_elem = root.xpath('.//p:PackageInfo', namespaces=NAMESPACES)
if package_elem:
    medicine_data["package_info"] = extract_structured_text(package_elem[0])
```

### 4.4 フェーズ4: 構造情報の保持（優先度: 低～中）

#### 4.4.1 参照関係の記録

**理由**:
- セクション間の相互参照を保持
- XMLの構造的完全性を維持

**実装方針**:
- 新しいテーブル `section_references` を作成
- 参照元と参照先を記録

```sql
CREATE TABLE section_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_id INTEGER,
    source_section TEXT,
    target_section TEXT,
    reference_type TEXT,  -- 'see_also', 'refer_to', etc.
    FOREIGN KEY (medicine_id) REFERENCES medicines(id)
);
```

#### 4.4.2 引用文献の記録

**実装方針**:
```python
# 文献情報
literature_elems = root.xpath('.//p:Literature', namespaces=NAMESPACES)
for lit in literature_elems:
    citation_id = lit.get('id')
    citation_text = extract_all_text(lit)
    # citations_dataに追加
```

**新規テーブル**:
```sql
CREATE TABLE citations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_id INTEGER,
    citation_id TEXT,  -- XML内のID
    citation_text TEXT,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id)
);
```

---

## 5. データベーススキーマ改善提案

### 5.1 完全版スキーマ設計

#### 5.1.1 medicines テーブル（拡張版）

```sql
CREATE TABLE medicines (
    -- 既存のフィールド（21列）
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT,
    generic_name TEXT,
    manufacturer TEXT,
    revision_date TEXT,
    jsc_code TEXT,
    indications TEXT,
    dosage TEXT,
    contraindications TEXT,
    side_effects TEXT,
    warnings TEXT,
    important_precautions TEXT,
    efficacy_precautions TEXT,
    pregnancy_precautions TEXT,
    pediatric_precautions TEXT,
    elderly_precautions TEXT,
    other_precautions TEXT,
    pharmacokinetics TEXT,
    storage TEXT,
    source_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- フェーズ1追加（3列）
    composition TEXT,              -- 組成・性状
    regulatory_class TEXT,         -- 規制区分
    overdosage TEXT,               -- 過量投与

    -- フェーズ2追加（3列）
    approval_number TEXT,          -- 承認番号
    marketing_start_date TEXT,     -- 販売開始年月
    efficacy_addition_date TEXT,   -- 効能追加年月

    -- フェーズ3追加（3列）
    clinical_studies TEXT,         -- 臨床成績
    nonclinical_studies TEXT,      -- 薬効薬理
    package_info TEXT              -- 包装情報
);
```

**合計**: 30列（現在21列 + 追加9列）

#### 5.1.2 新規テーブル

**section_metadata テーブル**:
```sql
CREATE TABLE section_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_id INTEGER,
    section_name TEXT,
    reference_category TEXT,  -- 'S', 'T', or NULL
    FOREIGN KEY (medicine_id) REFERENCES medicines(id)
);
```

**citations テーブル**:
```sql
CREATE TABLE citations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_id INTEGER,
    citation_id TEXT,
    citation_text TEXT,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id)
);
```

**section_references テーブル**:
```sql
CREATE TABLE section_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_id INTEGER,
    source_section TEXT,
    target_section TEXT,
    reference_type TEXT,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id)
);
```

### 5.2 スキーマバージョン管理

**schema_version テーブル**:
```sql
CREATE TABLE schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version VALUES
('1.0', '2025-11-22', 'Initial schema: 21 fields'),
('1.1', '2025-12-05', 'Added composition, regulatory_class, overdosage'),
('1.2', '2025-12-05', 'Added approval metadata'),
('1.3', '2025-12-05', 'Added clinical studies and package info'),
('2.0', '2025-12-05', 'Added metadata tables');
```

---

## 6. 実装ロードマップ

### 6.1 短期（1-2週間）

**目標**: フェーズ1の実装（重要フィールド追加）

**タスク**:
1. ✅ `parse_xml_data_lxml.py`に組成・性状抽出コードを追加
2. ✅ 規制区分、過量投与の抽出コードを追加
3. ✅ データベースマイグレーションスクリプト作成
4. ✅ 既存データベースへのカラム追加
5. ✅ 新フィールドを含むデータ再ロード
6. ✅ テストケース作成（サンプルXMLで検証）

**成果物**:
- `src/parse_xml_data_lxml.py` (v1.1)
- `migrations/add_phase1_fields.sql`
- `tests/test_phase1_extraction.py`

### 6.2 中期（2-4週間）

**目標**: フェーズ2の実装（メタデータ強化）

**タスク**:
1. ✅ 承認情報抽出コードの追加
2. ✅ 照合元データ区分の記録
3. ✅ `section_metadata` テーブルの作成と投入
4. ✅ サンプルクエリとドキュメント作成

**成果物**:
- `src/parse_xml_data_lxml.py` (v1.2)
- `migrations/add_metadata_tables.sql`
- `examples/metadata_queries.py`

### 6.3 長期（4-8週間）

**目標**: フェーズ3-4の実装（追加情報と構造情報）

**タスク**:
1. ✅ 臨床成績・薬効薬理の抽出
2. ✅ 引用文献テーブルの実装
3. ✅ 参照関係テーブルの実装
4. ✅ 完全版ドキュメント作成

**成果物**:
- `src/parse_xml_data_lxml.py` (v2.0)
- `docs/COMPLETE_SCHEMA.md`
- `examples/advanced_queries.py`

---

## 7. テスト戦略

### 7.1 サンプルファイル選定

**テスト用XMLファイル**:
1. **単独成分**: インフルエンザワクチン
2. **配合薬**: ミカムロ配合錠（複数成分）
3. **複雑な構造**: 表、リスト、注釈を含む添付文書
4. **血液製剤**: 特殊な記載項目を含む

### 7.2 検証項目

| 項目 | 検証方法 |
|-----|---------|
| **フィールド抽出** | 全フィールドがNULLでないことを確認 |
| **配合薬対応** | 複数成分が正しく結合されているか |
| **テーブル処理** | Markdown形式が正しく生成されているか |
| **メタデータ** | 承認番号、照合元区分が正しく記録されているか |
| **参照関係** | 相互参照が正しくリンクされているか |

### 7.3 統計検証

**データ完全性チェック**:
```sql
-- フィールドごとのNULL率
SELECT
    'composition' AS field,
    COUNT(*) AS total,
    SUM(CASE WHEN composition IS NULL THEN 1 ELSE 0 END) AS null_count,
    ROUND(SUM(CASE WHEN composition IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS null_rate
FROM medicines;
```

**期待値**:
- `composition`: NULL率 < 5%（ほぼ全医薬品に存在）
- `regulatory_class`: NULL率 < 10%
- `clinical_studies`: NULL率 40-60%（全医薬品に存在するわけではない）

---

## 8. ドキュメント更新計画

### 8.1 既存ドキュメントの更新

| ファイル | 更新内容 |
|---------|---------|
| `docs/DATABASE_SCHEMA.md` | 新フィールドの説明を追加 |
| `docs/XML_NAMESPACE.md` | 新要素のXPathパターンを追加 |
| `README.md` | フェーズごとの機能を更新 |

### 8.2 新規ドキュメント

| ファイル | 内容 |
|---------|------|
| `docs/FIELD_MAPPING.md` | XML要素とDBフィールドの対応表 |
| `docs/MIGRATION_GUIDE.md` | v1.0からv2.0へのマイグレーション手順 |
| `docs/QUALITY_METRICS.md` | データ品質指標とNULL率統計 |

---

## 9. 今後の課題

### 9.1 パフォーマンス最適化

**課題**:
- フィールド数増加によるデータロード時間の増加
- 複雑なクエリのパフォーマンス低下

**対策**:
1. バッチ処理の最適化（トランザクションサイズ調整）
2. 適切なインデックス設計
3. FTS5（全文検索）の活用

### 9.2 データ品質管理

**課題**:
- XML構造のバリエーションへの対応
- パース失敗の検出と記録

**対策**:
1. パースエラーログの記録テーブル作成
2. データ品質レポートの自動生成
3. 異常値検出ロジックの追加

### 9.3 仕様変更への対応

**課題**:
- PMDA仕様の将来的な変更
- 新しい医薬品分類への対応

**対策**:
1. スキーマバージョン管理の徹底
2. 柔軟なフィールド拡張設計
3. 仕様変更の定期的な監視

---

## 10. 参考資料

### 10.1 公式仕様書

- **ファイル**: `xml_guidance.pdf`
- **ページ数**: 31ページ
- **重要セクション**:
  - ページ4: 用語定義
  - ページ8-9: XML採用の背景
  - ページ10-24: 各記載項目の詳細
  - ページ25-29: 項目名一覧（フィールドリスト）

### 10.2 PMDA公式サイト

- 添付文書情報: https://www.pmda.go.jp/
- XMLスキーマ: （PDFに詳細記載）

### 10.3 プロジェクト内ドキュメント

- `docs/DATABASE_SCHEMA.md` - 現行スキーマ詳細
- `docs/IMPROVED_SCHEMA.md` - v2スキーマ設計
- `docs/XML_NAMESPACE.md` - 名前空間ガイド
- `CLAUDE.md` - プロジェクト概要

---

## 11. まとめ

### 11.1 現状の評価

**強み**:
- ✅ lxml + XPathによる堅牢なパース実装
- ✅ 主要フィールド（21列）の抽出完了
- ✅ 配合薬、テーブル、階層構造への対応
- ✅ 名前空間の正しい取扱い

**改善の余地**:
- ❌ 仕様上の9つの重要フィールドが未実装
- ❌ メタデータ（承認番号、照合元区分）が不足
- ❌ 構造情報（参照関係、引用文献）の損失

### 11.2 実装優先順位

**最優先（フェーズ1）**:
1. 組成・性状（Composition） - 仕様上の必須項目
2. 規制区分（PharmaceuticalRegu） - 取扱い上重要
3. 過量投与（Overdosage） - 医療安全上重要

**次優先（フェーズ2）**:
4. 承認情報（承認番号、販売開始年月） - メタデータ強化
5. 照合元データ区分（S/T） - データ分類

**将来実装（フェーズ3-4）**:
6. 臨床成績・薬効薬理 - 追加情報
7. 引用文献・参照関係 - 構造情報保持

### 11.3 期待される効果

**データ完全性**:
- フィールド数: 21列 → 30列（42%増）
- 仕様カバー率: 約60% → 約85%

**検索機能**:
- 成分・剤形での詳細検索が可能
- 規制区分での絞り込みが可能
- メタデータを活用した分析が可能

**データ品質**:
- 仕様準拠による標準化
- 構造情報の保持による完全性向上
- エラー検出・品質管理の強化

---

**更新履歴**:
- 2025-12-05: 初版作成（公式仕様書ベース）
