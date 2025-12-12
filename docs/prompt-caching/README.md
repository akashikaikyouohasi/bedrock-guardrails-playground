# Prompt Caching ドキュメント

このディレクトリには、AWS Bedrock Prompt Caching に関するドキュメントが含まれています。

## ドキュメント一覧

### [bedrock-prompt-caching-guide.md](./bedrock-prompt-caching-guide.md)

**AWS Bedrock Prompt Caching の完全ガイド**

Bedrock の Prompt Caching 機能を活用して、レイテンシを最大 85%、コストを最大 90% 削減する方法を解説しています。

#### 主な内容

| セクション | 内容 |
|-----------|------|
| **概要** | Prompt Caching とは、効果 |
| **対応モデル** | Claude 4.5/4.0/3.x モデル一覧、最小トークン数、日本語換算 |
| **AWS Bedrock の自動キャッシュ機能** | InvokeModel API によるデフォルト有効化 |
| **キャッシュの仕様** | TTL、料金体系、ヒット条件 |
| **Claude Agent SDK での利用** | 自動キャッシュ、実装例 |
| **ユースケース別パターン** | ドキュメント Q&A、サポート、コードレビュー |
| **ベストプラクティス** | 効果を高める設計、避けるべきパターン |
| **このプロジェクトでの実装例** | BedrockAgentSDK、Guardrails 統合 |
| **キャッシュ確認方法** | CloudWatch、AWS CLI、boto3 |
| **まとめ** | チェックリスト、次のステップ |

---

## クイックスタート

### 1. 環境変数を設定

```bash
# .env
CLAUDE_CODE_USE_BEDROCK=1
AWS_REGION=ap-northeast-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

### 2. Claude Agent SDK を使用

```python
from claude_agent_sdk import query, ClaudeAgentOptions
import asyncio

async def main():
    # 長いシステムプロンプト
    # Claude Sonnet 4.5: 1,024トークン（約2,000〜3,000文字）以上
    # Claude Opus/Haiku 4.5: 4,096トークン（約8,000〜12,000文字）以上
    options = ClaudeAgentOptions(
        system_prompt="長いシステムプロンプト（最小トークン数以上）..."
    )

    # 1回目: キャッシュ書き込み
    async for msg in query(prompt="質問1", options=options):
        print(msg)

    # 2回目以降: キャッシュ読み取り（高速・低コスト）
    async for msg in query(prompt="質問2", options=options):
        print(msg)

asyncio.run(main())
```

### 3. 効果を確認

```bash
# CloudWatch メトリクスで確認
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name CacheReadInputTokens \
  --dimensions Name=ModelId,Value=anthropic.claude-3-7-sonnet-20250219-v1:0 \
  --start-time 2025-01-01T00:00:00Z \
  --end-time 2025-01-01T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --region ap-northeast-1
```

---

## 重要なポイント

### ✅ 東京リージョン対応済み

日本国内データレジデンシー要件を満たしながら Prompt Caching を利用可能です。

### 🎉 AWS Bedrock の自動キャッシュ

**InvokeModel API を呼び出すと、プロンプトキャッシュがデフォルトで有効になります**

特別な設定や `cache_control` の手動設定は不要です！

### ✨ 追加実装不要

Claude Agent SDK では、環境変数を設定するだけで自動的に Prompt Caching が有効になります。

### 📊 最小トークン数（Claude 4.5 シリーズ）

| モデル | 最小トークン | 日本語換算（目安） |
|--------|-------------|-------------------|
| **Claude Sonnet 4.5** | 1,024 | 約 2,000〜3,000 文字 |
| **Claude Opus 4.5** | 4,096 | 約 8,000〜12,000 文字 |
| **Claude Haiku 4.5** | 4,096 | 約 8,000〜12,000 文字 |

**日本語の場合**: 1 トークン ≈ 2〜3 文字

### 🚀 最大の効果を得るには

- システムプロンプトを最小トークン数以上にする
- 静的コンテンツを先頭に配置する
- 5分以内に複数リクエストを送信する

---

## 関連ドキュメント

- [ADR-001: Guardrails に AWS Bedrock Guardrails を採用](../adr/ADR-001-guardrails-bedrock.md)
- [ADR-002: 評価に DeepEval + Langfuse を採用](../adr/ADR-002-evaluation-deepeval-langfuse.md)
- [テスト戦略](../evaluation/testing-strategy.md)
