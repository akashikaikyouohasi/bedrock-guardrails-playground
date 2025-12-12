# AWS Bedrock Prompt Caching ガイド

## 概要

Amazon Bedrock Prompt Caching は、頻繁に使用されるプロンプトをキャッシュすることで、**レイテンシを最大 85%、コストを最大 90% 削減**できる機能です。

**東京リージョン（ap-northeast-1）対応済み** ✅

```
┌─────────────────────────────────────────────────────────────┐
│                    Prompt Caching の仕組み                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  リクエスト 1（初回）                                        │
│  ┌──────────────────────────────────────────┐              │
│  │ [System Prompt] [Context] [User Query 1] │              │
│  │        ↓                                 │              │
│  │    キャッシュに書き込み（Write）+25%     │              │
│  └──────────────────────────────────────────┘              │
│                                                             │
│  リクエスト 2〜N（同一プレフィックス、5分以内）               │
│  ┌──────────────────────────────────────────┐              │
│  │ [System Prompt] [Context] [User Query N] │              │
│  │        ↓                                 │              │
│  │    キャッシュから読み込み（Read）90%OFF  │              │
│  └──────────────────────────────────────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 対応モデル

### Claude 4.5 シリーズ（最新）

| モデル | モデル ID | 最小トークン | 日本語換算（目安） | 最大チェックポイント |
|--------|----------|-------------|-------------------|-------------------|
| **Claude Opus 4.5** | anthropic.claude-opus-4-5-* | **4,096** | 約 8,000〜12,000 文字 | 4 |
| **Claude Sonnet 4.5** | anthropic.claude-sonnet-4-5-* | **1,024** | 約 2,000〜3,000 文字 | 4 |
| **Claude Haiku 4.5** | anthropic.claude-haiku-4-5-* | **4,096** | 約 8,000〜12,000 文字 | 4 |

**日本語文字数の計算**:
- 1 トークン ≈ 2〜3 文字（日本語の場合）
- 例: 1,024 トークン ≈ 2,000〜3,000 文字程度

### Claude 4.0 / 3.x シリーズ

| モデル | モデル ID | 最小トークン | 日本語換算（目安） | 最大チェックポイント |
|--------|----------|-------------|-------------------|-------------------|
| **Claude 3.7 Sonnet** | anthropic.claude-3-7-sonnet-20250219-v1:0 | 1,024 | 約 2,000〜3,000 文字 | 4 |
| **Claude 3.5 Haiku** | anthropic.claude-3-5-haiku-20241022-v1:0 | 2,048 | 約 4,000〜6,000 文字 | 4 |
| **Claude Sonnet 4** | anthropic.claude-sonnet-4-20250514-v1:0 | 1,024 | 約 2,000〜3,000 文字 | 4 |
| **Claude Opus 4** | anthropic.claude-opus-4-20250514-v1:0 | 1,024 | 約 2,000〜3,000 文字 | 4 |

### キャッシュ対象

| フィールド | 対応 | 説明 |
|-----------|------|------|
| `system` | ✅ | システムプロンプト |
| `messages` | ✅ | 会話履歴、ドキュメント等 |
| `tools` | ✅ | ツール定義 |

---

## キャッシュの仕様

### 基本仕様

| 項目 | 値 |
|------|-----|
| **TTL（有効期限）** | 5 分（固定） |
| **TTL リセット** | キャッシュヒット時に 5 分延長 |
| **最大チェックポイント** | リクエストあたり 4 個 |
| **最小トークン数** | モデル依存 |
| - Claude Sonnet 4.5 | 1,024 トークン（約 2,000〜3,000 文字） |
| - Claude Opus 4.5 | 4,096 トークン（約 8,000〜12,000 文字） |
| - Claude Haiku 4.5 | 4,096 トークン（約 8,000〜12,000 文字） |

### キャッシュヒットの条件

```
✅ キャッシュヒット:
   - プレフィックス（静的部分）が完全に同一
   - TTL 内（5分以内、または継続的にアクセス）

