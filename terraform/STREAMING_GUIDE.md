# Bedrock Guardrails ストリーミング処理ガイド

## 📖 概要

このガイドでは、Bedrock Guardrailsをストリーミング処理で使用する際の評価タイミングとブロック時の動作について詳しく説明します。

## 🎯 評価タイミング

Guardrailsは**2つのフェーズ**でコンテンツを評価します：

### 1️⃣ フェーズ1: 入力評価（Input Assessment）

**タイミング**: リクエスト送信時、モデル呼び出し前

**評価内容**:
- ユーザーのプロンプト全体をチェック
- 有害コンテンツの検出
- PII（個人情報）の検出
- 禁止トピックのチェック
- プロンプトインジェクション攻撃の検出

**ブロック時の動作**:
```
ユーザー入力
    ↓
Guardrail評価 ❌ BLOCKED
    ↓
モデルは呼び出されない（トークン消費なし）
    ↓
エラーレスポンス返却
```

### 2️⃣ フェーズ2: 出力評価（Output Assessment）

**タイミング**: ストリーミング中、リアルタイムで各チャンクを評価

**評価内容**:
- 生成されたテキストをチャンクごとにチェック
- 有害コンテンツの検出
- PII漏洩の防止
- ポリシー違反の検出

**ブロック時の動作**:
```
モデルがテキスト生成開始
    ↓
チャンク1 → Guardrail ✅ PASS → ユーザーに送信
    ↓
チャンク2 → Guardrail ✅ PASS → ユーザーに送信
    ↓
チャンク3 → Guardrail ❌ BLOCKED
    ↓
ストリーミング停止
    ↓
これまでの出力を破棄
    ↓
ブロックメッセージに置換
```

## 🔄 完全なフロー図

```
┌─────────────────────────────────────────────────────────────┐
│                    ストリーミング処理の流れ                     │
└─────────────────────────────────────────────────────────────┘

         ┌──────────────┐
         │ ユーザー入力  │
         └──────┬───────┘
                │
                ▼
┌───────────────────────────────────────────────────────────┐
│           【フェーズ1: 入力評価】                            │
│                                                           │
│   ┌─────────────────────────────────┐                    │
│   │   Guardrail 入力チェック          │                    │
│   │                                 │                    │
│   │  ✓ 有害コンテンツ                │                    │
│   │  ✓ PII検出                      │                    │
│   │  ✓ 禁止トピック                  │                    │
│   │  ✓ プロンプトインジェクション      │                    │
│   └─────────┬───────────────────────┘                    │
│             │                                            │
│        ┌────┴────┐                                       │
│        │         │                                       │
│   [PASS]    [BLOCKED]                                    │
│        │         │                                       │
└────────┼─────────┼───────────────────────────────────────┘
         │         │
         │         └──────────────────┐
         │                            │
         ▼                            ▼
    ┌─────────────┐          ┌─────────────────────┐
    │ モデル呼び出し│          │ ❌ エラーレスポンス   │
    └──────┬──────┘          │                     │
           │                 │ ・処理中断           │
           │                 │ ・トークン消費: 0    │
           │                 │ ・ブロック理由を返す  │
           │                 └─────────────────────┘
           │
┌──────────┴────────────────────────────────────────────────┐
│          【フェーズ2: 出力評価】                             │
│                                                           │
│        ┌─────────────────┐                               │
│        │ テキスト生成開始  │                               │
│        └────────┬────────┘                               │
│                 │                                         │
│                 ▼                                         │
│   ╔═════════════════════════╗                            │
│   ║  ストリーミングループ      ║                            │
│   ╚═════════════════════════╝                            │
│                 │                                         │
│       ┌─────────┴─────────┐                              │
│       │                   │                              │
│       ▼                   │                              │
│   ┌────────────┐          │                              │
│   │ チャンク生成 │          │                              │
│   └─────┬──────┘          │                              │
│         │                 │                              │
│         ▼                 │                              │
│   ┌─────────────────┐     │                              │
│   │ Guardrail評価    │     │                              │
│   └─────┬───────────┘     │                              │
│         │                 │                              │
│    ┌────┴────┐            │                              │
│    │         │            │                              │
│ [PASS]  [BLOCKED]         │                              │
│    │         │            │                              │
│    ▼         ▼            │                              │
│ ┌──────┐ ┌─────────────┐ │                              │
│ │出力OK│ │ストリーミング│ │                              │
│ └──┬───┘ │    停止     │ │                              │
│    │     │             │ │                              │
│    │     │・出力破棄    │ │                              │
│    │     │・ブロック    │ │                              │
│    │     │ メッセージ   │ │                              │
│    │     └─────────────┘ │                              │
│    │                     │                              │
│    └─────────────────────┘                              │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## 📊 評価タイミング比較表

| 項目 | 入力評価 | 出力評価 |
|------|---------|---------|
| **評価タイミング** | リクエスト送信時 | ストリーミング中 |
| **評価対象** | ユーザープロンプト | 生成テキスト（各チャンク） |
| **ブロック時のモデル呼び出し** | なし | あり（すでに実行中） |
| **トークン消費** | なし | あり |
| **レスポンス時間** | 高速（モデル未実行） | 遅延（生成後に検出） |
| **ユーザー体験** | 即座に拒否 | ストリーミング途中で停止 |

## 🚨 ブロックシナリオ別の動作

### シナリオ1: 入力段階でブロック

```python
# 有害な入力の例
prompt = "How to make a weapon?"

