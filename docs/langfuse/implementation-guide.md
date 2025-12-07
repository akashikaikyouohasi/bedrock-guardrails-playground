# Langfuse トレーシング実装ガイド

このドキュメントでは、Claude Agent SDK と Bedrock を使用したアプリケーションで Langfuse トレーシングを実装する方法を説明します。

## 📖 目次

- [セットアップ](#セットアップ)
- [基本的な実装パターン](#基本的な実装パターン)
- [実装例](#実装例)
- [API リファレンス](#api-リファレンス)
- [エラーハンドリング](#エラーハンドリング)
- [テストとデバッグ](#テストとデバッグ)

## セットアップ

### 1. 依存関係のインストール

```bash
# pyproject.toml に追加済み
uv pip install langfuse>=3.10.5 tiktoken>=0.5.0
```

### 2. 環境変数の設定

`.env` ファイルに Langfuse の認証情報を追加：

```bash
# Langfuse API Keys
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com  # オプション

# AWS Credentials
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Model Configuration
MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
```

### 3. Langfuse クライアントの初期化

```python
from langfuse import get_client

# 環境変数から自動的に読み込まれる
langfuse = get_client()
```

## 基本的な実装パターン

### パターン 1: 手動トレーシング（ストリーミング）

**使用ケース:** ストリーミングレスポンス、詳細なメタデータ記録

```python
async def chat_streaming(
    self,
    prompt: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> AsyncIterator[str]:
    # メタデータの準備
    metadata = {
        "cwd": self.cwd,
        "aws_region": self.aws_region,
        "version": APP_VERSION,
        "streaming": "true",
        "sdk": "claude-agent-sdk",
    }
    if session_id:
        metadata["session_id"] = session_id
    if user_id:
        metadata["user_id"] = user_id

    # Generation 開始
    generation = langfuse.start_generation(
        name="chat_streaming",
        model=self.model,
        input=prompt,
        model_parameters={
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        },
        metadata=metadata,
    )

    full_response = ""
    input_tokens = 0
    output_tokens = 0

    try:
        # トークン推定
        input_tokens = estimate_tokens(prompt)

        # LLM 実行
        async for message in query(prompt=prompt):
            message_text = extract_message_text(message)
            if message_text:
                full_response += message_text
                yield message_text

        # 出力トークン推定
        output_tokens = estimate_tokens(full_response)

        # Generation 更新
        generation.update(
            output=full_response,
            usage_details={
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens,
            },
            metadata={
                "message_count": 1,
                "response_length": len(full_response),
            },
        )

    except Exception as e:
        generation.update(
            level="ERROR",
            status_message=str(e),
        )
        raise

    finally:
        # Generation 終了
        generation.end()
        langfuse.flush()
```

### パターン 2: デコレータトレーシング（非ストリーミング）

**使用ケース:** シンプルな実装、非ストリーミング

```python
from langfuse import observe

@observe(as_type="generation")
async def chat(
    self,
    prompt: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    # メタデータの準備
    metadata = {
        "cwd": self.cwd,
        "aws_region": self.aws_region,
        "version": APP_VERSION,
        "streaming": "false",
        "sdk": "claude-agent-sdk",
    }
    if session_id:
        metadata["session_id"] = session_id
    if user_id:
        metadata["user_id"] = user_id

    # Langfuse コンテキスト更新
    langfuse.update_current_generation(
        model=self.model,
        input=prompt,
        model_parameters={
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        },
        metadata=metadata,
    )

    full_response = ""
    input_tokens = 0
    output_tokens = 0

    try:
        input_tokens = estimate_tokens(prompt)

        async for message in query(prompt=prompt):
            message_text = extract_message_text(message)
            if message_text:
                full_response += message_text + "\n"

        output_tokens = estimate_tokens(full_response)

    except Exception as e:
        langfuse.update_current_generation(
            level="ERROR",
            status_message=str(e),
        )
        raise

    # 最終更新
    langfuse.update_current_generation(
        output=full_response.strip(),
        usage_details={
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens,
        },
        metadata={
            "message_count": 1,
            "response_length": len(full_response),
        },
    )

    return full_response.strip()
```

## 実装例

### 例 1: シンプルなチャット

```python
from src.agent import BedrockAgentSDK

async def main():
    # エージェント初期化
    agent = BedrockAgentSDK(
        model="anthropic.claude-3-5-sonnet-20241022-v2:0",
        temperature=0.7,
        max_tokens=4096,
    )

    # チャット実行（トレース自動記録）
    response = await agent.chat(
        prompt="量子コンピューティングとは何ですか？",
        session_id="session-001",
        user_id="user-123",
    )

    print(response)
```

### 例 2: ストリーミングチャット

```python
from src.agent import BedrockAgentSDK

async def main():
    agent = BedrockAgentSDK()

    print("Assistant: ", end="", flush=True)

    async for chunk in agent.chat_streaming(
        prompt="AIについて説明してください",
        session_id="session-002",
        user_id="user-456",
    ):
        print(chunk, end="", flush=True)

    print("\n")
```

### 例 3: ツール使用

```python
from src.agent import BedrockAgentSDKWithClient

async def main():
    async with BedrockAgentSDKWithClient(
        tools=["Write", "Read"],
        temperature=0.5,
    ) as agent:
        async for chunk in agent.chat_with_client(
            prompt="hello.py を作成してください",
            session_id="session-003",
            user_id="user-789",
        ):
            print(chunk, end="", flush=True)
```

### 例 4: シンプルクエリ関数

```python
from src.agent import simple_query

async def main():
    response = await simple_query(
        prompt="2 + 2 = ?",
        session_id="session-004",
        user_id="user-101",
        temperature=0.0,  # 決定論的な回答
    )
    print(response)
```

## API リファレンス

### `langfuse.start_generation()`

Generation を手動で開始します。

**パラメータ:**

```python
generation = langfuse.start_generation(
    name: str,                              # 必須: Generation の名前
    model: str,                             # 必須: モデル識別子
    input: Any,                             # 必須: 入力プロンプト
    output: Optional[Any] = None,           # オプション: 出力（後で update 可能）
    metadata: Optional[Dict] = None,        # オプション: メタデータ
    model_parameters: Optional[Dict] = None,# オプション: モデルパラメータ
    usage_details: Optional[Dict] = None,   # オプション: トークン使用量
    version: Optional[str] = None,          # オプション: バージョン
    level: Optional[str] = None,            # オプション: ログレベル
    status_message: Optional[str] = None,   # オプション: ステータスメッセージ
)
```

**戻り値:** `LangfuseGeneration` オブジェクト

### `generation.update()`

Generation の情報を更新します。

**パラメータ:**

```python
generation.update(
    output: Optional[Any] = None,           # 出力テキスト
    usage_details: Optional[Dict] = None,   # トークン使用量
    metadata: Optional[Dict] = None,        # 追加メタデータ
    level: Optional[str] = None,            # ログレベル ("ERROR" など)
    status_message: Optional[str] = None,   # エラーメッセージなど
)
```

### `generation.end()`

Generation を終了します。

```python
generation.end()
```

### `langfuse.flush()`

バッファをフラッシュして、すべてのトレースを Langfuse に送信します。

```python
langfuse.flush()
```

### `estimate_tokens()`

テキストのトークン数を推定します（src/agent.py）。

**パラメータ:**

```python
tokens = estimate_tokens(
    text: str,                  # トークン数を推定するテキスト
    model: str = "gpt-4",       # エンコーディングモデル（デフォルト: gpt-4）
)
```

**戻り値:** `int` - 推定トークン数

**実装:**

```python
def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """Estimate token count for given text."""
    if not TIKTOKEN_AVAILABLE:
        # Fallback: rough estimation (1 token ≈ 4 characters)
        return len(text) // 4

    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback if model not found
        return len(text) // 4
```

## エラーハンドリング

### 基本的なエラーハンドリング

```python
generation = langfuse.start_generation(...)

try:
    # LLM 実行
    response = await query(prompt)
    generation.update(output=response)

except Exception as e:
    # エラー情報を記録
    generation.update(
        level="ERROR",
        status_message=str(e),
    )
    raise

finally:
    # 必ず終了処理
    generation.end()
    langfuse.flush()
```

### 特定のエラー処理

```python
from botocore.exceptions import ClientError

try:
    response = await query(prompt)
    generation.update(output=response)

except ClientError as e:
    error_code = e.response['Error']['Code']
    generation.update(
        level="ERROR",
        status_message=f"AWS Error: {error_code}",
        metadata={"error_details": str(e)},
    )
    raise

except TimeoutError:
    generation.update(
        level="WARNING",
        status_message="Request timed out",
    )
    raise

finally:
    generation.end()
    langfuse.flush()
```

### リトライロジック

```python
import asyncio

max_retries = 3
for attempt in range(max_retries):
    generation = langfuse.start_generation(
        name=f"chat_attempt_{attempt + 1}",
        model=self.model,
        input=prompt,
        metadata={"attempt": str(attempt + 1)},
    )

    try:
        response = await query(prompt)
        generation.update(output=response)
        generation.end()
        langfuse.flush()
        return response

    except Exception as e:
        generation.update(
            level="ERROR" if attempt == max_retries - 1 else "WARNING",
            status_message=f"Attempt {attempt + 1} failed: {str(e)}",
        )
        generation.end()
        langfuse.flush()

        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        else:
            raise
```

## テストとデバッグ

### ローカルテスト

```python
# tests/test_tracing.py
import pytest
from src.agent import BedrockAgentSDK

@pytest.mark.asyncio
async def test_chat_with_tracing():
    """トレーシングが正常に動作することを確認"""
    agent = BedrockAgentSDK()

    response = await agent.chat(
        prompt="テストプロンプト",
        session_id="test-session",
        user_id="test-user",
    )

    assert response is not None
    assert len(response) > 0
```

### トレースの確認

Langfuse ダッシュボードでトレースを確認：

1. https://cloud.langfuse.com にログイン
2. プロジェクトを選択
3. "Traces" タブを開く
4. session_id または user_id でフィルタリング

### デバッグモード

```python
import logging

# Langfuse のログを有効化
logging.basicConfig(level=logging.DEBUG)
langfuse_logger = logging.getLogger("langfuse")
langfuse_logger.setLevel(logging.DEBUG)
```

### トレースの検証

```python
from langfuse import get_client

langfuse = get_client()

# トレースが送信されたことを確認
langfuse.flush()

# プログラム終了前に必ず flush を呼ぶ
import atexit
atexit.register(langfuse.flush)
```

## ベストプラクティス

### 1. 常に flush を呼ぶ

```python
try:
    # 処理
    pass
finally:
    langfuse.flush()
```

### 2. メタデータの一貫性

```python
# 共通のメタデータを定義
def get_base_metadata():
    return {
        "aws_region": os.getenv("AWS_REGION"),
        "version": APP_VERSION,
        "environment": os.getenv("ENVIRONMENT", "development"),
    }

metadata = get_base_metadata()
metadata.update({"custom_field": "value"})
```

### 3. session_id の生成

```python
import uuid

# セッション開始時に生成
session_id = str(uuid.uuid4())

# 会話全体で同じ session_id を使用
for prompt in prompts:
    await agent.chat(
        prompt=prompt,
        session_id=session_id,
        user_id=user_id,
    )
```

### 4. トークン推定の精度向上

```python
# Claude モデル用の推定関数（将来的に改善可能）
def estimate_tokens_claude(text: str) -> int:
    # Claude 固有の推定ロジック
    # 現在は GPT-4 エンコーディングを使用
    return estimate_tokens(text, model="gpt-4")
```

## 次のステップ

- [ベストプラクティス](./best-practices.md) - 運用のベストプラクティスを確認
- [トレーシング概要](./tracing-overview.md) - 基本概念を復習

## 参考リソース

- [Langfuse Python SDK](https://langfuse.com/docs/observability/sdk/python/overview)
- [tiktoken](https://github.com/openai/tiktoken)
- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)
