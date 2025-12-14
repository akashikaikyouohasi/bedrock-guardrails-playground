# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

**Claude Agent SDK** を AWS Bedrock バックエンドで使用し、**Bedrock Guardrails のリアルタイム統合**と Langfuse による監視・評価を実装したサンプルプロジェクト。

### 主な技術スタック
- **Claude Agent SDK**: Anthropic 公式エージェントフレームワーク
- **AWS Bedrock**: Claude モデルのバックエンド（InvokeModel API）
- **ApplyGuardrail API**: リアルタイムセーフティチェック
- **Langfuse**: LLM トレーシング・評価（v3.10.5+）
- **UV**: Python パッケージマネージャー

---

## 開発コマンド

### セットアップ
```bash
make setup          # 初回セットアップ（依存関係インストール + .env作成）
make install        # 依存関係のインストール
make sync           # 依存関係の同期（install + update）
```

### 実行
```bash
make run            # サンプル実行（src/examples.py）
make shell          # IPython シェル起動
```

### Prompt Caching 実験
```bash
make cache-test     # 基本テスト（3回のリクエスト）
make cache-compare  # キャッシュあり・なし比較
make cache-metrics  # CloudWatch Logs からメトリクス取得
```

### 評価
```bash
make eval-setup     # 評価用依存関係インストール（DeepEval）
make eval           # LLM 評価実行
```

### テスト・クリーンアップ
```bash
make test           # テスト実行
make clean          # キャッシュ削除
```

---

## アーキテクチャ

### 全体構成
```
User Input
    ↓
[INPUT Check (optional)] → ApplyGuardrail API
    ↓
[Claude Agent SDK] → AWS Bedrock (InvokeModel)
    ↓ (streaming chunks)
[Buffer 蓄積 → OUTPUT Check] → ApplyGuardrail API
    ↓
[Langfuse トレーシング]
```

### 重要なファイル構成

#### Core Implementation
- **`src/agent.py`** - エージェント実装の中核 (v1.1.0 MVP改善版)
  - `BedrockAgentSDK`: シンプル版（ツールなし）
  - `BedrockAgentSDKWithClient`: 高機能版（ツールあり）
  - `AgentMetrics`: ResultMessage から抽出したメトリクスを保持するデータクラス
  - Langfuse `@observe()` デコレーターで自動トレーシング
  - **重要**: `system_prompt` パラメータで Prompt Caching が自動有効化
  - **v1.1.0 改善**: ResultMessage から実測値を取得、session_id/user_id をトレースレベルで設定

- **`terraform/examples/streaming_example.py`** - Guardrails リアルタイム統合
  - `AgentSDKWithApplyGuardrail`: Claude Agent SDK + ApplyGuardrail API
  - INPUT/OUTPUT チェックの個別制御
  - ストリーミング途中停止機能（有害コンテンツ検出時）
  - チェック間隔: 0（無効）、50（厳格）、100（バランス）、200（パフォーマンス）

- **`src/evaluation.py`** - Langfuse 評価システム
  - `DatasetClient`: データセット管理
  - `run_evaluation_simple()`: ツール未使用評価
  - `run_evaluation_with_tools()`: ツール使用評価

- **`experiments/prompt-caching/`** - Prompt Caching 実験
  - `test_basic_caching.py`: 基本テスト
  - `test_comparison.py`: 比較テスト
  - `check_cache_metrics.py`: CloudWatch Logs からメトリクス取得

#### 設定ファイル
- **`.env`** - 環境変数（未バージョン管理）
  ```bash
  CLAUDE_CODE_USE_BEDROCK=1
  AWS_REGION=us-west-2
  AWS_ACCESS_KEY_ID=your_key
  AWS_SECRET_ACCESS_KEY=your_secret
  LANGFUSE_PUBLIC_KEY=pk-lf-...
  LANGFUSE_SECRET_KEY=sk-lf-...
  ```

- **`pyproject.toml`** - UV プロジェクト設定
  - `langfuse>=3.10.5` 必須（v2.x とは API 互換性なし）
  - `claude-agent-sdk>=0.1.0`

---

## 重要な実装パターン

### 1. Prompt Caching の自動有効化