❌ キャッシュミス:
   - プレフィックスに 1 文字でも変更がある
   - TTL 超過（5分以上アクセスなし）
```

### 料金

| トークン種別 | 料金（標準比） | 説明 |
|-------------|---------------|------|
| **キャッシュ書き込み** | +25% | 初回処理時 |
| **キャッシュ読み取り** | **-90%** | 再利用時（大幅削減） |

### コスト効果の計算例

```
前提: 10,000 トークンのシステムプロンプト、100 回のリクエスト

【キャッシュなし】
  10,000 × 100 = 1,000,000 トークン（標準料金）

【キャッシュあり】
  初回: 10,000 × 1.25 = 12,500 トークン相当
  2回目以降: 10,000 × 0.10 × 99 = 99,000 トークン相当
  合計: 111,500 トークン相当

  削減率: 約 89%
```

---

## AWS Bedrock の自動キャッシュ機能

### InvokeModel API によるデフォルト有効化

**重要: AWS Bedrock では Prompt Caching がデフォルトで有効です！** 🎉

AWS の公式ドキュメントによると：

> **InvokeModel API を呼び出すと、プロンプトキャッシュがデフォルトで有効になります**

つまり、特別な設定や `cache_control` の手動設定は不要で、以下の条件を満たせば自動的にキャッシュが有効になります：

```
✅ 自動キャッシュの条件:
1. 最小トークン数を満たす（モデルによって 1,024〜4,096 トークン）
2. プレフィックス（静的部分）が同一
3. TTL 内（5分以内にリクエスト）
```

参考リンク：https://docs.aws.amazon.com/ja_jp/bedrock/latest/userguide/prompt-caching.html

### 手動設定との違い

| 方法 | 説明 | 推奨 |
|------|------|------|
| **自動（Bedrock デフォルト）** | InvokeModel API が自動的に最適なキャッシュポイントを設定 | ✅ 推奨（ほとんどのケース） |
| **手動（cache_control）** | `cache_control: {"type": "ephemeral"}` を明示的に設定 | 特定の最適化が必要な場合のみ |

**ほとんどのユースケースでは、自動キャッシュで十分な効果が得られます。**

### 確認方法

Bedrock のログ（CloudWatch Logs）で以下のフィールドを確認できます：

```json
{
  "input": {
    "inputTokenCount": 2,
    "cacheReadInputTokenCount": 14401,  // キャッシュから読み込まれたトークン
    "cacheWriteInputTokenCount": 0      // キャッシュに書き込まれたトークン
  }
}
```

`cacheReadInputTokenCount` が 0 より大きければ、キャッシュが効いています。

---

## Claude Agent SDK での利用

### 概要

**重要: Claude Agent SDK では追加の実装は一切不要です！** ✨

Claude Agent SDK は内部で AWS Bedrock の InvokeModel API を使用しているため、Prompt Caching が自動的に有効になります。環境変数を設定するだけで、以下が自動的にキャッシュされます：

- ✅ システムプロンプト（最小トークン数以上の場合）
- ✅ ツール定義
- ✅ 会話コンテキスト

### 必要なのは環境変数の設定だけ

```bash
# .env
CLAUDE_CODE_USE_BEDROCK=1
AWS_REGION=ap-northeast-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

**これだけで完了！コードに特別な変更は不要です。**

