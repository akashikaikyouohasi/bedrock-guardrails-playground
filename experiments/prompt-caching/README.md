# Prompt Caching 実験

このディレクトリには、AWS Bedrock Prompt Caching の効果を確認するための実験スクリプトが含まれています。

## 📋 前提条件

### 1. 環境変数の設定

```bash
# .env ファイルに以下が設定されている必要があります:
CLAUDE_CODE_USE_BEDROCK=1
AWS_REGION=us-west-2  # 東京リージョンの場合は ap-northeast-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

### 2. Bedrock ログの有効化（メトリクス確認に必要）

CloudWatch メトリクスの代わりに、より正確でリアルタイムな Bedrock ログを使用します。

**AWS コンソールで有効化:**
1. Amazon Bedrock コンソール → Settings → Model invocation logging
2. CloudWatch Logs にログを送信するように設定
3. ロググループ名: `bedrock-logs`
4. ログストリーム名: `aws/bedrock/modelinvocations`

**または AWS CLI で有効化:**
```bash
aws bedrock put-model-invocation-logging-configuration \
  --logging-config '{
    "cloudWatchConfig": {
      "logGroupName": "bedrock-logs",
      "roleArn": "arn:aws:iam::YOUR_ACCOUNT:role/BedrockLoggingRole"
    },
    "textDataDeliveryEnabled": true,
    "imageDataDeliveryEnabled": false,
    "embeddingDataDeliveryEnabled": false
  }'
```

**注意:** ログが有効化されるまで数分かかります。

## 🚀 実験スクリプト

### 1. 基本的なキャッシュテスト

```bash
python experiments/prompt-caching/test_basic_caching.py
```

**何をテストするか:**
- 長いシステムプロンプト（約1,200トークン）で3つの質問に回答
- 1回目: キャッシュ書き込み（+25% コスト）
- 2〜3回目: キャッシュ読み取り（-90% コスト、高速化）

**期待される結果:**
- 2回目以降のリクエストが約37-38%高速化
- Bedrock ログでキャッシュヒット（85%以上）を確認可能
- コスト削減率: 約75%

---

### 2. キャッシュあり・なし比較テスト

```bash
python experiments/prompt-caching/test_comparison.py
```

**何をテストするか:**
- 短いシステムプロンプト vs 長いシステムプロンプト
- それぞれ3回実行して実行時間を比較

**期待される結果:**
- 長いプロンプトで2回目以降が高速化
- レイテンシ削減率を確認

---

### 3. Bedrock ログからメトリクス確認

```bash
# デフォルト（過去1時間、Claude Haiku 4.5）
python experiments/prompt-caching/check_cache_metrics.py
# または
make cache-metrics

# 過去6時間のメトリクスを確認
python experiments/prompt-caching/check_cache_metrics.py --hours 6

# 別のモデルを確認（Claude 3.7 Sonnet）
python experiments/prompt-caching/check_cache_metrics.py \
  --model-id anthropic.claude-3-7-sonnet-20250219-v1:0
```

**何を確認するか:**
- 総入力トークン数（新規入力 + キャッシュ書き込み + キャッシュ読み取り）
- キャッシュヒット率
- コスト削減率
- 実質コストと削減額

**実際の出力例:**
```
📊 統計情報
----------------------------------------------------------------------
総入力トークン数: 275,446 トークン
  - 新規入力: 19,905 トークン
  - キャッシュ書き込み: 18,748 トークン
  - キャッシュ読み取り: 236,793 トークン

キャッシュヒット率: 85.97%
コスト削減率: 約 77.4%

💰 コスト内訳（トークン相当）
----------------------------------------------------------------------
新規入力トークン:            19,905 × 1.00 =     19,905
キャッシュ書き込み:          18,748 × 1.25 =     23,435
キャッシュ読み取り:         236,793 × 0.10 =     23,679
----------------------------------------------------------------------
実質コスト:                  67,019 トークン相当
元のコスト:                 275,446 トークン相当
削減額:                     208,427 トークン (75.7%)

