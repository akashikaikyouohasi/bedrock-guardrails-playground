# Claude Agent SDK with Bedrock & Langfuse

このプロジェクトは、**Claude Agent SDK**（公式エージェントフレームワーク）をAmazon BedrockをLLMプロバイダーとして使用し、Langfuseで監視する方法を示します。

## Claude Agent SDKとは？

Claude Agent SDKは、AnthropicのAIエージェント構築用公式フレームワークです。基本的なAnthropic APIクライアントとは異なり、Agent SDKは以下を提供します：

- **自律的なエージェントループ** - エージェントが自動的にツールを使用し、推論し、反復できる
- **組み込みツール管理** - Pythonデコレーターでツールを定義
- **ストリーミングレスポンス** - エージェントとのリアルタイムインタラクション
- **ファイル操作とコード実行** - 組み込み機能
- **状態管理** - マルチターン会話の処理

## アーキテクチャ

```
Your App → Claude Agent SDK → AWS Bedrock → Claude Models
                ↓
           Langfuse (監視)
```

## 機能

- **Claude Agent SDK**: Anthropic公式エージェントフレームワーク
- **AWS Bedrockバックエンド**: AWS Bedrock経由でClaudeモデルを使用
- **ストリーミングレスポンス**: リアルタイムのエージェントインタラクション
- **Langfuse統合**: 完全な観測性とトレーシング
- **ツールサポート**: Read、Write、Bash、カスタムツール
- **UVパッケージマネージャー**: 高速でモダンなPythonパッケージ管理

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
AWS_REGION=us-east-1

# Claude Agent SDK - Bedrockモードを有効化
CLAUDE_CODE_USE_BEDROCK=1

# Langfuse認証情報（https://cloud.langfuse.com から取得）
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# オプション: 使用するClaudeモデルを指定
# デフォルト: anthropic.claude-3-5-sonnet-20241022-v2:0
ANTHROPIC_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
```

### 4. サンプルの実行

```bash
# Claude Agent SDKサンプルを実行
make run

# または直接実行
uv run python src/examples.py
```

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

### 例3: ツールを使うエージェント

```python
import anyio
from agent import BedrockAgentSDK

async def main():
    agent = BedrockAgentSDK()

    # エージェントにファイル読み取りとbashコマンド実行を許可
    tools = ["Read", "Bash"]

    async for message in agent.chat_streaming(
        "ファイル一覧を表示して、プロジェクト構造を分析して",
        tools=tools
    ):
        print(message)

anyio.run(main)
```

### 例4: ClaudeSDKClientの使用（高度）

```python
import anyio
from agent import BedrockAgentSDKWithClient

async def main():
    async with BedrockAgentSDKWithClient() as agent:
        async for message in agent.chat_with_client(
            "Hello Worldを出力するPythonスクリプトを作成して",
            tools=["Write"]
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

`tools`パラメータに渡すことでツールを有効化：

```python
tools = ["Read", "Write", "Bash"]
await agent.chat_streaming(prompt, tools=tools)
```

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
make help       # 利用可能なコマンドを表示
make install    # 依存関係をインストール
make sync       # 依存関係を同期（インストール + 更新）
make run        # サンプルを実行（Claude Agent SDK）
make shell      # IPythonシェルを起動
make clean      # キャッシュファイルを削除
make setup      # 初回セットアップ
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

プロジェクトには7つのサンプルシナリオが含まれます：

1. **シンプルクエリ** - 基本的な一回限りのクエリ
2. **ストリーミングチャット** - リアルタイムストリーミングレスポンス
3. **非ストリーミングチャット** - 完全なレスポンスを収集
4. **ツールを使うエージェント** - ReadとBashツールの使用
5. **ClaudeSDKClient** - 高度なクライアント使用
6. **コード実行** - コードを書いて実行するエージェント
7. **ファイル読み取り** - プロジェクトファイルを読むエージェント

`make run`ですべて実行できます！

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