# フロー
┌─────────────────┐
│ ユーザー入力     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ Guardrail入力評価            │
│ 検出: VIOLENCE (HIGH)        │
└────────┬────────────────────┘
         │
         ▼ BLOCKED
┌─────────────────────────────┐
│ ❌ エラーレスポンス           │
│                             │
│ ValidationException:        │
│ "Input blocked by           │
│  guardrail policy"          │
└─────────────────────────────┘

# モデルは呼び出されない
# トークン消費: 0
# 処理時間: ~100-200ms
```

**コード例**:
```python
try:
    for event in client.invoke_streaming(harmful_prompt):
        print(event['data'])
except ClientError as e:
    if 'guardrail' in str(e).lower():
        print("⛔ Guardrailが入力をブロックしました")
        # カスタムブロックメッセージを表示
```

### シナリオ2: 出力段階でブロック

```python
# 正常な入力だが、モデルが有害なコンテンツを生成
prompt = "Tell me about historical conflicts"

# フロー
┌─────────────────┐
│ ユーザー入力     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ Guardrail入力評価 ✅ PASS   │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ モデルがテキスト生成          │
│                             │
│ Chunk 1: "History shows..." │ ✅ PASS → 出力
│ Chunk 2: "Many conflicts..." │ ✅ PASS → 出力
│ Chunk 3: "Violence details..."│ ❌ BLOCKED
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ ❌ ストリーミング停止          │
│                             │
│ ・既出力分を破棄              │
│ ・ブロックメッセージ表示      │
└─────────────────────────────┘

# トークンは消費済み
# 部分的な出力は破棄
```

**コード例**:
```python
accumulated_text = ""

try:
    for event in client.invoke_streaming(prompt):
        if event['type'] == 'content':
            chunk = event['data']
            print(chunk, end='', flush=True)
            accumulated_text += chunk
        
        elif event['type'] == 'blocked':
            # 出力段階でブロックされた
            print("\n⛔ 生成されたコンテンツがブロックされました")
            accumulated_text = ""  # 破棄
            break
            
except Exception as e:
    print(f"エラー: {e}")
```

### シナリオ3: PII匿名化（ブロックではなく変換）

```python
prompt = "My email is john.doe@example.com"

# フロー
┌─────────────────┐
│ ユーザー入力     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ Guardrail入力評価            │
│ 検出: EMAIL (ANONYMIZE)      │
└────────┬────────────────────┘
         │
         ▼ TRANSFORM