### 基本的な使い方

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    # 長いシステムプロンプト
    # Claude Sonnet 4.5: 1,024トークン（約2,000〜3,000文字）以上で自動キャッシュ
    # Claude Opus/Haiku 4.5: 4,096トークン（約8,000〜12,000文字）以上で自動キャッシュ
    system_prompt = """あなたは専門的なカスタマーサポートアシスタントです。

    以下のマニュアルに基づいて回答してください：

    [製品マニュアル]
    第1章: 製品概要
    ...（長いテキスト - 最小トークン数を満たす必要があります）...

    第2章: 基本操作
    ...（長いテキスト）...

    第3章: トラブルシューティング
    ...（長いテキスト）...
    """

    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
    )

    # 1回目のクエリ（キャッシュ書き込み）
    async for message in query(prompt="パスワードのリセット方法は？", options=options):
        print(message)

    # 2回目以降のクエリ（キャッシュ読み取り → 高速・低コスト）
    async for message in query(prompt="返品の手順を教えて", options=options):
        print(message)

asyncio.run(main())
```

### ClaudeSDKClient での利用

`ClaudeSDKClient`（低レベル API）でも同様に、自動的にプロンプトキャッシュが有効になります。

```python
from claude_agent_sdk import ClaudeSDKClient
import asyncio

async def main():
    async with ClaudeSDKClient() as client:
        # 長いシステムプロンプト（自動的にキャッシュされる）
        system_prompt = """あなたは専門的なアシスタントです。
        
        以下のマニュアルに基づいて回答してください：
        [長いドキュメント...]
        """
        
        # 1回目のクエリ（キャッシュ書き込み）
        response1 = await client.create_message(
            system=system_prompt,
            messages=[{"role": "user", "content": "質問1"}],
            max_tokens=1024
        )
        print(response1.content)
        
        # 2回目以降のクエリ（キャッシュ読み取り → 高速・低コスト）
        response2 = await client.create_message(
            system=system_prompt,  # 同じシステムプロンプトでキャッシュが効く
            messages=[{"role": "user", "content": "質問2"}],
            max_tokens=1024
        )
        print(response2.content)

asyncio.run(main())
```

**`query()` 関数も `ClaudeSDKClient` も、内部的には同じBedrockのプロンプトキャッシュ機能を使用しているため、どちらでも同等の効果が得られます。**

### キャッシュ効果を最大化する設計

#### 1. システムプロンプトの構造化

```python
# 推奨: 静的部分を先頭に、動的部分を後方に
system_prompt = """
[静的部分 - キャッシュ対象]
あなたは〇〇のアシスタントです。

以下のルールに従ってください：
1. ...
2. ...

参照ドキュメント：
{長いドキュメント}

[動的部分 - キャッシュ対象外]
現在の日時: {datetime.now()}  # ← これは含めない
"""
```

#### 2. ツール定義のキャッシュ

```python
from claude_agent_sdk import ClaudeAgentOptions, Tool

# ツール定義は自動的にキャッシュされる
tools = [
    Tool(
        name="search_documents",
        description="社内ドキュメントを検索します",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "検索クエリ"}
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="get_user_info",
        description="ユーザー情報を取得します",
        input_schema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "ユーザーID"}
            },
            "required": ["user_id"]
        }
    ),
    # 多くのツールを定義しても、キャッシュにより2回目以降は高速
]

options = ClaudeAgentOptions(
    system_prompt="あなたはツールを使用できるアシスタントです。",
    tools=tools,
)
```

#### 3. セッション管理によるキャッシュ活用

```python
class CachedAgentSession:
    """キャッシュを効果的に活用するセッション管理"""

    def __init__(self, system_prompt: str, tools: list = None):
        self.options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            tools=tools or [],
            permission_mode='acceptEdits',
        )
        self.conversation_history = []

    async def chat(self, user_message: str) -> str:
        """
        同一セッション内での会話はキャッシュが効く
        - システムプロンプト: キャッシュ
        - ツール定義: キャッシュ
        - 会話履歴の共通部分: キャッシュ
        """
        response_text = ""
        async for message in query(
            prompt=user_message,
            options=self.options,
        ):
            if hasattr(message, 'text'):
                response_text += message.text

        return response_text


