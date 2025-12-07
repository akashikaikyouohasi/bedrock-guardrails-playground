# Claude.md - プロジェクトコンテキスト

## プロジェクト概要

このプロジェクトは、**Claude Agent SDK** を AWS Bedrock のバックエンドとして使用し、**Bedrock Guardrails のリアルタイム統合**と Langfuse で LLM アプリケーションを監視・評価するサンプルです。

### 主な目的
- Claude Agent SDK の動作確認
- Bedrock 経由での Claude モデルの利用
- **Bedrock Guardrails のリアルタイムチェック実装** (ApplyGuardrail API)
- Langfuse を使用した LLM トレースと評価
- エージェントベースのアプリケーション構築

## アーキテクチャ

```
┌─────────────┐
│  Your App   │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Claude Agent SDK + Guardrails       │
│  (src/agent.py)                      │
│  (terraform/examples/                │
│   streaming_example.py)              │
└──────┬───────────────────────────────┘
       │
       ├────────────────┬─────────────────┐
       │                │                 │
       ▼                ▼                 ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
│ AWS Bedrock │  │  ApplyGuard  │  │ Langfuse Server  │
│ (Claude 3+) │  │  rail API    │  │ (Monitoring)     │
│ (Streaming) │  │ (Realtime    │  └──────────────────┘
└─────────────┘  │  Check)      │
                 └──────────────┘
```

### Guardrails リアルタイムチェック

```
User Input
    ↓
[INPUT Check] → ApplyGuardrail API
    ↓ (if PASS)
[Claude Streaming] → Bedrock
    ↓ (chunks)
[Buffer 蓄積] → 100文字ごと
    ↓
[OUTPUT Check] → ApplyGuardrail API
    ↓
[BLOCKED?] → Yes: 停止 / No: 継続
```

## ファイル構成と役割

### Core Implementation Files

- **`src/agent.py`** - Claude Agent SDK の実装
  - `BedrockAgentSDK`: ツールなしのシンプルなエージェント
  - `BedrockAgentSDKWithClient`: ツール機能付きのエージェント
  - `@observe()` デコレーターで自動トレーシング有効化

- **`terraform/examples/streaming_example.py`** - Guardrails リアルタイムチェック実装
  - `AgentSDKWithApplyGuardrail`: Claude Agent SDK + ApplyGuardrail API
  - INPUT チェック: プロンプト送信前の検証（オプション）
  - OUTPUT チェック: ストリーミング中のリアルタイム検証
  - 即座停止: 有害コンテンツ検出時にストリーミングを即座に停止
  - チェック間隔設定: 0（無効）、50（厳格）、100（バランス）、200（パフォーマンス）

- **`src/evaluation.py`** - Langfuse 評価システム
  - `DatasetClient` クラスでデータセット管理
  - 複数の評価関数（contains_evaluator, similarity_evaluator など）
  - `run_evaluation_simple()`: ツール未使用の評価
  - `run_evaluation_with_tools()`: ツール使用時の評価

- **`src/run_evaluation.py`** - 評価実行スクリプト
  - メイン評価ワークフロー
  - JSON/CSV データセットのロード
  - 結果の Langfuse ダッシュボードへの送信

### Configuration & Build

- **`pyproject.toml`** - UV プロジェクト設定
  - Langfuse `>=3.10.5` (最新 API に対応)
  - claude-agent-sdk `>=0.1.0`
  - boto3, anyio, python-dotenv

- **`Makefile`** - ビルドコマンド
  - `make setup`: 初期セットアップ
  - `make run`: サンプル実行
  - `make eval`: Langfuse 評価実行
  - `make shell`: IPython 対話シェル

- **`.env` ファイル** - 環境設定（未バージョン管理）
  - AWS 認証情報
  - Langfuse API キー
  - Claude モデル指定

### Data & Documentation

- **`datasets/`** - 評価用データセット
  - `sample_qa.json`: JSON 形式のサンプルデータ
  - `sample_qa.csv`: CSV 形式のサンプルデータ

- **`terraform/`** - インフラストラクチャコード
  - AWS リソース定義（Bedrock Guardrails）

- **`docs/apply_guardrails/`** - Guardrails 実装ドキュメント
  - `implementation-guide.md`: バックエンドエンジニア向け実装ガイド
    - フロー図（Mermaid）
    - API レスポンスフォーマット詳細
    - 実装パターン（基本 & リアルタイム）
    - FastAPI 実装例
  - `streaming-realtime-check-experiment.md`: 実験レポート
    - 8つのテストケース
    - リアルタイム停止の実証（2ケース成功）
    - パフォーマンスメトリクス
  - `apply-guardrail-api-implementation.md`: ApplyGuardrail API 基礎

## 重要な実装ポイント

### Guardrails リアルタイムチェック実装

**背景**: Claude Agent SDK は Bedrock Guardrails をネイティブサポートしていない

**解決策**: ApplyGuardrail API を使用したハイブリッドアプローチ

```python
from streaming_example import AgentSDKWithApplyGuardrail

# Guardrails 統合エージェントの初期化
agent = AgentSDKWithApplyGuardrail(
    guardrail_id="gifc1v7qwbdm",
    guardrail_version="DRAFT",
    enable_input_check=True,   # INPUT チェック有効
    enable_output_check=True   # OUTPUT チェック有効
)

# リアルタイムチェック付きストリーミング
try:
    response = agent.chat_streaming(
        prompt="ユーザープロンプト",
        realtime_check_interval=100  # 100文字ごとにチェック
    )
    print(response)
except ValueError as e:
    print(f"ブロック: {e}")
```