┌─────────────────────────────┐
│ ✅ 処理継続（匿名化）          │
│                             │
│ 変換後:                      │
│ "My email is ***@***.com"   │
└─────────────────────────────┘

# ブロックされない
# モデルには匿名化後のテキストが渡される
```

## 💻 実装例

### 完全な実装コード

`examples/streaming_example.py`を参照してください。このファイルには以下が含まれます：

1. ストリーミングクライアントの実装
2. 入力/出力評価の処理
3. ブロック時のエラーハンドリング
4. トレース情報の取得
5. デモンストレーション

### 実行方法

```bash
# 環境変数の設定
export GUARDRAIL_ID='your-guardrail-id'
export GUARDRAIL_VERSION='1'

# フロー図の表示
python examples/streaming_example.py

# デモの実行
python examples/streaming_example.py --demo
```

## 📈 パフォーマンス考慮事項

### レイテンシへの影響

| フェーズ | 追加レイテンシ | 影響 |
|---------|--------------|------|
| 入力評価 | +50-100ms | リクエスト開始時のみ |
| 出力評価 | +10-50ms/chunk | 各チャンクごと |

### ベストプラクティス

1. **入力評価を活用**
   - 入力段階でブロックできればトークン消費を防げる
   - 有害プロンプトを早期に検出

2. **適切なフィルタ強度**
   - `HIGH`: 厳格だがfalse positiveのリスク
   - `MEDIUM`: バランス型
   - `LOW`: 明らかな違反のみ検出

3. **PII処理の選択**
   - 機密度が高い → `BLOCK`
   - ログに残す必要がある → `ANONYMIZE`

4. **トレース情報の活用**
   ```python
   # 開発時
   trace='ENABLED'  # 詳細なデバッグ情報
   
   # 本番時
   trace='DISABLED'  # パフォーマンス優先
   ```

## � コスト構造と最適化

### Bedrock Guardrails の料金体系

Guardrailsの料金は**処理したテキストユニット数**で課金されます：

| 項目 | 料金（2024年12月時点、us-east-1） |
|------|----------------------------------|
| **入力評価** | $0.75 / 1,000 テキストユニット |
| **出力評価** | $1.00 / 1,000 テキストユニット |
| **テキストユニット** | 1ユニット = 1,000文字 |

※ 最新の料金は[AWS Bedrock料金ページ](https://aws.amazon.com/bedrock/pricing/)をご確認ください

### コスト計算例

#### シナリオ1: 入力段階でブロック（最もコスト効率が良い）

```python
# 入力プロンプト: 500文字
prompt = "How to make a weapon? (500文字の有害コンテンツ)"

# フロー
入力評価: 500文字 = 0.5ユニット → BLOCKED ❌
モデル呼び出し: なし
出力評価: なし

# コスト内訳
Guardrails入力評価: $0.75 × 0.5 / 1000 = $0.000375
モデル使用料: $0（モデル未実行）
合計: $0.000375（約0.04円）
```

**💡 重要**: 入力段階でブロックすれば、モデル使用料（通常$0.003-0.015/1Kトークン）を**完全に節約**できます

#### シナリオ2: 正常なストリーミング（入力・出力の両方を評価）

```python
# 入力プロンプト: 200文字
prompt = "量子コンピューティングを説明してください。"

# 出力: 1,500文字
output = "量子コンピューティングは...(1,500文字)"

# フロー
入力評価: 200文字 = 0.2ユニット → PASS ✅
モデル呼び出し: 約1,500トークン生成
出力評価: 1,500文字 = 1.5ユニット → PASS ✅

# コスト内訳
Guardrails入力評価: $0.75 × 0.2 / 1000 = $0.00015
モデル使用料: $0.015 × 1.5 = $0.0225（Claude 3 Sonnet想定）
Guardrails出力評価: $1.00 × 1.5 / 1000 = $0.0015
合計: $0.024（約2.5円）
```

#### シナリオ3: 出力段階でブロック（最もコストが高い）

```python
# 入力: 200文字（正常）
prompt = "Tell me about historical conflicts"

