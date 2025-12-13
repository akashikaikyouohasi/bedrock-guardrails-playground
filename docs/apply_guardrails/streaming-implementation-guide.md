# ApplyGuardrail API ストリーミング実装ガイド

このドキュメントは、AWS Bedrock の ApplyGuardrail API をストリーミング出力と組み合わせて使用する際の実装ガイドです。

## 概要

ApplyGuardrail API を使用することで、Bedrock の InvokeModel API や他のLLMエンジンと独立して、任意のテキストに対してGuardrailsチェックを実行できます。ストリーミング出力の場合、適切なバッファリング戦略を使用することで、レイテンシとコストのバランスを取りながらリアルタイムチェックを実現できます。

## ストリーミングチェックの仕組み

### チェック単位の重要な仕様

**⚠️ 重要**: ApplyGuardrail API は**区間ごとのチェック**を行います。累積データ全体をチェックするのではありません。

```
例：2000文字の出力の場合

[0-1000文字] → バッファに蓄積 → apply_guardrail(0-1000文字) → バッファクリア
[1000-2000文字] → バッファに蓄積 → apply_guardrail(1000-2000文字) → バッファクリア
                                     ↑ 最初の1000文字の文脈は含まれない

最終チェック → apply_guardrail(残りのバッファ)
```

この方式により：
- ✅ コスト効率が良い（毎回累積をチェックしない）
- ✅ レイテンシが低い（チェック対象が小さい）
- ⚠️ 文脈依存の違反を見逃す可能性がある

## AWS公式推奨のバッファリング戦略

### TEXT_UNIT の定義

AWS公式サンプルコード（[amazon-bedrock-samples](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/responsible_ai/bedrock-guardrails/Apply_Guardrail_with_Streaming_and_Long_Context.ipynb)）では以下の定数が使用されています：

```python
TEXT_UNIT = 1000  # 1テキストユニット = 1000文字
LIMIT_TEXT_UNIT = 25  # 1リクエストあたりの最大テキストユニット数
```

### バッファリングロジック

```python
buffer_text = ""

# ストリーミングチャンクを処理
for chunk in stream:
    new_text = chunk['text']

    # バッファが TEXT_UNIT を超える場合、チェック実行
    if len(buffer_text + new_text) > TEXT_UNIT:
        is_blocked, alt_text, response = apply_guardrail(
            buffer_text,
            "OUTPUT",
            guardrail_id,
            guardrail_version
        )

        if is_blocked:
            # 有害コンテンツ検出時はストリーミングを停止
            print("⚠️ 有害コンテンツを検出しました")
            break

        # フィルタリングされたテキストを出力
        print(alt_text, end='', flush=True)

        # バッファをクリアして新しいテキストのみを保持
        buffer_text = new_text
    else:
        # まだ閾値に達していない場合は蓄積
        buffer_text += new_text

# ストリーミング完了後、残りのバッファをチェック
if buffer_text:
    is_blocked, alt_text, response = apply_guardrail(
        buffer_text,
        "OUTPUT",
        guardrail_id,
        guardrail_version
    )
    if not is_blocked:
        print(alt_text, end='', flush=True)
```

## apply_guardrail 関数の実装

### 基本実装

```python
def apply_guardrail(text, source_type, guardrail_id, version="DRAFT"):
    """
    ApplyGuardrail API を使用してテキストをチェック

    Args:
        text: チェック対象のテキスト
        source_type: "INPUT" または "OUTPUT"
        guardrail_id: Guardrail ID
        version: Guardrailのバージョン（デフォルト: "DRAFT"）

    Returns:
        tuple: (is_blocked, alternate_text, response)
            - is_blocked: ブロックされた場合 True
            - alternate_text: フィルタリング後のテキスト
            - response: API レスポンス全体
    """
    bedrock_runtime = boto3.client('bedrock-runtime')

    response = bedrock_runtime.apply_guardrail(
        guardrailIdentifier=guardrail_id,
        guardrailVersion=version,
        source=source_type,
        content=[{"text": {"text": text}}]
    )

    action = response.get('action', 'NONE')
    is_blocked = (action == 'GUARDRAIL_INTERVENED')

    # OUTPUT の場合、フィルタリング後のテキストを取得
    if source_type == "OUTPUT" and len(response.get('outputs', [])) > 0:
        alternate_text = response['outputs'][0]['text']
    else:
        alternate_text = text

    return is_blocked, alternate_text, response
```

### 長文処理用の実装

25,000文字（25 TEXT_UNIT）を超える文書を処理する場合：

```python
import textwrap

def apply_guardrail_full_text(text, source_type, guardrail_id, version="DRAFT"):
    """
    長文を分割してGuardrailsチェック

    制限: 1リクエストあたり最大 25 TEXT_UNIT (25,000文字)
    """
    TEXT_UNIT = 1000
    LIMIT_TEXT_UNIT = 25
    MAX_CHARS = LIMIT_TEXT_UNIT * TEXT_UNIT  # 25,000文字

    # テキストを分割
    chunks = textwrap.wrap(
        text,
        width=MAX_CHARS,
        break_long_words=False,
        replace_whitespace=False
    )

    filtered_text = ""

    for chunk in chunks:
        is_blocked, alt_text, response = apply_guardrail(
            chunk,
            source_type,
            guardrail_id,
            version
        )

        if is_blocked:
            # 重大な違反が検出された場合、即座に停止
            return True, filtered_text, response

        filtered_text += alt_text

    return False, filtered_text, response
```