**AWS Bedrock では InvokeModel API がデフォルトでキャッシュを有効化** - 手動設定不要。

```python
from src.agent import BedrockAgentSDK

# system_prompt を渡すだけで自動キャッシュ
agent = BedrockAgentSDK(
    system_prompt="長いシステムプロンプト（最小トークン数以上）...",
    model="anthropic.claude-3-7-sonnet-20250219-v1:0"
)

# 1回目: キャッシュ書き込み
response1 = await agent.chat("質問1", session_id="test", user_id="user1")

# 2回目以降: キャッシュ読み取り（高速・低コスト）
response2 = await agent.chat("質問2", session_id="test", user_id="user1")
```

**最小トークン数（Claude 4.5 シリーズ）**:
- Claude Sonnet 4.5: 1,024 トークン（約 2,000〜3,000 文字）
- Claude Opus/Haiku 4.5: 4,096 トークン（約 8,000〜12,000 文字）

### 2. Guardrails リアルタイムチェック

**背景**: Claude Agent SDK は Bedrock Guardrails をネイティブサポートしていない
**解決策**: ApplyGuardrail API を使用したハイブリッドアプローチ

```python
from terraform.examples.streaming_example import AgentSDKWithApplyGuardrail

agent = AgentSDKWithApplyGuardrail(
    guardrail_id="your_id",
    guardrail_version="DRAFT",
    enable_input_check=True,   # INPUT チェック有効
    enable_output_check=True   # OUTPUT チェック有効
)

try:
    response = await agent.chat_streaming(
        prompt="ユーザープロンプト",
        realtime_check_interval=100  # 100文字ごとにチェック
    )
except ValueError as e:
    print(f"ブロック: {e}")
```

**特徴**:
- INPUT ブロック時: LLM 実行なし（コスト削減）
- OUTPUT リアルタイムチェック: ストリーミング中に定期的に検証
- 即座停止: 有害コンテンツ検出時にストリーミング停止
- **AWS推奨バッファサイズ**: 1,000文字（1 TEXT_UNIT）
- **チェック方式**: 区間ごと（累積ではない）- コストとレイテンシのバランス

### 3. Langfuse 3.x API の使用 (MVP改善版 v1.1.0)

**重要**: Langfuse 2.x の `root_span.generation()` は v3.x で削除済み

**改善点（v1.1.0）**:
- ✅ `ResultMessage` から実際のトークン使用量・コスト・時間を取得（tiktoken推定から移行）
- ✅ `session_id`/`user_id` をトレースレベルで設定（メタデータではなく適切なフィールドに）
- ✅ Prompt Caching メトリクス（`cache_creation_input_tokens`, `cache_read_input_tokens`）を追跡

```python
from src.agent import BedrockAgentSDK

# session_id/user_id はトレースレベルで自動設定される
agent = BedrockAgentSDK(
    system_prompt="長いシステムプロンプト...",
)

# Langfuse に正確なメトリクスが記録される:
# - input_tokens, output_tokens (実測値)
# - cache_creation_input_tokens, cache_read_input_tokens
# - total_cost_usd, duration_ms
# - session_id, user_id (トレースレベル)
response = await agent.chat("質問", session_id="my-session", user_id="user-123")
```

**Langfuse ダッシュボードで確認できる情報**:
- トークン使用量（入力/出力/キャッシュ）
- コスト（USD）
- レイテンシ（ms）
- セッション別・ユーザー別の追跡
- Prompt Caching の効果

**API の使い方**:
```python
# ❌ 古い API (v2.x) - 使用不可
root_span = item.run(run_name="test")
generation = root_span.generation(...)  # AttributeError

# ✅ 新しい API (v3.x)
# デコレーター使用時: langfuse_context を使用
from langfuse.decorators import langfuse_context

langfuse_context.update_current_trace(session_id="...", user_id="...")
langfuse_context.update_current_observation(usage={...})

# 手動トレーシング時: trace → generation の階層構造
trace = langfuse.trace(name="...", session_id="...", user_id="...")
generation = trace.generation(name="...", model="...", input="...")
generation.update(output="...", usage={...})
generation.end()
```