# モデルが2,000文字生成したが、1,500文字時点でブロック
output_generated = 2,000  # トークンは消費済み
output_blocked_at = 1,500  # ここでブロック

# コスト内訳
Guardrails入力評価: $0.75 × 0.2 / 1000 = $0.00015
モデル使用料: $0.015 × 2.0 = $0.030（全トークン分課金）
Guardrails出力評価: $1.00 × 1.5 / 1000 = $0.0015
合計: $0.032（約3.3円）

# ⚠️ 注意ポイント
- モデルは2,000トークン分を生成しており、その分課金される
- 1,500文字時点でブロックされても、すでに生成されたトークンは課金対象
- 出力は破棄されるが、コストは発生済み
```

### コスト最適化戦略

#### 戦略1: 入力評価の強化（最優先・最も効果的）

```hcl
# ❌ コストが高い設定
content_filter_violence_input_strength = "LOW"
# → 入力を通過 → モデル実行 → 出力でブロック
# → モデル料金($0.015-0.03) + Guardrail料金($0.001) = 高コスト

# ✅ コスト最適化
content_filter_violence_input_strength = "HIGH"
# → 入力でブロック → モデル未実行
# → Guardrail料金($0.0004)のみ = 90-95%削減
```

**節約効果**: 入力ブロックで**モデル料金を完全に節約**（$0.015-0.03/リクエスト）

#### 戦略2: 出力評価の選択的適用

```hcl
# ユースケースに応じて出力評価を調整

# ケース1: ユーザー向けチャットボット（厳格）
content_filter_violence_input_strength = "HIGH"
content_filter_violence_output_strength = "HIGH"
# コスト: 高　セキュリティ: 最高

# ケース2: 社内ツール（入力のみチェック）
content_filter_violence_input_strength = "HIGH"
content_filter_violence_output_strength = "NONE"  # 出力評価を無効化
# コスト: 中　セキュリティ: 中（入力は保護）
```

**節約効果**: 出力評価を無効化すると**約40-50%のGuardrailコスト削減**

#### 戦略3: 不要なポリシーの無効化

```hcl
# すべて有効化（コスト高、処理時間長）
content_filter_sexual_input_strength = "HIGH"
content_filter_violence_input_strength = "HIGH"
content_filter_hate_input_strength = "HIGH"
content_filter_insults_input_strength = "HIGH"
content_filter_misconduct_input_strength = "HIGH"
content_filter_prompt_attack_input_strength = "HIGH"

# ↓ 必要最小限に絞る

# B2Bツールで侮辱表現チェックが不要な場合
content_filter_insults_input_strength = "NONE"

# 内部APIでプロンプトインジェクション対策が不要な場合
content_filter_prompt_attack_input_strength = "NONE"
```

**節約効果**: 処理時間短縮により間接的にコスト削減

#### 戦略4: PII処理の最適化

```hcl
# すべてANONYMIZE（処理コスト高）
pii_action_email = "ANONYMIZE"     # 複雑な文字列置換処理
pii_action_phone = "ANONYMIZE"
pii_action_credit_card = "ANONYMIZE"

# ↓ 最適化

# クリティカルな情報はBLOCK（処理コスト低）
pii_action_credit_card = "BLOCK"    # 単純なブロック処理
pii_action_ssn = "BLOCK"

# 必要な場合のみANONYMIZE
pii_action_email = "ANONYMIZE"
pii_action_name = "NONE"            # 氏名チェック無効化
```

**節約効果**: 
- `BLOCK`は`ANONYMIZE`より処理が軽量
- 不要なPII検出を無効化することで**約20-30%削減**

#### 戦略5: トレース情報の制御

```python
# 開発環境
trace='ENABLED'   # デバッグに必要

