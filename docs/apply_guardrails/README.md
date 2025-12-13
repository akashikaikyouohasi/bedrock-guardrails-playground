# ApplyGuardrail API ドキュメント

AWS Bedrock の ApplyGuardrail API を使用したストリーミング統合とベストプラクティスに関するドキュメント集です。

## 📚 ドキュメント一覧

### [ストリーミング実装ガイド](./streaming-implementation-guide.md)

ApplyGuardrail API をストリーミング出力と組み合わせて使用する際の実装ガイド。

**主な内容:**
- ✅ AWS公式推奨のバッファリング戦略（1,000文字単位）
- ✅ チェック単位の仕様（区間ごと vs 累積）
- ✅ `apply_guardrail` 関数の実装例
- ✅ 長文処理（25,000文字超）の実装
- ✅ エラーハンドリングとポリシー違反判定
- ✅ Claude Agent SDK との統合例
- ✅ トラブルシューティング

### [ベストプラクティス](./best-practices.md)

本番環境でApplyGuardrail APIを使用する際のベストプラクティス集。

**主な内容:**
- ✅ アーキテクチャ設計（INPUT/OUTPUT両方のチェック）
- ✅ パフォーマンス最適化（非同期処理、キャッシング）
- ✅ コスト最適化（適切なバッファサイズ、INPUTチェック）
- ✅ セキュリティとコンプライアンス（データレジデンシー、PII）
- ✅ エラーハンドリング（リトライ、フォールバック）
- ✅ モニタリングとロギング（CloudWatch統合）
- ✅ テストとバリデーション

## 🚀 クイックスタート

### 基本的な使い方

```python
import boto3

bedrock_runtime = boto3.client('bedrock-runtime', region_name='ap-northeast-1')

def apply_guardrail(text, source_type, guardrail_id, version="DRAFT"):
    response = bedrock_runtime.apply_guardrail(
        guardrailIdentifier=guardrail_id,
        guardrailVersion=version,
        source=source_type,  # "INPUT" or "OUTPUT"
        content=[{"text": {"text": text}}]
    )

    action = response.get('action', 'NONE')
    is_blocked = (action == 'GUARDRAIL_INTERVENED')

    if source_type == "OUTPUT" and len(response.get('outputs', [])) > 0:
        filtered_text = response['outputs'][0]['text']
    else:
        filtered_text = text

    return is_blocked, filtered_text, response

# 使用例
is_blocked, filtered, _ = apply_guardrail(
    "チェックしたいテキスト",
    "OUTPUT",
    "your-guardrail-id",
    "DRAFT"
)

if is_blocked:
    print("⚠️ コンテンツがブロックされました")
else:
    print(f"✅ フィルタリング済み: {filtered}")
```

### ストリーミングとの統合

```python
async def stream_with_guardrail(prompt, guardrail_id, version):
    buffer = ""
    TEXT_UNIT = 1000  # AWS推奨

    async for chunk in llm.stream(prompt):
        buffer += chunk

        # 1000文字ごとにチェック
        if len(buffer) >= TEXT_UNIT:
            is_blocked, filtered, _ = apply_guardrail(
                buffer,
                "OUTPUT",
                guardrail_id,
                version
            )

            if is_blocked:
                print("🚫 有害コンテンツを検出、停止します")
                break

            print(filtered, end='', flush=True)
            buffer = ""

    # 残りをチェック
    if buffer:
        is_blocked, filtered, _ = apply_guardrail(buffer, "OUTPUT", guardrail_id, version)
        if not is_blocked:
            print(filtered, end='', flush=True)
```

## 📊 重要な仕様

### チェック単位

⚠️ **重要**: ApplyGuardrail API は**区間ごとのチェック**を行います。

```
例：2000文字の出力の場合

[0-1000文字]    → チェック → バッファクリア
[1000-2000文字] → チェック → バッファクリア
                   ↑ 最初の1000文字の文脈は含まれない
```

**理由**:
- ✅ コスト効率（毎回累積をチェックしない）
- ✅ レイテンシ削減（チェック対象が小さい）
- ⚠️ 文脈依存の違反を見逃す可能性

### 料金体系

**ApplyGuardrail API**（フィルタータイプごと）:

| フィルタータイプ | 価格 |
|----------------|------|
| Content filters | $0.15 / 1,000 units |
| Denied topics | $0.15 / 1,000 units |
| Sensitive information (PII) | $0.10 / 1,000 units |
| Word filters | 無料 |

**重要**:
- 1 TEXT_UNIT = 1,000文字
- **1,000文字未満は1 TEXT_UNITに切り上げ**（例: 1文字でも1 TEXT_UNIT）
- 複数フィルター使用時は合算（例: Content + Topics + PII = $0.40 / 1,000 units）