🎉 キャッシュが効いています！
```

---

## 📊 実験の流れ

### Step 1: 基本テストを実行

```bash
make cache-test
# または
python experiments/prompt-caching/test_basic_caching.py
```

約3分間実行され、3つの質問に回答します。

### Step 2: 1〜2分待つ

Bedrock ログが CloudWatch Logs に反映されるまで待ちます（ほぼリアルタイム）。

### Step 3: メトリクスを確認

```bash
make cache-metrics
# または
python experiments/prompt-caching/check_cache_metrics.py
```

キャッシュヒット率とコスト削減効果が即座に確認できます。

---

## 🔍 キャッシュが効く条件

| 条件 | 説明 |
|------|------|
| **最小トークン数** | 1,024 トークン以上のシステムプロンプト |
| **プレフィックスの一致** | 静的部分が完全に同一 |
| **TTL** | 5分以内に再リクエスト |

---

## 💡 期待される効果

### 実測値（Claude Agent SDK + Bedrock）

#### レイテンシ削減
```
1回目（キャッシュ書き込み）: 10.70秒
2回目（キャッシュ読み取り）:  6.72秒  ← 約37%高速化
3回目（キャッシュ読み取り）:  6.58秒  ← 約38%高速化
```

#### コスト削減（実測値）
```
総入力トークン数: 275,446 トークン
  - 新規入力:          19,905 トークン (7.2%)
  - キャッシュ書き込み: 18,748 トークン (6.8%)
  - キャッシュ読み取り: 236,793 トークン (85.97%)

【キャッシュなしの場合】
  275,446 トークン × 1.00 = 275,446 コスト相当

【キャッシュありの場合（実質）】
  新規入力:          19,905 × 1.00 =  19,905
  キャッシュ書き込み: 18,748 × 1.25 =  23,435
  キャッシュ読み取り: 236,793 × 0.10 =  23,679
  合計: 67,019 コスト相当

削減率: 75.7% 🎉
```

### 長期的なコスト削減例

```
【キャッシュなし】
  10,000 トークン × 100回 = 1,000,000 トークン

【キャッシュあり】
  初回: 10,000 × 1.25 = 12,500
  2〜100回目: 10,000 × 0.10 × 99 = 99,000
  合計: 111,500 トークン

削減率: 約89%
```

---

## 📈 Bedrock ログでの確認

### メトリクス取得方法

`check_cache_metrics.py` は **Bedrock のログ**（CloudWatch Logs）から直接メトリクスを取得します。

**メリット:**
- ✅ ほぼリアルタイム（数秒〜1分で反映）
- ✅ より詳細な情報
- ✅ CloudWatch メトリクスより確実

### メトリクス一覧

| フィールド | 説明 |
|-------------|------|
| `input.inputTokenCount` | 入力トークン総数 |
| `input.cacheReadInputTokenCount` | キャッシュから読み取られたトークン数 |
| `input.cacheWriteInputTokenCount` | キャッシュに書き込まれたトークン数 |

### CloudWatch Logs Insights クエリ例

AWS コンソールの CloudWatch Logs Insights で直接確認する場合：

```sql
# ロググループ: bedrock-logs
# 期間: 過去1時間

fields @timestamp, input.inputTokenCount, input.cacheReadInputTokenCount, input.cacheWriteInputTokenCount
| filter modelId like /claude-haiku-4-5/
| stats
    sum(input.inputTokenCount) as totalInput,
    sum(input.cacheReadInputTokenCount) as totalCacheRead,
    sum(input.cacheWriteInputTokenCount) as totalCacheWrite,
    count(*) as requestCount
```

**結果の見方:**
- `totalInput`: 新規入力トークン数
- `totalCacheRead`: キャッシュから読み取られたトークン数（**高いほど効果的**）
- `totalCacheWrite`: キャッシュに書き込まれたトークン数（初回リクエスト）
- `requestCount`: リクエスト総数

---

## 🐛 トラブルシューティング

### ロググループが見つからない

**原因:**
- Bedrock のログが有効化されていない

**解決策:**
1. AWS コンソールで Bedrock のログを有効化
2. 数分待ってから再実行
3. 「前提条件」セクションの手順を参照

### メトリクスが表示されない

**原因:**
- ログの反映に数秒〜1分かかる
- リクエストが実行されていない
- モデル ID が一致していない

**解決策:**
```bash
# 1〜2分待ってから再実行
make cache-metrics

# 別のモデル ID を指定（Claude 3.7 Sonnet）
python experiments/prompt-caching/check_cache_metrics.py \
  --model-id anthropic.claude-3-7-sonnet-20250219-v1:0

# 過去2時間のデータを確認
python experiments/prompt-caching/check_cache_metrics.py --hours 2
```

### キャッシュヒット率が0%

**原因:**
- システムプロンプトが1,024トークン未満
- リクエスト間隔が5分以上空いた
- システムプロンプトが変更された

**解決策:**
- システムプロンプトを長くする
- 5分以内に連続してリクエストする
- システムプロンプトを固定する

---

## 📚 関連ドキュメント

- [Prompt Caching 完全ガイド](../../docs/prompt-caching/bedrock-prompt-caching-guide.md)
- [AWS Bedrock Prompt Caching 公式ドキュメント](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)