# 本番環境
trace='DISABLED'  # トレース転送コストを削減
```

**節約効果**: 約**5-10%のデータ転送コスト削減**

### 月額コスト試算例

#### 小規模アプリケーション（月間10,000リクエスト）

```
想定条件:
- 月間リクエスト: 10,000件
- 平均入力: 300文字（0.3ユニット）
- 平均出力: 1,000文字（1.0ユニット）
- 入力ブロック率: 5%（500件）

コスト計算:
【正常処理 9,500件】
  Guardrails入力評価: $0.75 × 0.3 × 9,500 / 1000 = $2.14
  Guardrails出力評価: $1.00 × 1.0 × 9,500 / 1000 = $9.50
  モデル料金: $0.015 × 1.0 × 9,500 = $142.50

【入力ブロック 500件】
  Guardrails入力評価: $0.75 × 0.3 × 500 / 1000 = $0.11
  モデル料金: $0（未実行で節約）

月額合計:
  Guardrails料金: $11.75
  Bedrock モデル料金: $142.50
  総計: $154.25（約16,000円）
  
💰 入力ブロックによる節約額: $7.50（約800円）
```

#### 中規模アプリケーション（月間100,000リクエスト）

```
想定条件:
- 月間リクエスト: 100,000件
- 平均入力: 500文字（0.5ユニット）
- 平均出力: 1,500文字（1.5ユニット）
- 入力ブロック率: 10%（10,000件）

コスト計算:
【正常処理 90,000件】
  Guardrails入力評価: $0.75 × 0.5 × 90,000 / 1000 = $33.75
  Guardrails出力評価: $1.00 × 1.5 × 90,000 / 1000 = $135.00
  モデル料金: $0.015 × 1.5 × 90,000 = $2,025.00

【入力ブロック 10,000件】
  Guardrails入力評価: $0.75 × 0.5 × 10,000 / 1000 = $3.75
  モデル料金: $0（未実行で節約）

月額合計:
  Guardrails料金: $172.50（約18,000円）
  Bedrock モデル料金: $2,025.00（約210,000円）
  総計: $2,197.50（約228,000円）
  
💰 入力ブロックによる節約額: $225.00（約23,000円）
   入力ブロックがなければ: $2,422.50（+10%コスト増）
```

### コスト vs セキュリティのバランス

```
┌────────────────────────────────────────────────────────────┐
│              コスト-セキュリティマトリクス                    │
└────────────────────────────────────────────────────────────┘

高セキュリティ
    ▲
    │  ┌─────────────────────────────┐
    │  │ 🔴 設定4: 最高セキュリティ    │
    │  │  入力: HIGH                 │  月額コスト: $200-300
    │  │  出力: HIGH                 │  セキュリティ: ⭐⭐⭐⭐⭐
    │  │  全PII: ANONYMIZE           │  ユースケース:
    │  │  全ポリシー有効              │  - 公開API
    │  └─────────────────────────────┘  - 金融サービス
    │                                   - 医療系アプリ
    │
    │         ┌─────────────────────────────┐
    │         │ 🟢 設定3: 推奨バランス型     │
    │         │  入力: HIGH                │  月額コスト: $150-200
    │         │  出力: MEDIUM              │  セキュリティ: ⭐⭐⭐⭐
    │         │  重要PII: BLOCK            │  ユースケース:
    │         │  選択的ポリシー             │  - 一般的なチャットボット
    │         └─────────────────────────────┘  - カスタマーサポート
    │
    │                  ┌─────────────────────────────┐
    │                  │ 🟡 設定2: コスト重視        │
    │                  │  入力: MEDIUM              │  月額コスト: $100-150
    │                  │  出力: LOW/NONE            │  セキュリティ: ⭐⭐⭐
    │                  │  PII: 選択的               │  ユースケース:
    │                  │  最小限のポリシー           │  - 社内ツール
    │                  └─────────────────────────────┘  - ドキュメント生成
    │
    │                           ┌─────────────────────────────┐
    │                           │ 🔵 設定1: 開発/テスト用      │
    │                           │  入力: LOW                 │  月額コスト: $50-100
    │                           │  出力: NONE                │  セキュリティ: ⭐⭐
    │                           │  PII: 最小限               │  ユースケース:
    │                           │  最小限のポリシー           │  - 開発環境
    │                           └─────────────────────────────┘  - プロトタイプ
