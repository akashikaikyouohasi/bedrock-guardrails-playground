# Claude Agent SDK with Bedrock Guardrails & Langfuse

このプロジェクトは、**Claude Agent SDK**（公式エージェントフレームワーク）とAmazon Bedrock Guardrailsを組み合わせた安全なAIアプリケーションの実装方法を示します。

## 🎯 主な成果

**ApplyGuardrail API**を使用することで、Claude Agent SDKとBedrock Guardrailsのリアルタイム統合に成功しました：

- ✅ **リアルタイム OUTPUT チェック**: ストリーミング中に有害コンテンツを検出・即座に停止
- ✅ **実証済みの効果**: 2つのテストケースで有害コンテンツを検出し、ストリーミングを途中停止
- ✅ **INPUT チェック**: プロンプト送信前のブロックでコスト削減
- ✅ **Agent SDK機能の維持**: ツール使用や会話継続などの高度な機能
- ✅ **柔軟な制御**: INPUT/OUTPUT フィルタリングを個別に設定可能（有効/無効切り替え）
- ✅ **詳細なドキュメント**: 
  - [実装ガイド](docs/apply_guardrails/implementation-guide.md) - バックエンドエンジニア向け
  - [実験レポート](docs/apply_guardrails/streaming-realtime-check-experiment.md) - 検証結果

## アーキテクチャ

```
User Input
    ↓
┌─────────────────────────────────────┐
│ 1. INPUT チェック (オプション)        │
│    ApplyGuardrail API               │
│    - プロンプト送信前の検証           │
│    - ブロック時: LLM実行なし          │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 2. Claude Agent SDK                 │
│    (AWS Bedrock ストリーミング)      │
│    - ツール使用、会話継続             │
│    - リアルタイムチャンク出力         │
└──────────┬──────────────────────────┘
           │
           │ バッファ蓄積 (例: 100文字)
           ↓
┌─────────────────────────────────────┐
│ 3. OUTPUT チェック (リアルタイム)     │
│    ApplyGuardrail API               │
│    - 定期的なチェック (50-200文字)    │
│    - 検出時: ストリーミング即座停止    │
└─────────────────────────────────────┘
    ↓
    Langfuse (監視・トレーシング)
```

### リアルタイムチェックの特徴

- **即座停止**: 有害コンテンツ検出時にストリーミングを即座に停止
- **バッファ方式**: 指定文字数ごとに累積バッファをチェック
- **設定可能**: チェック間隔 (0=無効, 50=厳格, 100=バランス, 200=パフォーマンス)
- **コスト効率**: INPUT ブロックで LLM 実行コストをゼロに

## Claude Agent SDKとは？

Claude Agent SDKは、AnthropicのAIエージェント構築用公式フレームワークです。基本的なAnthropic APIクライアントとは異なり、Agent SDKは以下を提供します：

- **自律的なエージェントループ** - エージェントが自動的にツールを使用し、推論し、反復できる
- **組み込みツール管理** - Pythonデコレーターでツールを定義
- **ストリーミングレスポンス** - エージェントとのリアルタイムインタラクション
- **ファイル操作とコード実行** - 組み込み機能
- **状態管理** - マルチターン会話の処理

## 機能

- **🛡️ Bedrock Guardrails統合**: ApplyGuardrail APIによる入出力フィルタリング
- **⚡ Prompt Caching**: レイテンシ最大85%、コスト最大90%削減（東京リージョン対応）
- **Claude Agent SDK**: Anthropic公式エージェントフレームワーク
- **AWS Bedrockバックエンド**: AWS Bedrock経由でClaudeモデルを使用
- **ストリーミングレスポンス**: リアルタイムのエージェントインタラクション
- **Langfuse統合**: 完全な観測性とトレーシング
- **ツールサポート**: Read、Write、Bash、カスタムツール
- **UVパッケージマネージャー**: 高速でモダンなPythonパッケージ管理

## 📚 ドキュメント

### Guardrails 実装ガイド

- **[実装ガイド](docs/apply_guardrails/implementation-guide.md)** - バックエンドエンジニア向け完全ガイド
  - フロー図 (Mermaid)
  - API レスポンスフォーマット詳細
  - 実装パターン (基本 & リアルタイム)
  - FastAPI 実装例
  - エラーハンドリング