# 使用例
async def main():
    # セッション開始（システムプロンプトがキャッシュされる）
    session = CachedAgentSession(
        system_prompt="長いシステムプロンプト...",
        tools=[...],
    )

    # 同一セッション内の会話はキャッシュが効く
    await session.chat("質問1")  # キャッシュ書き込み
    await session.chat("質問2")  # キャッシュ読み取り（高速）
    await session.chat("質問3")  # キャッシュ読み取り（高速）
```

---

## ユースケース別パターン

### 1. ドキュメント Q&A（最も効果的）

```
効果: ★★★★★

┌─────────────────────────────────────────────────────────────┐
│  同一ドキュメントに対する複数質問                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [System] + [Document]  ← キャッシュ（1回書き込み）         │
│         ↓                                                   │
│  [User Query 1] → 回答 1                                    │
│  [User Query 2] → 回答 2  ← キャッシュ読み取り              │
│  [User Query 3] → 回答 3  ← キャッシュ読み取り              │
│                                                             │
│  コスト削減: 最大 90%                                        │
└─────────────────────────────────────────────────────────────┘
```

```python
class DocumentQAAgent:
    def __init__(self, document: str):
        self.options = ClaudeAgentOptions(
            system_prompt=f"""あなたはドキュメント分析アシスタントです。
            以下のドキュメントに基づいて質問に回答してください。

            ドキュメント:
            {document}
            """,
        )

    async def ask(self, question: str) -> str:
        result = ""
        async for message in query(prompt=question, options=self.options):
            if hasattr(message, 'text'):
                result += message.text
        return result


# 使用例
async def main():
    # 長いドキュメントをロード
    with open("manual.txt", "r") as f:
        document = f.read()

    qa = DocumentQAAgent(document)

    # 複数の質問（2回目以降はキャッシュで高速・低コスト）
    print(await qa.ask("このドキュメントの概要は？"))
    print(await qa.ask("第3章の内容を要約して"))
    print(await qa.ask("トラブルシューティングの手順は？"))
```

### 2. カスタマーサポートエージェント

```
効果: ★★★★☆

複数ユーザーからの問い合わせに同一ナレッジベースで対応
```

```python
class SupportAgent:
    def __init__(self, knowledge_base: str, tools: list):
        self.options = ClaudeAgentOptions(
            system_prompt=f"""あなたはカスタマーサポートエージェントです。

            回答ルール:
            1. 丁寧な敬語を使用
            2. 不明な点は確認を促す
            3. 必要に応じてツールを使用

            ナレッジベース:
            {knowledge_base}
            """,
            tools=tools,
        )

    async def handle_inquiry(self, user_id: str, message: str) -> str:
        # 各ユーザーの問い合わせでキャッシュが効く
        # - システムプロンプト: キャッシュ
        # - ナレッジベース: キャッシュ
        # - ツール定義: キャッシュ
        result = ""
        async for msg in query(prompt=message, options=self.options):
            if hasattr(msg, 'text'):
                result += msg.text
        return result
```

### 3. コードレビューエージェント

```
効果: ★★★★☆

同一プロジェクトの複数ファイルをレビュー
```

```python
class CodeReviewAgent:
    def __init__(self, coding_guidelines: str):
        self.options = ClaudeAgentOptions(
            system_prompt=f"""あなたはシニアソフトウェアエンジニアです。
            以下のコーディングガイドラインに基づいてレビューしてください。

            ガイドライン:
            {coding_guidelines}

            レビュー観点:
            - セキュリティ
            - パフォーマンス
            - 可読性
            - テスト容易性
            """,
        )

    async def review(self, code: str, filename: str) -> str:
        prompt = f"ファイル: {filename}\n\n```\n{code}\n```\n\nこのコードをレビューしてください。"
        result = ""
        async for msg in query(prompt=prompt, options=self.options):
            if hasattr(msg, 'text'):
                result += msg.text
        return result