**特徴**:
- INPUT ブロック時: LLM 実行なし（コスト削減）
- OUTPUT リアルタイムチェック: ストリーミング中に定期的に検証
- 即座停止: 有害コンテンツ検出時にストリーミングを即座に停止
- 柔軟な設定: INPUT/OUTPUT を個別に有効/無効化

**実証済みの効果**:
- 2つのテストケースでストリーミング途中停止に成功
- 50-100文字間隔でのチェックで実用的なパフォーマンス
- Claude の安全機構 + Guardrails の二重防御

### Langfuse 3.x API の変更点

**問題**: 元々のコードは Langfuse 2.x の古い API を使用していた
- `root_span.generation()` メソッドが存在しない

**解決策**: Langfuse 3.10.5 の新 API に対応
- `item.run()` は `LangfuseSpan` を返す（`generation()` メソッドなし）
- `span.score()` で直接スコアを記録
- 推奨: `dataset.run_experiment()` を使用

### エージェント実装の特徴

1. **`BedrockAgentSDK`** - シンプル版
   - ツール機能なし
   - ストリーミング対応

2. **`BedrockAgentSDKWithClient`** - 高機能版
   - ツール機能対応（Read, Write, Bash 等）
   - ClaudeSDKClient を内部で使用

### トレーシング

- `@observe()` デコレーターで自動トレーシング
- すべてのエージェント実行が Langfuse に自動送信
- 手動トレーシングのサポート（`start_as_current_span()` など）

## 環境要件

- **Python**: 3.10+
- **Package Manager**: UV
- **AWS**: Bedrock アクセス + Claude モデル有効化
- **Langfuse**: SaaS アカウント (cloud.langfuse.com)

## セットアップ手順

```bash
# 1. 依存関係インストール
make install

# 2. .env ファイル作成・編集
cp .env.example .env
# AWS と Langfuse の認証情報を設定

# 3. サンプル実行
make run

# 4. 評価実行
make eval
```

## 開発時の注意点

### バージョン管理

- `pyproject.toml` で明示的にバージョン指定
- `uv.lock` で完全に固定化
- CI/CD では `uv.lock` を使用

### API キーの管理

- `.env` は `.gitignore` に含める
- `.env.example` にはプレースホルダーを設定
- 本番環境では環境変数で管理

### 非同期処理

- `anyio` を使用（asyncio よりも互換性が高い）
- すべてのエージェント呼び出しは async
- `asyncio.run()` ではなく `anyio.run()` を使用

## トラブルシューティング

### Langfuse 接続エラー

```
langfuse.api.resources.commons.errors.not_found_error.NotFoundError: Dataset not found
```

**原因**: データセットが Langfuse に存在しない
**解決**: `load_and_create_dataset()` でデータセットを作成

### AWS 認証エラー

```
InvalidSignatureException: The request signature we calculated does not match
```

**原因**: AWS 認証情報が無効または期限切れ
**解決**: `.env` の AWS 認証情報を確認・更新

### CLI Not Found

```
CLI not found error
```

**原因**: Claude Agent SDK が正しくインストールされていない
**解決**: `uv pip install --force-reinstall claude-agent-sdk`

## 参考リソース

- [Claude Agent SDK Docs](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Langfuse SDK v3 Docs](https://langfuse.com/docs/sdk/python)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [UV Package Manager](https://github.com/astral-sh/uv)

## 最新の変更

### 2025-12-07

- **Guardrails リアルタイムチェック実装完了**
  - `AgentSDKWithApplyGuardrail` クラス実装
  - INPUT/OUTPUT チェックの柔軟な設定
  - ストリーミング途中停止機能の実証
  - 実験レポートと実装ガイドの作成

- **ドキュメント整備**
  - `implementation-guide.md`: バックエンドエンジニア向け実装ガイド
  - `streaming-realtime-check-experiment.md`: 検証実験レポート
  - フロー図（Mermaid）、API レスポンスフォーマット詳細

### 2024-12-06

- Langfuse を 2.52.0 から 3.10.5 にアップグレード
- 古い `generation()` API を削除
- `span.score()` による直接スコアリングに対応
- `pyproject.toml` で Langfuse `>=3.10.5` を明示指定
- 評価ワークフロー完全動作確認

## キーコンセプト

### Dataset Items と Runs

```python
# データセットアイテムを取得
dataset = langfuse.get_dataset("qa-evaluation-dataset")

# 各アイテムについて実行
for item in dataset.items:
    # item.input: 入力データ
    # item.expected_output: 期待される出力
    # item.metadata: メタデータ

    # 実行トレースを開始
    with item.run(run_name="my-run") as span:
        # アプリケーション実行
        output = my_app(item.input)

        # スコアを記録
        span.score(name="accuracy", value=1.0)
```

### 評価関数

```python
def evaluator(output: str, expected_output: str) -> float:
    """0.0 ~ 1.0 のスコアを返す"""
    # 評価ロジック
    return score
```

## ライセンス

MIT