- **[実験レポート](docs/apply_guardrails/streaming-realtime-check-experiment.md)** - リアルタイムチェック検証結果
  - 8つのテストケース詳細
  - リアルタイム停止の実証 (2ケース成功)
  - パフォーマンスメトリクス
  - 実装推奨事項

- **[基礎ドキュメント](docs/apply_guardrails/apply-guardrail-api-implementation.md)** - ApplyGuardrail API の基礎

### Prompt Caching ガイド

- **[Prompt Caching ガイド](docs/prompt-caching/bedrock-prompt-caching-guide.md)** - コスト削減・高速化の完全ガイド
  - レイテンシ最大 85%、コスト最大 90% 削減
  - Claude Agent SDK での自動キャッシュ活用
  - CloudWatch でのキャッシュ効果測定
  - ✅ **東京リージョン対応済み**

### インフラとサンプル

- **[Terraform インフラ](terraform/)** - Guardrails リソースの定義
- **[実装サンプル](terraform/examples/)** - リアルタイムチェック実装
  - `streaming_example.py` - AgentSDKWithApplyGuardrail クラス

## 前提条件

- Python 3.10以上
- [uv](https://github.com/astral-sh/uv) パッケージマネージャー
- AWS アカウント（Bedrockアクセス、Claudeモデル有効化済み）
- Langfuse アカウント（SaaS: https://cloud.langfuse.com）

## クイックスタート

### 1. UVのインストール

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# または pip を使用
pip install uv
```

### 2. プロジェクトのセットアップ

```bash
# セットアップ実行（依存関係のインストールと.envファイルの作成）
make setup
```

### 3. 環境設定

`.env`ファイルを編集して認証情報を設定：

```bash
# AWS認証情報
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-west-2

# Claude Agent SDK - Bedrockモードを有効化
CLAUDE_CODE_USE_BEDROCK=1

# Bedrock Guardrails設定（オプション）
BEDROCK_GUARDRAIL_ID=your_guardrail_id
BEDROCK_GUARDRAIL_VERSION=DRAFT

# Langfuse認証情報（https://cloud.langfuse.com から取得）
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# オプション: 使用するClaudeモデルを指定
# デフォルト: anthropic.claude-3-5-sonnet-20241022-v2:0
ANTHROPIC_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
```

### 4. サンプルの実行

#### 基本的な使用例

```bash
# Claude Agent SDKサンプルを実行
make run

# または直接実行
uv run python src/examples.py
```

#### Guardrails統合デモ（リアルタイムチェック）

```bash
# リアルタイム Guardrails チェックのデモを実行
cd terraform/examples
python streaming_example.py
```

**実装内容**:
- `AgentSDKWithApplyGuardrail` クラス: Claude Agent SDK + ApplyGuardrail API
- INPUT チェック: プロンプト送信前の検証
- OUTPUT チェック: ストリーミング中のリアルタイム検証（100文字ごと）
- 即座停止: 有害コンテンツ検出時にストリーミングを即座に停止

**テストケース**:
- Part 1: INPUT フィルタリングテスト
- Part 1.5: INPUT 無効 + リアルタイム OUTPUT チェック（攻撃的プロンプト）
- Part 1.6: Haiku モデルでの検証
- Part 2: OUTPUT シミュレーションテスト

詳細は以下を参照：
- [実装ガイド](docs/apply_guardrails/implementation-guide.md)
- [実験レポート](docs/apply_guardrails/streaming-realtime-check-experiment.md)

## AWS Bedrockのセットアップ

### Bedrockモデルの有効化

1. AWSコンソール → Bedrock → Model accessに移動
2. Claudeモデルへのアクセスをリクエスト：
   - Claude 3.5 Sonnet
   - Claude 3 Opus
   - Claude 3 Haiku

### IAM権限

AWSユーザー/ロールに以下の権限が必要です：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    }
  ]
}
```

### モデルの変更

デフォルトでは`Claude 3.5 Sonnet v2`が使用されますが、環境変数で変更できます：

```bash
# .envファイルに追加
ANTHROPIC_MODEL=anthropic.claude-3-opus-20240229-v1:0
```

**利用可能なBedrockモデルID：**

| モデル | モデルID | 特徴 |
|--------|----------|------|
| Claude 3.5 Sonnet v2 | `anthropic.claude-3-5-sonnet-20241022-v2:0` | 最新・最も高性能（デフォルト） |
| Claude 3.5 Sonnet v1 | `anthropic.claude-3-5-sonnet-20240620-v1:0` | 前バージョン |
| Claude 3 Opus | `anthropic.claude-3-opus-20240229-v1:0` | 最高性能・高コスト |
| Claude 3 Haiku | `anthropic.claude-3-haiku-20240307-v1:0` | 高速・低コスト |

**小型モデル用のリージョン設定（オプション）：**

```bash
# Haiku用に別のリージョンを指定する場合
ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION=us-west-2
```

## 使用例

### 例1: シンプルなクエリ

```python
import anyio
from agent import simple_query

async def main():
    response = await simple_query("2 + 2は？")
    print(response)

anyio.run(main)
```

### 例2: ストリーミングチャット

```python
import anyio
from agent import BedrockAgentSDK

async def main():
    agent = BedrockAgentSDK()

    async for chunk in agent.chat_streaming("量子コンピューティングについて説明して"):
        print(chunk)

anyio.run(main)
```

### 例3: ClaudeSDKClientでツールを使う（高度）

**注意**: `BedrockAgentSDK`は`tools`パラメータを受け取りますが、内部的には使用されません。ツール機能が必要な場合は、必ず`BedrockAgentSDKWithClient`を使用してください。

```python
import anyio
from agent import BedrockAgentSDKWithClient

async def main():
    # ツールを初期化時に指定
    tools = ["Write"]

    async with BedrockAgentSDKWithClient(tools=tools) as agent:
        async for message in agent.chat_with_client(
            "Hello Worldを出力するPythonスクリプトを作成して"
        ):
            print(message)

anyio.run(main)
```

### 例4: 複数のツールを使う

```python
import anyio
from agent import BedrockAgentSDKWithClient

async def main():
    # ファイル読み取りとBashコマンド実行を許可
    tools = ["Read", "Bash"]

    async with BedrockAgentSDKWithClient(tools=tools) as agent:
        async for message in agent.chat_with_client(
            "README.mdを読んで、プロジェクト構造を分析して"
        ):
            print(message)

anyio.run(main)
```

## 利用可能なツール

Claude Agent SDKは以下の組み込みツールを提供：

- **Read**: ファイルシステムからファイルを読み取る
- **Write**: ファイルシステムにファイルを書き込む
- **Bash**: bashコマンドを実行
- **Edit**: 既存ファイルを編集
- **Glob**: パターンでファイルを検索
- **Grep**: ファイル内容を検索

**ツールの有効化方法:**

`BedrockAgentSDKWithClient`を使用し、初期化時に`tools`を指定：

```python
tools = ["Read", "Write", "Bash"]
async with BedrockAgentSDKWithClient(tools=tools) as agent:
    async for message in agent.chat_with_client(prompt):
        print(message)
```

**重要**: `BedrockAgentSDK`の`chat_streaming()`メソッドは`tools`パラメータを受け取りますが、内部的には使用されません。ツール機能が必要な場合は、`BedrockAgentSDKWithClient`を使用してください。

## プロジェクト構造

```
.
├── src/
│   ├── __init__.py          # パッケージ初期化
│   ├── agent.py             # Claude Agent SDK実装
│   └── examples.py          # 使用例
├── pyproject.toml           # UVプロジェクト設定
├── Makefile                 # ビルド・実行コマンド
├── .env.example             # 環境変数テンプレート
└── README.md                # このファイル
```

## 利用可能なMakeコマンド

```bash
make help           # 利用可能なコマンドを表示
make install        # 依存関係をインストール
make sync           # 依存関係を同期（インストール + 更新）
make run            # サンプルを実行（Claude Agent SDK）
make shell          # IPythonシェルを起動
make clean          # キャッシュファイルを削除
make setup          # 初回セットアップ

# Prompt Caching 実験
make cache-test     # 基本的なキャッシュテスト
make cache-compare  # キャッシュあり・なし比較
make cache-metrics  # CloudWatch メトリクス確認
```

## Langfuseでの監視

すべてのエージェントインタラクションがLangfuseで自動的に追跡されます：

1. https://cloud.langfuse.com にアクセス
2. プロジェクトに移動
3. 以下を含むトレースを表示：
   - 完全な会話履歴
   - ツール使用イベント
   - トークン数（利用可能な場合）
   - レイテンシメトリクス
   - エラートラッキング

各エージェントメソッドは`@observe()`でデコレートされ、自動トレーシングが有効になっています。

## 違い: Agent SDK vs Anthropic SDK

| 機能 | Claude Agent SDK | Anthropic SDK |
|------|------------------|---------------|
| **レベル** | 高レベルエージェントフレームワーク | 低レベルAPIクライアント |
| **エージェントループ** | 自動 | 手動実装 |
| **ツール管理** | 組み込み | 手動 |
| **状態管理** | 組み込み | 手動 |
| **コード実行** | 組み込み | 外部 |
| **複雑度** | 高い抽象化 | 低い抽象化 |
| **用途** | 自律的エージェント | シンプルなAPI呼び出し |

## トラブルシューティング

### "Could not connect to Bedrock"

- AWS認証情報が正しいか確認
- Bedrockがリージョンで有効になっているか確認
- Bedrockコンソールでモデルアクセスが許可されているか確認
- `CLAUDE_CODE_USE_BEDROCK=1`が設定されているか確認

### "Langfuse authentication failed"

- APIキーが正しいか確認
- `LANGFUSE_HOST`が`https://cloud.langfuse.com`に設定されているか確認
- PUBLIC_KEYとSECRET_KEYを使用しているか確認（APIキーではない）

### "Module not found"エラー

```bash
# 依存関係を再インストール
make clean
make install
```

### "CLI not found"エラー

Claude Agent SDKはClaude Code CLIを自動的にバンドルします。このエラーが表示される場合：
- `claude-agent-sdk`が正しくインストールされているか確認
- 再インストールを試す: `uv pip install --force-reinstall claude-agent-sdk`

## 含まれるサンプル

プロジェクトには4つのサンプルシナリオが含まれます：

1. **シンプルクエリ** (`example_simple_query`) - 基本的な一回限りのクエリ（ツールなし）
2. **ストリーミングチャット** (`example_streaming_chat`) - リアルタイムストリーミングレスポンス（ツールなし）
3. **非ストリーミングチャット** (`example_non_streaming_chat`) - 完全なレスポンスを収集（ツールなし）
4. **ClaudeSDKClientでツールを使用** (`example_with_client`) - Writeツールを使ってファイルを作成

**注意**: ツール機能（Read、Write、Bash等）が必要な場合は、必ず`BedrockAgentSDKWithClient`を使用してください。`BedrockAgentSDK`はツールをサポートしていません。

`make run`でサンプルを実行できます！

## 開発

### 対話型シェル

```bash
make shell

# IPythonで
from src.agent import BedrockAgentSDK
import anyio

async def test():
    agent = BedrockAgentSDK()
    response = await agent.chat("こんにちは！")
    print(response)

anyio.run(test)
```

### カスタムツールの追加

デコレーターを使ってカスタムツールを定義できます：

```python
from claude_agent_sdk import tool

@tool
def get_weather(location: str) -> str:
    """指定場所の天気を取得"""
    return f"{location}の天気: 晴れ、22°C"

# エージェントで使用
async for message in agent.chat_streaming(
    "東京の天気は？",
    tools=[get_weather]
):
    print(message)
```

## リソース

- [Claude Agent SDK ドキュメント](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Claude Agent SDK Python GitHub](https://github.com/anthropics/claude-agent-sdk-python)
- [AWS Bedrock ドキュメント](https://docs.aws.amazon.com/bedrock/)
- [Langfuse ドキュメント](https://langfuse.com/docs)
- [UV ドキュメント](https://github.com/astral-sh/uv)

## 参考資料

- [Agent SDK overview - Claude Docs](https://docs.claude.com/en/api/agent-sdk/overview)
- [Claude Agent SDK Tutorial - DataCamp](https://www.datacamp.com/tutorial/how-to-use-claude-agent-sdk)
- [GitHub - anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python)
- [Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)

## ライセンス

MIT

## コントリビューション

コントリビューションを歓迎します！お気軽にPull Requestを提出してください。