# 使用例: 複数ファイルのレビュー（ガイドラインはキャッシュ）
async def review_project():
    with open("coding_guidelines.md", "r") as f:
        guidelines = f.read()

    reviewer = CodeReviewAgent(guidelines)

    files = ["main.py", "utils.py", "api.py", "models.py"]
    for filename in files:
        with open(filename, "r") as f:
            code = f.read()
        review = await reviewer.review(code, filename)
        print(f"=== {filename} ===\n{review}\n")
```

---

## ベストプラクティス

### キャッシュ効果を高める設計

```
✅ 推奨:
├── 静的コンテンツを先頭に配置
│   └── System Prompt → Document → Tools → User Query
├── 最小トークン数（1,024）以上の静的部分を確保
├── 5分以内に複数リクエストを送信するユースケース
├── 同一ドキュメント/ナレッジベースへの複数質問
└── セッション内での連続会話

❌ 避けるべき:
├── 動的コンテンツを先頭に配置
│   └── 例: 現在時刻、ランダム値を System Prompt の先頭に
├── 静的部分が少ない（1,024トークン未満）
├── リクエスト間隔が5分以上空く
└── 毎回異なるコンテキスト
```

### キャッシュミスを避ける

```python
# ❌ 悪い例: 動的な値が先頭にある
system_prompt = f"""
現在時刻: {datetime.now()}  # ← 毎回変わるのでキャッシュミス
あなたはアシスタントです。
{長いドキュメント}
"""

# ✅ 良い例: 静的な値を先頭に
system_prompt = f"""
あなたはアシスタントです。
{長いドキュメント}
"""
# 現在時刻はユーザーメッセージに含める
user_message = f"現在時刻は {datetime.now()} です。質問: ..."
```

---

## このプロジェクトでの実装例

### BedrockAgentSDK との統合

このプロジェクトの `BedrockAgentSDK` クラスでも、Prompt Caching が自動的に有効になります。

```python
# src/agent.py を使用
from src.agent import BedrockAgentSDK
import asyncio

async def main():
    # 長いシステムプロンプトを持つエージェント
    agent = BedrockAgentSDK(
        system_prompt="""あなたは AWS Bedrock Guardrails の専門家です。

        以下のドキュメントに基づいて回答してください：

        [Guardrails 詳細ドキュメント - 長いテキスト...]
        """,
        model_id="anthropic.claude-3-7-sonnet-20250219-v1:0"
    )

    # 複数の質問（システムプロンプトはキャッシュされる）
    response1 = await agent.chat(
        prompt="Guardrails の設定方法は？",
        session_id="user-123",
        user_id="user-123"
    )
    print(response1)

    response2 = await agent.chat(
        prompt="ApplyGuardrail API の使い方は？",
        session_id="user-123",
        user_id="user-123"
    )
    print(response2)  # ← キャッシュが効いて高速・低コスト

asyncio.run(main())
```

### Guardrails と Prompt Caching の組み合わせ

```python
from src.agent import BedrockAgentSDKWithClient
from terraform.examples.streaming_example import AgentSDKWithApplyGuardrail
import asyncio

async def main():
    # Guardrails 統合エージェント + Prompt Caching
    agent = AgentSDKWithApplyGuardrail(
        guardrail_id="your-guardrail-id",
        guardrail_version="DRAFT",
        enable_input_check=True,
        enable_output_check=True,
    )

    # 長いシステムプロンプトを設定
    agent.system_prompt = """あなたは安全性を重視したアシスタントです。

    以下のポリシーに従ってください：
    [長いポリシードキュメント...]
    """

    # 複数のユーザーからの問い合わせ
    # システムプロンプトとガードレール設定がキャッシュされる
    for user_id in ["user-1", "user-2", "user-3"]:
        response = await agent.chat_streaming(
            prompt=f"ユーザー {user_id} からの質問",
            realtime_check_interval=100
        )
        print(f"User {user_id}: {response}")