低セキュリティ
    └───────────────────────────────────────────────────────► 
                低コスト                              高コスト
```

### 推奨設定: コスト効率の良いバランス型

```hcl
# 🟢 推奨設定（コストとセキュリティのバランス）

# === 入力評価: 厳格にチェック（モデル料金を節約） ===
content_filter_sexual_input_strength = "HIGH"
content_filter_violence_input_strength = "HIGH"
content_filter_hate_input_strength = "HIGH"
content_filter_misconduct_input_strength = "HIGH"
content_filter_prompt_attack_input_strength = "HIGH"

# 侮辱表現は中程度（ビジネス用途では必要に応じて）
content_filter_insults_input_strength = "MEDIUM"

# === 出力評価: 入力より緩和（コスト削減） ===
# モデルが生成する内容は入力よりも安全な傾向
content_filter_sexual_output_strength = "MEDIUM"
content_filter_violence_output_strength = "MEDIUM"
content_filter_hate_output_strength = "MEDIUM"
content_filter_insults_output_strength = "LOW"
content_filter_misconduct_output_strength = "MEDIUM"

# プロンプトインジェクションは出力では不要
content_filter_prompt_attack_output_strength = "NONE"

# === PII処理: クリティカルはBLOCK、その他はANONYMIZE ===
pii_action_credit_card = "BLOCK"  # 軽量処理
pii_action_ssn = "BLOCK"          # 軽量処理

pii_action_email = "ANONYMIZE"    # 必要に応じて
pii_action_phone = "ANONYMIZE"
pii_action_name = "NONE"          # 無効化してコスト削減
pii_action_address = "NONE"       # 無効化してコスト削減
```

**この設定による効果**:
- ✅ セキュリティを確保しつつ、コストを**約30-40%削減**
- ✅ 入力段階での厳格なチェックでモデル料金を節約
- ✅ 出力評価を最適化してGuardrail料金を削減
- ✅ 月間100,000リクエストで約**$60-80（6,000-8,000円）の節約**

### コスト監視の実装

```python
import boto3
from datetime import datetime, timedelta

def calculate_guardrail_costs(guardrail_id: str, days: int = 30):
    """過去N日間のGuardrailコストを推定"""
    cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    # リクエスト数を取得
    response = cloudwatch.get_metric_statistics(
        Namespace='AWS/Bedrock',
        MetricName='Invocations',
        Dimensions=[
            {'Name': 'GuardrailId', 'Value': guardrail_id}
        ],
        StartTime=start_time,
        EndTime=end_time,
        Period=86400,  # 1日ごと
        Statistics=['Sum']
    )
    
    total_requests = sum(d['Sum'] for d in response['Datapoints'])
    
    # 推定コスト計算
    # 仮定: 平均500文字入力、1500文字出力
    avg_input_units = 0.5
    avg_output_units = 1.5
    
    input_cost = total_requests * avg_input_units * 0.75 / 1000
    output_cost = total_requests * avg_output_units * 1.00 / 1000
    total_cost = input_cost + output_cost
    
    print(f"\n📊 過去{days}日間のGuardrailコスト推定")
    print("=" * 60)
    print(f"総リクエスト数: {total_requests:,.0f}")
    print(f"入力評価コスト: ${input_cost:.2f} ({input_cost * 104:.0f}円)")
    print(f"出力評価コスト: ${output_cost:.2f} ({output_cost * 104:.0f}円)")
    print(f"合計: ${total_cost:.2f} ({total_cost * 104:.0f}円)")
    print(f"月額換算: ${total_cost * 30 / days:.2f} ({total_cost * 30 / days * 104:.0f}円)")
    print("=" * 60)
    
    return total_cost

