# Langfuse トレーシング ドキュメント

このディレクトリには、Claude Agent SDK と Bedrock を使用したアプリケーションにおける Langfuse トレーシングの実装と運用に関するドキュメントが含まれています。

## 📚 ドキュメント一覧

### [トレーシング概要](./tracing-overview.md)
Langfuse トレーシングの基本概念、アーキテクチャ、および送信される情報の詳細について説明しています。

- Langfuse とは
- トレーシングの仕組み
- Generation、Trace、Span の概念
- 送信される情報の一覧

### [実装ガイド](./implementation-guide.md)
実際の実装方法、サンプルコード、API の使い方について説明しています。

- 基本的な実装パターン
- 手動トレーシング vs デコレータ
- トークン使用量の記録
- session_id / user_id の設定
- エラーハンドリング

### [ベストプラクティス](./best-practices.md)
運用におけるベストプラクティス、パフォーマンス最適化、トラブルシューティングについて説明しています。

- メタデータの設計
- コスト最適化
- パフォーマンスチューニング
- よくある問題と解決方法

## 🚀 クイックスタート

### 基本的な使い方

```python
from src.agent import BedrockAgentSDK

# エージェントを初期化
agent = BedrockAgentSDK(
    model="anthropic.claude-3-5-sonnet-20241022-v2:0",
    temperature=0.7,
    max_tokens=4096
)

# session_id と user_id を指定して実行
response = await agent.chat(
    prompt="こんにちは",
    session_id="session-123",
    user_id="user-456"
)
```

### Langfuse ダッシュボードで確認

すべてのトレースは自動的に Langfuse に送信されます。以下の情報が記録されます：

- ✅ **トークン使用量** - 入力/出力トークン数とコスト
- ✅ **モデルパラメータ** - temperature, max_tokens など
- ✅ **セッション追跡** - session_id による会話フロー
- ✅ **ユーザー分析** - user_id によるユーザー別メトリクス
- ✅ **パフォーマンス** - レスポンス時間、メッセージ数
- ✅ **環境情報** - AWS リージョン、SDK バージョン

## 📊 送信される主な情報

| カテゴリ | フィールド | 説明 |
|---------|-----------|------|
| **基本情報** | `model` | モデル識別子 |
| | `input` | 入力プロンプト |
| | `output` | 生成されたレスポンス |
| **使用量** | `usage_details.input` | 入力トークン数 |
| | `usage_details.output` | 出力トークン数 |
| | `usage_details.total` | 合計トークン数 |
| **パラメータ** | `model_parameters.temperature` | サンプリング温度 |
| | `model_parameters.max_tokens` | 最大トークン数 |
| **トレース** | `metadata.session_id` | セッション ID |
| | `metadata.user_id` | ユーザー ID |
| **環境** | `metadata.aws_region` | AWS リージョン |
| | `metadata.version` | アプリケーションバージョン |
| | `metadata.streaming` | ストリーミングモード |
| | `metadata.sdk` | 使用 SDK |

## 🔧 実装されているクラスとメソッド

### BedrockAgentSDK
シンプルなエージェント（ツールなし）

- `chat_streaming(prompt, session_id, user_id)` - ストリーミングチャット
- `chat(prompt, session_id, user_id)` - 非ストリーミングチャット

### BedrockAgentSDKWithClient
ツール機能付きエージェント

- `chat_with_client(prompt, session_id, user_id)` - ツール使用可能なチャット

### simple_query
シンプルなクエリ関数

- `simple_query(prompt, session_id, user_id, model, temperature, max_tokens)` - 単発クエリ

## 📈 Langfuse ダッシュボードの活用

### コスト分析
- トークン使用量からコストを自動計算
- ユーザー別、セッション別のコスト追跡
- 時系列でのコスト推移

### パフォーマンス分析
- レスポンス時間の分析
- トークン効率の測定
- ボトルネックの特定

### ユーザー分析
- user_id でユーザー別の使用状況を追跡
- session_id で会話フローを可視化
- ユーザーエンゲージメントの測定

## 🔗 関連リンク

- [Langfuse 公式ドキュメント](https://langfuse.com/docs)
- [Langfuse Python SDK](https://langfuse.com/docs/observability/sdk/python/overview)
- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)
- [プロジェクト README](../../README.md)
- [CLAUDE.md - プロジェクトコンテキスト](../../CLAUDE.md)

## 📝 更新履歴

### 2025-12-08
- 初版作成
- トークン使用量の推定機能を追加
- モデルパラメータの記録を追加
- session_id / user_id の metadata 対応
- 詳細なメタデータの追加

## 💡 サポート

問題が発生した場合は、[ベストプラクティス](./best-practices.md) の「トラブルシューティング」セクションを参照してください。