### 4. ツール使用の実装

**重要**: `BedrockAgentSDK` は `tools` パラメータを受け取るが**内部で使用しない**。
ツール機能が必要な場合は `BedrockAgentSDKWithClient` を使用すること。

```python
# ❌ ツールは動作しない
agent = BedrockAgentSDK(tools=["Read", "Write"])  # tools は無視される

# ✅ 正しい実装
from src.agent import BedrockAgentSDKWithClient

async with BedrockAgentSDKWithClient(tools=["Read", "Write"]) as agent:
    async for message in agent.chat_with_client(prompt):
        print(message)
```

---

## データフロー

### Guardrails リアルタイムチェック

```
1. INPUT チェック（オプション）
   - ApplyGuardrail API でプロンプトを検証
   - ブロック時: LLM 実行せずエラー返却

2. Claude Streaming
   - AWS Bedrock InvokeModel API
   - ストリーミングチャンク受信

3. OUTPUT チェック（リアルタイム）
   - バッファに蓄積（例: 100文字ごと）
   - ApplyGuardrail API で区間バッファを検証（チェック後クリア）
   - ⚠️ 注意: 累積ではなく区間ごとのチェック（前回の文脈は失われる）
   - ブロック検出時: ストリーミング即座停止
   - 最終チェック: 完了後に全体を再検証（オプション）

4. Langfuse トレーシング
   - すべてのリクエストを自動記録
   - トークン数、レイテンシ、エラーを追跡
```

---

## トラブルシューティング

### Langfuse 接続エラー
```
NotFoundError: Dataset not found
```
**解決**: `DatasetClient.load_and_create_dataset()` でデータセット作成

### AWS 認証エラー
```
InvalidSignatureException
```
**解決**: `.env` の AWS 認証情報を確認・更新

### Claude Agent SDK エラー
```
CLI not found error
```
**解決**: `uv pip install --force-reinstall claude-agent-sdk`

### キャッシュが効かない
**確認方法**:
```bash
make cache-metrics  # CloudWatch Logs から確認
```

**原因**:
- システムプロンプトが最小トークン数未満
- リクエスト間隔が 5分以上
- プロンプトが毎回変更されている

---

## 環境要件

- **Python**: 3.10+
- **Package Manager**: UV
- **AWS**: Bedrock アクセス + Claude モデル有効化
- **Langfuse**: SaaS アカウント (cloud.langfuse.com)

---

## ドキュメント参照

### Guardrails 関連
- **Guardrails 総合ガイド**: `docs/apply_guardrails/README.md`
- **設計ガイド**: `docs/apply_guardrails/design-guide.md` 🆕
  - 設計フロー（6フェーズ）と総合チェックリスト
  - 要件定義、ポリシー設計、実装、テスト、デプロイ、運用
  - ユースケース別推奨設定マトリクス
- **ストリーミング実装ガイド**: `docs/apply_guardrails/streaming-implementation-guide.md`
  - AWS公式推奨のバッファリング戦略（1,000文字単位）
  - チェック単位の仕様（区間ごと vs 累積）の詳細
  - エラーハンドリングとトラブルシューティング
- **ベストプラクティス**: `docs/apply_guardrails/best-practices.md`
  - アーキテクチャ設計、パフォーマンス最適化
  - コスト最適化、セキュリティとコンプライアンス
  - モニタリング、テストとバリデーション

### その他
- **Prompt Caching**: `docs/prompt-caching/bedrock-prompt-caching-guide.md`
- **Langfuse 評価**: `docs/langfuse/evaluation-strategy.md`
- **ADR**: `docs/adr/` - アーキテクチャ決定記録
- **README**: プロジェクト全体概要と使用例

---

## 開発時の注意点

### バージョン管理
- `pyproject.toml` で明示的にバージョン指定
- `uv.lock` で完全固定化
- Langfuse `>=3.10.5` 必須（v2.x とは非互換）

### 非同期処理
- `anyio` を使用（`asyncio` より互換性高い）
- すべてのエージェント呼び出しは async
- `anyio.run()` を推奨

### セキュリティ
- `.env` は `.gitignore` に含める
- 本番環境では環境変数で管理