# 使用例
import os
guardrail_id = os.getenv('GUARDRAIL_ID')
if guardrail_id:
    calculate_guardrail_costs(guardrail_id, days=7)
```

### コスト最適化チェックリスト

#### ✅ 実装前のチェック

- [ ] 入力評価を`HIGH`に設定（最重要）
- [ ] 不要なコンテンツフィルタを無効化
- [ ] 出力評価は入力より緩和
- [ ] PIIは`BLOCK`を優先（`ANONYMIZE`は必要な場合のみ）
- [ ] 本番環境では`trace='DISABLED'`

#### ✅ 運用中のチェック

- [ ] CloudWatch Metricsでブロック率を監視
- [ ] 月次でコストレポートを確認
- [ ] False positiveが多い場合は設定を調整
- [ ] ブロック率が10%超える場合は入力検証を強化
- [ ] コストアラートを設定（予算の120%超過時など）

### よくある質問（コスト編）

**Q1: Guardrailsを使うと、どのくらいコストが増えますか？**

A: モデル料金の**約5-10%の追加コスト**です。ただし、入力段階でブロックすることで、無駄なモデル実行を防ぎ、トータルではコスト削減につながります。

**Q2: 入力評価と出力評価、どちらが重要ですか？**

A: **入力評価が圧倒的に重要**です。入力でブロックすればモデル料金（コストの90-95%）を節約できます。

**Q3: すべてのリクエストでGuardrailsを適用すべきですか？**

A: ユースケース次第です：
- 公開API → 必須
- 社内ツール → 入力のみでも可
- 開発環境 → 最小限でも可

**Q4: コストを最小限にしたいです。最低限の設定は？**

A: 以下の設定を推奨：
```hcl
# 最小限の設定（セキュリティは妥協）
content_filter_violence_input_strength = "MEDIUM"
content_filter_hate_input_strength = "MEDIUM"
# その他はNONE

# 出力評価は無効化
content_filter_*_output_strength = "NONE"
```

ただし、**セキュリティリスクが高まる**ため、本番環境では非推奨です。

## �🔍 トラブルシューティング

### Q1: 入力がブロックされたかどうかを判定するには？

```python
from botocore.exceptions import ClientError

try:
    response = client.invoke_streaming(prompt)
except ClientError as e:
    if 'ValidationException' in str(e) and 'guardrail' in str(e).lower():
        print("入力段階でブロックされました")
        # ブロック理由を解析
```

### Q2: 出力のどの部分でブロックされたかを知るには？

```python
chunk_history = []

for event in stream:
    if event['type'] == 'content':
        chunk_history.append(event['data'])
    elif event['type'] == 'blocked':
        print(f"チャンク#{len(chunk_history)}でブロック")
        print(f"直前のテキスト: {chunk_history[-1]}")
```

### Q3: ブロック頻度が高すぎる場合は？

1. Terraformでフィルタ強度を調整
   ```hcl
   content_filter_violence_input_strength = "MEDIUM"  # HIGH → MEDIUM
   ```

2. 特定のカテゴリを無効化
   ```hcl
   content_filter_insults_input_strength = "NONE"
   ```

3. CloudWatch Metricsで分析
   ```python
   # どのポリシーでブロックが多いかを確認
   cloudwatch.get_metric_statistics(
       MetricName='GuardrailInterventionByPolicy'
   )
   ```

## 📚 関連リンク

- [Bedrock Guardrails API リファレンス](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModelWithResponseStream.html)
- [Guardrails トレース仕様](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-trace.html)
- [ストリーミングベストプラクティス](https://docs.aws.amazon.com/bedrock/latest/userguide/streaming-best-practices.html)

## 🎯 次のステップ

1. `terraform/`ディレクトリでGuardrailをデプロイ
2. `examples/streaming_example.py`を実行してフローを確認
3. 独自のユースケースに合わせて設定をカスタマイズ
4. CloudWatchでメトリクスを監視