## エラーハンドリング

### ポリシー違反の判定

```python
def is_policy_assessment_blocked(response):
    """
    Guardrailsレスポンスから違反の有無を判定

    複数のポリシータイプをチェック:
    - topicPolicy: トピック制限
    - wordPolicy: 禁止ワード
    - sensitiveInformationPolicy: PII検出
    - contentPolicy: 有害コンテンツ
    """
    assessments = response.get('assessments', [])
    if not assessments:
        return False

    assessment = assessments[0]
    policy_types = [
        'topicPolicy',
        'wordPolicy',
        'sensitiveInformationPolicy',
        'contentPolicy'
    ]

    blocked_count = 0
    for policy_type in policy_types:
        if policy_type in assessment:
            policy_data = assessment[policy_type]

            # topicPolicy の場合
            if policy_type == 'topicPolicy':
                for topic in policy_data.get('topics', []):
                    if topic.get('action') == 'BLOCKED':
                        blocked_count += 1

            # wordPolicy の場合
            elif policy_type == 'wordPolicy':
                for word in policy_data.get('customWords', []) + policy_data.get('managedWordLists', []):
                    if word.get('action') == 'BLOCKED':
                        blocked_count += 1

            # sensitiveInformationPolicy の場合
            elif policy_type == 'sensitiveInformationPolicy':
                for pii in policy_data.get('piiEntities', []) + policy_data.get('regexes', []):
                    if pii.get('action') == 'BLOCKED':
                        blocked_count += 1

            # contentPolicy の場合
            elif policy_type == 'contentPolicy':
                for filter_item in policy_data.get('filters', []):
                    if filter_item.get('action') == 'BLOCKED':
                        blocked_count += 1

    return blocked_count > 0
```

### ClientError のハンドリング

```python
from botocore.exceptions import ClientError

try:
    is_blocked, alt_text, response = apply_guardrail(
        text,
        "OUTPUT",
        guardrail_id,
        guardrail_version
    )
except ClientError as err:
    error_message = err.response['Error']['Message']
    print(f"❌ Guardrail APIエラー: {error_message}")
    # エラー時の処理（例: オリジナルテキストをブロック）
    raise
```

## パフォーマンスとコスト最適化

### レイテンシの測定

```python
response = bedrock_runtime.apply_guardrail(...)

# メタデータからレイテンシを取得
metadata = response.get('metadata', {})
latency_ms = metadata.get('metrics', {}).get('latencyMs', 0)

print(f"Guardrailsチェック時間: {latency_ms}ms")
```

### コスト計算

ApplyGuardrail API の料金は**テキストユニット**単位で課金されます。

**重要**: 1,000文字未満は**1 TEXT_UNITに切り上げ**されます。

```python
import math

TEXT_UNIT = 1000  # 1000文字 = 1テキストユニット

def calculate_text_units(text):
    """テキストユニット数を計算（切り上げ）"""
    return math.ceil(len(text) / TEXT_UNIT)

# 例: 5,600文字のテキスト
text_units = calculate_text_units("あ" * 5600)
print(f"テキストユニット数: {text_units}")  # 出力: 6

# 切り上げの例
print(calculate_text_units("あ" * 1))     # 1 TEXT_UNIT
print(calculate_text_units("あ" * 999))   # 1 TEXT_UNIT
print(calculate_text_units("あ" * 1000))  # 1 TEXT_UNIT
print(calculate_text_units("あ" * 1001))  # 2 TEXT_UNIT
```

**料金体系**（フィルタータイプごと）:

| フィルタータイプ | 価格 |
|----------------|------|
| Content filters | $0.15 / 1,000 units |
| Denied topics | $0.15 / 1,000 units |
| Sensitive information (PII) | $0.10 / 1,000 units |
| Word filters | 無料 |

**注意**: 複数のフィルターを使用する場合は合算されます。
- 例: Content + Topics + PII = $0.40 / 1,000 units

### 推奨バッチサイズ

| シナリオ | 推奨バッチサイズ | 理由 |
|---------|----------------|------|
| **ストリーミング** | 1,000文字 (1 TEXT_UNIT) | コストとレイテンシのバランス |
| **小さい文書** | 全体を1回でチェック | ≤25,000文字なら1リクエストで処理可能 |
| **大きい文書** | 25,000文字ごと (25 TEXT_UNIT) | APIの上限に合わせて分割 |
| **リアルタイム性重視** | 500-1,000文字 | より頻繁にチェック |
| **コスト重視** | 2,000-5,000文字 | チェック回数を削減 |

## 実装例: Claude Agent SDK との統合

このプロジェクトの `terraform/examples/streaming_example.py` で実装されている `AgentSDKWithApplyGuardrail` クラスを参照してください：