asyncio.run(main())
```

**メリット:**
- システムプロンプト + ポリシードキュメント: キャッシュで高速化
- Guardrails チェック: 安全性を担保
- コスト削減: 90% の削減効果

---

## キャッシュが効いているかの確認方法

### CloudWatch メトリクスでの確認

AWS CloudWatch を使用して、Prompt Caching の効果を確認できます。

#### 確認手順

1. **CloudWatch コンソールにアクセス**
   - AWS コンソール → CloudWatch → メトリクス

2. **Bedrock メトリクスを選択**
   - 「AWS/Bedrock」名前空間を選択
   - 「ModelId」でフィルタリング

3. **以下のメトリクスを確認**

| メトリクス名 | 説明 |
|------------|------|
| `InputTokens` | 入力トークン総数 |
| `CacheReadInputTokens` | キャッシュから読み取られたトークン数 ✅ |
| `CacheWriteInputTokens` | キャッシュに書き込まれたトークン数 |

#### キャッシュヒット率の計算

```
キャッシュヒット率 = CacheReadInputTokens / InputTokens × 100%

例:
  InputTokens: 100,000
  CacheReadInputTokens: 80,000
  → キャッシュヒット率: 80%
```

### コンソールでの確認例

```bash
# AWS CLI でメトリクスを取得
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

### プログラムでの確認（boto3）

```python
import boto3
from datetime import datetime, timedelta

def check_cache_metrics(model_id: str):
    """Prompt Caching メトリクスを確認"""
    cloudwatch = boto3.client('cloudwatch', region_name='ap-northeast-1')

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)

    # キャッシュ読み取りトークン数
    cache_read = cloudwatch.get_metric_statistics(
        Namespace='AWS/Bedrock',
        MetricName='CacheReadInputTokens',
        Dimensions=[{'Name': 'ModelId', 'Value': model_id}],
        StartTime=start_time,
        EndTime=end_time,
        Period=3600,
        Statistics=['Sum']
    )

    # 入力トークン総数
    input_tokens = cloudwatch.get_metric_statistics(
        Namespace='AWS/Bedrock',
        MetricName='InputTokens',
        Dimensions=[{'Name': 'ModelId', 'Value': model_id}],
        StartTime=start_time,
        EndTime=end_time,
        Period=3600,
        Statistics=['Sum']
    )

    # Datapoints をソートして最新を取得
    cache_read_points = sorted(cache_read.get('Datapoints', []),
                               key=lambda x: x['Timestamp'], reverse=True)
    input_points = sorted(input_tokens.get('Datapoints', []),
                         key=lambda x: x['Timestamp'], reverse=True)

    if cache_read_points and input_points:
        cache_read_sum = cache_read_points[0]['Sum']
        input_tokens_sum = input_points[0]['Sum']

        if input_tokens_sum > 0:
            cache_hit_rate = (cache_read_sum / input_tokens_sum) * 100
            cost_reduction = cache_read_sum * 0.9 / input_tokens_sum * 100

            print(f"モデル: {model_id}")
            print(f"入力トークン総数: {input_tokens_sum:,.0f}")
            print(f"キャッシュ読み取り: {cache_read_sum:,.0f}")
            print(f"キャッシュヒット率: {cache_hit_rate:.2f}%")
            print(f"コスト削減率: 約 {cost_reduction:.1f}%")
        else:
            print("入力トークンがありません")
    else:
        print("メトリクスデータが見つかりません（過去1時間にリクエストがない可能性があります）")


# 使用例
check_cache_metrics("anthropic.claude-3-7-sonnet-20250219-v1:0")
```

### 実行結果の例

```
モデル: anthropic.claude-3-7-sonnet-20250219-v1:0
入力トークン総数: 150,000
キャッシュ読み取り: 120,000
キャッシュヒット率: 80.00%
コスト削減率: 約 67.0%

💡 キャッシュが効いています！
   - キャッシュ書き込み: 30,000 トークン × 1.25 = 37,500 相当
   - キャッシュ読み取り: 120,000 トークン × 0.10 = 12,000 相当
   - 総コスト: 49,500 トークン相当（元: 150,000）
   - 削減効果: 100,500 トークン（約 67% 削減）
```