**コスト例**:
```python
import math

# 5,000文字のテキストを3回チェック（3種類のフィルター使用）
text_units_per_check = math.ceil(5000 / 1000)  # 5 TEXT_UNIT
total_units = text_units_per_check * 3  # 15 TEXT_UNIT
filters_cost = 0.40  # Content + Topics + PII
cost = (total_units / 1000) * filters_cost  # $0.006

# 切り上げの例
math.ceil(1 / 1000)     # 1 TEXT_UNIT (1文字)
math.ceil(999 / 1000)   # 1 TEXT_UNIT (999文字)
math.ceil(1000 / 1000)  # 1 TEXT_UNIT (1000文字)
math.ceil(1001 / 1000)  # 2 TEXT_UNIT (1001文字)
```

### レート制限

- **デフォルト**: 25 TEXT_UNIT / 秒
- **最大リクエストサイズ**: 25 TEXT_UNIT (25,000文字)

## 🔗 関連リソース

### プロジェクト内の実装例

- [terraform/examples/streaming_example.py](../../terraform/examples/streaming_example.py)
  - `AgentSDKWithApplyGuardrail` クラス
  - リアルタイムチェックの実装
  - INPUT/OUTPUT フィルタリングのデモ

### AWS公式ドキュメント

- [AWS Bedrock Guardrails Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
- [ApplyGuardrail API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ApplyGuardrail.html)
- [公式サンプルコード - Apply Guardrail with Streaming](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/responsible_ai/bedrock-guardrails/Apply_Guardrail_with_Streaming_and_Long_Context.ipynb)
- [AWS Blog: Use the ApplyGuardrail API with long-context inputs and streaming outputs](https://aws.amazon.com/blogs/machine-learning/use-the-applyguardrail-api-with-long-context-inputs-and-streaming-outputs-in-amazon-bedrock/)

### プロジェクト内の関連ドキュメント

- [ADR-001: Guardrails に AWS Bedrock Guardrails を採用](../adr/ADR-001-guardrails-bedrock.md)

## 💡 使い分けガイド

### InvokeModel + guardrailConfig vs ApplyGuardrail API

| 方式 | 適用シーン | メリット | デメリット |
|------|-----------|---------|----------|
| **InvokeModel + guardrailConfig** | Bedrockモデル専用 | シンプル、統合的 | Bedrock限定 |
| **ApplyGuardrail API** | 任意のLLM | 柔軟、独立運用可 | 実装複雑 |

**推奨**:
- ✅ Bedrockのみ使用 → `guardrailConfig`
- ✅ 複数LLMエンジン → `ApplyGuardrail API`
- ✅ ストリーミングのカスタマイズが必要 → `ApplyGuardrail API`

## 🎯 よくある質問

### Q: ストリーミング時のチェック間隔は？

**A**: AWS公式推奨は**1,000文字（1 TEXT_UNIT）**です。

- 500文字: レイテンシ重視、コスト高
- 1,000文字: バランス（推奨）
- 2,000文字: コスト重視、見逃しリスク増

### Q: INPUT と OUTPUT どちらをチェックすべき？

**A**: **両方をチェック**することを強く推奨します。

- INPUT: プロンプトインジェクション対策、LLMコスト削減
- OUTPUT: 有害コンテンツ生成の防止、PII漏洩防止

### Q: 累積データ全体をチェックできる？

**A**: デフォルトでは**区間ごとのチェック**です。全体をチェックする場合：

```python
# 完了後に全体を再チェック
full_response = ""
for chunk in stream:
    full_response += chunk
    # 区間チェック...

# 最終チェック（全体）
final_result = apply_guardrail(full_response, "OUTPUT", ...)
```

### Q: PII はマスキングされる？

**A**: **OUTPUT ソース**でのみマスキングされます。INPUT ソースではマスキング非対応。

```python
# ✅ マスキングあり
result = apply_guardrail("電話: 090-1234-5678", "OUTPUT", ...)
print(result[1])  # "電話: ***-****-****"

# ❌ マスキングなし（ブロックのみ）
result = apply_guardrail("電話: 090-1234-5678", "INPUT", ...)
```

## 📝 本番環境チェックリスト

デプロイ前に確認：

- [ ] INPUT/OUTPUT 両方のチェックを実装
- [ ] 適切なバッファサイズ（1,000文字推奨）
- [ ] エラーハンドリングとリトライ戦略
- [ ] タイムアウト設定（5-10秒）
- [ ] メトリクス収集（ブロック率、レイテンシ、コスト）
- [ ] CloudWatchアラート設定
- [ ] PII マスキング設定確認
- [ ] データレジデンシー要件確認
- [ ] ユニットテスト実装
- [ ] 統合テスト実装
- [ ] コスト見積もり完了

## 🤝 コントリビューション

ドキュメントの改善提案やバグ報告は Issue でお知らせください。