```python
class AgentSDKWithApplyGuardrail:
    async def chat_streaming(self, prompt: str, realtime_check_interval: int = 100):
        """
        Args:
            realtime_check_interval: リアルタイムチェックの間隔（文字数）
                - 0: 完了後にのみチェック
                - 50: 厳格（50文字ごと）
                - 100: バランス（推奨）
                - 200: パフォーマンス重視
        """
        buffer = ""
        full_response = ""

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        buffer += block.text
                        full_response += block.text

                        # 間隔ごとにチェック
                        if len(buffer) >= realtime_check_interval:
                            result = self.apply_guardrail(buffer, "OUTPUT")
                            if result["is_blocked"]:
                                # 即座に停止
                                break
                            buffer = ""  # チェック後クリア
```

## ベストプラクティス

### 1. チェック間隔の選択

```python
# ❌ 悪い例: 毎回チェック（コスト高、レイテンシ悪化）
if new_text:
    apply_guardrail(new_text, "OUTPUT", ...)

# ✅ 良い例: 1000文字ごとにチェック
if len(buffer) >= 1000:
    apply_guardrail(buffer, "OUTPUT", ...)
```

### 2. INPUT と OUTPUT の両方をチェック

```python
# INPUT チェック（プロンプトインジェクション対策）
input_result = apply_guardrail(user_prompt, "INPUT", guardrail_id, version)
if input_result[0]:  # is_blocked
    return "申し訳ございません。そのリクエストは処理できません。"

# LLM実行
response = invoke_model(user_prompt)

# OUTPUT チェック（有害コンテンツ生成の防止）
output_result = apply_guardrail(response, "OUTPUT", guardrail_id, version)
if output_result[0]:  # is_blocked
    return "申し訳ございません。適切な回答を生成できませんでした。"

return output_result[1]  # フィルタリング済みテキスト
```

### 3. マスキングへの対応

```python
# OUTPUT ソースの場合、マスキングされたテキストを使用
response = apply_guardrail(text, "OUTPUT", guardrail_id, version)

# response['outputs'][0]['text'] にマスキング済みテキストが含まれる
filtered_text = response['outputs'][0]['text']
print(filtered_text)  # 例: "私の電話番号は ***-****-**** です"
```

### 4. レート制限への対応

ApplyGuardrail API のデフォルトレート制限: **25 テキストユニット/秒**

```python
import time

def apply_guardrail_with_rate_limit(text, source_type, guardrail_id, version):
    """レート制限を考慮した実装"""
    text_units = (len(text) // 1000) + 1

    # 1秒あたりのユニット数を追跡
    if hasattr(apply_guardrail_with_rate_limit, 'units_this_second'):
        units_this_second = apply_guardrail_with_rate_limit.units_this_second
    else:
        units_this_second = 0
        apply_guardrail_with_rate_limit.units_this_second = 0

    # レート制限に達する場合は待機
    if units_this_second + text_units > 25:
        time.sleep(1)
        apply_guardrail_with_rate_limit.units_this_second = 0

    result = apply_guardrail(text, source_type, guardrail_id, version)
    apply_guardrail_with_rate_limit.units_this_second += text_units

    return result
```

## トラブルシューティング

### 問題: チェックが遅すぎる

**原因**: バッファサイズが大きすぎる

**解決策**: `realtime_check_interval` を小さくする（例: 1000 → 500）

```python
await agent.chat_streaming(prompt, realtime_check_interval=500)
```

### 問題: コストが高すぎる

**原因**: チェック頻度が高すぎる

**解決策**: `realtime_check_interval` を大きくする（例: 100 → 1000）

```python
await agent.chat_streaming(prompt, realtime_check_interval=1000)
```

### 問題: 文脈依存の違反を見逃す

**原因**: 区間ごとのチェックでは前の文脈が失われる

**解決策**:
1. 最終チェックで全体を再検証する
2. より小さい間隔でチェック
3. 累積バッファを使用する（コスト増）

```python
# 方法1: 最終チェック（推奨）
if full_response:
    final_result = apply_guardrail(full_response, "OUTPUT", ...)
    if final_result[0]:
        # 全体として問題がある場合の処理
        pass

# 方法3: 累積バッファ（コスト高）
cumulative_buffer = ""
for chunk in stream:
    cumulative_buffer += chunk
    if len(cumulative_buffer) >= 1000:
        apply_guardrail(cumulative_buffer, "OUTPUT", ...)  # 毎回全体をチェック
```

## 参考資料

- [AWS公式サンプルコード - Apply Guardrail with Streaming](https://github.com/aws-samples/amazon-bedrock-samples/blob/main/responsible_ai/bedrock-guardrails/Apply_Guardrail_with_Streaming_and_Long_Context.ipynb)
- [AWS Blog: Use the ApplyGuardrail API with long-context inputs and streaming outputs](https://aws.amazon.com/blogs/machine-learning/use-the-applyguardrail-api-with-long-context-inputs-and-streaming-outputs-in-amazon-bedrock/)
- [AWS Bedrock Guardrails Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
- [ApplyGuardrail API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ApplyGuardrail.html)
- [本プロジェクトの実装例](../../terraform/examples/streaming_example.py)