### ログベースでの確認

AWS Bedrock のモデル呼び出しログ（CloudWatch Logs または S3）を有効にしている場合、リクエスト/レスポンスの詳細を確認できます。

```json
{
  "schemaType": "ModelInvocationLog",
  "accountId": "123456789012",
  "identity": {
    "arn": "arn:aws:iam::123456789012:user/example"
  },
  "modelId": "anthropic.claude-3-7-sonnet-20250219-v1:0",
  "input": {
    "inputContentType": "application/json",
    "inputTokenCount": 10000
  },
  "output": {
    "outputContentType": "application/json",
    "outputTokenCount": 500
  },
  "metadata": {
    "cacheReadInputTokenCount": 9000,  // ← キャッシュヒット！
    "cacheWriteInputTokenCount": 0
  }
}
```

---

## 制限事項

| 制限 | 内容 |
|------|------|
| **TTL 固定** | 5分（変更不可） |
| **最大チェックポイント** | リクエストあたり 4 個 |
| **最小トークン数** | モデル依存（1,024〜2,048） |

### Anthropic 直接 API との違い

| 項目 | Bedrock | Anthropic API |
|------|---------|---------------|
| TTL | 5分（固定） | 5分 or 1時間（選択可） |
| 料金 | キャッシュ書き込み +25% | 同様 |

---

## データレジデンシー

```
✅ 東京リージョン（ap-northeast-1）対応済み

   日本国内データレジデンシー要件を満たしながら
   Prompt Caching を利用可能です。
```

---

## まとめ

### Prompt Caching を活用すべきユースケース

| ユースケース | 効果 | 理由 |
|------------|------|------|
| **ドキュメント Q&A** | ★★★★★ | 同一ドキュメントへの複数質問で最大効果 |
| **カスタマーサポート** | ★★★★★ | 共通ナレッジベース + 複数ユーザー対応 |
| **コードレビュー** | ★★★★☆ | ガイドライン固定 + 複数ファイル処理 |
| **チャットボット** | ★★★★☆ | システムプロンプト固定 + 連続会話 |
| **エージェント（ツール多数）** | ★★★★☆ | ツール定義がキャッシュされる |

### チェックリスト

```
✅ 環境変数の設定
   └─ CLAUDE_CODE_USE_BEDROCK=1
   └─ AWS_REGION=ap-northeast-1

✅ システムプロンプトの最適化
   └─ 静的部分を先頭に配置
   └─ 1,024 トークン以上確保

✅ キャッシュ効果の確認
   └─ CloudWatch メトリクスで確認
   └─ CacheReadInputTokens をモニタリング

✅ コスト削減の実感
   └─ 2回目以降のリクエストで高速化
   └─ 最大 90% のコスト削減
```

### 次のステップ

1. **環境変数を設定**
   ```bash
   # .env
   CLAUDE_CODE_USE_BEDROCK=1
   AWS_REGION=ap-northeast-1
   ```

2. **既存コードを確認**
   - システムプロンプトが 1,024 トークン以上あるか
   - 静的コンテンツが先頭にあるか

3. **CloudWatch で効果測定**
   - `CacheReadInputTokens` メトリクスを確認
   - キャッシュヒット率を計測

4. **必要に応じて最適化**
   - システムプロンプトの再構成
   - セッション管理の導入

---

## 参考リンク

- [AWS Bedrock Prompt Caching 公式ドキュメント](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)
- [Anthropic Prompt Caching 公式ドキュメント](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) - Claude 4.5 モデルの最小トークン数仕様
- [AWS Blog: Effectively use prompt caching on Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/effectively-use-prompt-caching-on-amazon-bedrock/)
- [Claude Agent SDK Documentation](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [CloudWatch メトリクス](https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-cw.html)
