"""
Claude Agent SDK + Bedrock Guardrails ストリーミング処理の実装例

このスクリプトは、Claude Agent SDKとboto3を使用してBedrock Guardrailsを
適用したストリーミング処理の実装方法を示します。

参考: 
- Claude Agent SDK: https://platform.claude.com/docs/ja/agent-sdk/python
- Bedrock boto3: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime.html
"""

import os
import asyncio
import json
from typing import Iterator, Dict, Any
from dotenv import load_dotenv
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, TextBlock, ResultMessage
import boto3

# 環境変数を読み込み
load_dotenv()


def setup_bedrock_env():
    """Bedrock環境変数をセットアップ"""
    # Bedrockモードを有効化
    os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"
    
    # AWS認証情報を設定
    if os.getenv("AWS_ACCESS_KEY_ID"):
        os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
    if os.getenv("AWS_SECRET_ACCESS_KEY"):
        os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
    if os.getenv("AWS_REGION"):
        os.environ["AWS_REGION"] = os.getenv("AWS_REGION")


class AgentSDKWithApplyGuardrail:
    """
    Claude Agent SDK + ApplyGuardrail API を組み合わせた実装
    
    このクラスは以下の機能を提供します：
    1. 入力チェック: ユーザー入力を apply_guardrail でフィルタリング
    2. Agent SDK: ツール使用や会話継続などの高度な機能
    3. 出力チェック: Agent の応答を apply_guardrail でフィルタリング
    
    参考: https://dev.classmethod.jp/articles/filtering-non-generative-ai-apps-with-amazon-bedrock-guardrails-apply-guardrail-api/
    """
    
    def __init__(
        self,
        guardrail_id: str = None,
        guardrail_version: str = "DRAFT",
        aws_region: str = None,
        model: str = "sonnet",
        allowed_tools: list = None,
        enable_input_filtering: bool = True,
        enable_output_filtering: bool = True
    ):
        """
        Args:
            guardrail_id: Bedrock GuardrailのID（オプション）
            guardrail_version: Guardrailのバージョン（デフォルト: DRAFT）
            aws_region: AWSリージョン（デフォルト: 環境変数 AWS_REGION）
            model: 使用するClaudeモデル（sonnet/opus/haiku）
            allowed_tools: 許可するツールのリスト
            enable_input_filtering: 入力フィルタリングを有効化
            enable_output_filtering: 出力フィルタリングを有効化
        """
        self.guardrail_id = guardrail_id or os.getenv("BEDROCK_GUARDRAIL_ID")
        self.guardrail_version = guardrail_version
        self.aws_region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        self.model = model
        self.allowed_tools = allowed_tools or ["Read", "Write"]
        self.enable_input_filtering = enable_input_filtering
        self.enable_output_filtering = enable_output_filtering
        
        # Bedrock Runtimeクライアント（ApplyGuardrail API用）
        self.bedrock_runtime = boto3.client(
            "bedrock-runtime",
            region_name=self.aws_region
        )
        
        # Bedrock環境をセットアップ
        setup_bedrock_env()
        
        self.options = ClaudeAgentOptions(
            model=self.model,
            allowed_tools=self.allowed_tools,
            permission_mode="acceptEdits"
        )
    
    def apply_guardrail(self, text: str, source: str = "INPUT") -> Dict[str, Any]:
        """
        ApplyGuardrail API を使用してテキストをチェック
        
        Args:
            text: チェックするテキスト
            source: "INPUT" または "OUTPUT"
        
        Returns:
            {
                "action": "NONE" | "GUARDRAIL_INTERVENED",
                "filtered_text": str,  # フィルタリング後のテキスト
                "assessments": [...],  # 評価結果
                "is_blocked": bool     # ブロックされたかどうか
            }
        """
        response = self.bedrock_runtime.apply_guardrail(
            guardrailIdentifier=self.guardrail_id,
            guardrailVersion=self.guardrail_version,
            source=source,
            content=[{"text": {"text": text}}]
        )
        
        # 結果を処理
        action = response.get("action", "NONE")
        is_blocked = action == "GUARDRAIL_INTERVENED"
        
        # OUTPUT で outputs が空の場合は元のテキストを使用
        if source == "OUTPUT" and len(response.get("outputs", [])) > 0:
            filtered_text = response["outputs"][0]["text"]
        else:
            filtered_text = text
        
        return {
            "action": action,
            "filtered_text": filtered_text,
            "assessments": response.get("assessments", []),
            "is_blocked": is_blocked,
            "raw_response": response
        }
    
    async def chat_streaming(self, prompt: str):
        """
        ApplyGuardrail API + Claude Agent SDK でストリーミング処理
        
        処理フロー:
        1. INPUT チェック: プロンプトをフィルタリング
        2. Agent SDK: Claude Agent SDK で応答生成
        3. OUTPUT チェック: 応答をフィルタリング
        """
        
        print("\n" + "="*80)
        print("【Claude Agent SDK + ApplyGuardrail API ストリーミング開始】")
        print("="*80)
        print(f"プロンプト: {prompt[:100]}...")
        print(f"モデル: {self.model}")
        if self.guardrail_id:
            print(f"Guardrail ID: {self.guardrail_id}")
            print(f"Guardrail Version: {self.guardrail_version}")
            print(f"入力フィルタリング: {'有効' if self.enable_input_filtering else '無効'}")
            print(f"出力フィルタリング: {'有効' if self.enable_output_filtering else '無効'}")
        else:
            print("Guardrail: 未設定")
        print()
        
        # ステップ1: INPUT チェック
        if self.enable_input_filtering and self.guardrail_id:
            print("🛡️ ステップ1: 入力をチェック中...")
            input_result = self.apply_guardrail(prompt, source="INPUT")
            
            if input_result["is_blocked"]:
                print("🚫 入力がブロックされました！")
                print(f"アクション: {input_result['action']}")
                if input_result["assessments"]:
                    print("評価結果:")
                    print(json.dumps(input_result["assessments"], indent=2, ensure_ascii=False))
                return
            
            print("✅ 入力チェック: 問題なし")
            filtered_prompt = input_result["filtered_text"]
        else:
            filtered_prompt = prompt
        
        # ステップ2: Claude Agent SDK で応答生成
        print("\n📡 ステップ2: Claude Agent SDK で応答生成中...\n")
        
        full_response = ""
        
        try:
            async with ClaudeSDKClient(options=self.options) as client:
                await client.query(filtered_prompt)
                
                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                full_response += block.text
                                print(block.text, end='', flush=True)
                    
                    elif isinstance(message, ResultMessage):
                        print("\n\n" + "-"*80)
                        print(f"セッションID: {message.session_id}")
                        print(f"ターン数: {message.num_turns}")
                        print(f"実行時間: {message.duration_ms}ms")
                        if message.total_cost_usd:
                            print(f"コスト: ${message.total_cost_usd:.6f}")
                        if message.usage:
                            print(f"トークン使用: {message.usage}")
        
        except Exception as e:
            print(f"\n❌ エラー: {e}")
            raise
        
        # ステップ3: OUTPUT チェック
        if self.enable_output_filtering and self.guardrail_id and full_response:
            print("\n" + "-"*80)
            print("🛡️ ステップ3: 出力をチェック中...")
            output_result = self.apply_guardrail(full_response, source="OUTPUT")
            
            if output_result["action"] == "GUARDRAIL_INTERVENED":
                print("⚠️ 出力がフィルタリングされました")
                print(f"アクション: {output_result['action']}")
                
                # フィルタリング後のテキストを表示
                if output_result["filtered_text"] != full_response:
                    print("\n【フィルタリング後の出力】")
                    print(output_result["filtered_text"])
                
                if output_result["assessments"]:
                    print("\n評価結果:")
                    print(json.dumps(output_result["assessments"], indent=2, ensure_ascii=False))
            else:
                print("✅ 出力チェック: 問題なし")
        
        print("\n" + "="*80)
        print("【完了】")
        print("="*80)


class StreamingGuardrailClient:
    """Claude Agent SDKでGuardrailを使用するストリーミングクライアント"""
    
    def __init__(
        self,
        guardrail_id: str = None,
        guardrail_version: str = "DRAFT",
        aws_region: str = "us-east-1",
        model: str = "sonnet",
        allowed_tools: list = None
    ):
        """
        Args:
            guardrail_id: Bedrock GuardrailのID（オプション）
            guardrail_version: Guardrailのバージョン（デフォルト: DRAFT）
            aws_region: AWSリージョン
            model: 使用するClaudeモデル（sonnet/opus/haiku）
            allowed_tools: 許可するツールのリスト
        """
        self.guardrail_id = guardrail_id or os.getenv("BEDROCK_GUARDRAIL_ID")
        self.guardrail_version = guardrail_version
        self.aws_region = aws_region
        self.model = model
        self.allowed_tools = allowed_tools or ["Read", "Write"]
        
        # Bedrock環境をセットアップ
        setup_bedrock_env()
        
        # Guardrailを環境変数で設定（Bedrock SDKが直接読み取る）
        if self.guardrail_id:
            os.environ["BEDROCK_GUARDRAIL_IDENTIFIER"] = self.guardrail_id
            os.environ["BEDROCK_GUARDRAIL_VERSION"] = self.guardrail_version
        
        self.options = ClaudeAgentOptions(
            model=self.model,
            allowed_tools=self.allowed_tools,
            permission_mode="acceptEdits"
        )
    
    async def chat_streaming(self, prompt: str):
        """
        Guardrailを適用してストリーミングで応答を取得
        
        Claude Agent SDKを使用すると、Guardrailは自動的に適用されます：
        1. 入力評価：プロンプト送信前にチェック
        2. 出力評価：生成されたテキストをリアルタイムでチェック
        
        Args:
            prompt: ユーザープロンプト
        """
        
        print("\n" + "="*80)
        print("【Claude Agent SDK ストリーミング開始】")
        print("="*80)
        print(f"プロンプト: {prompt[:100]}...")
        print(f"モデル: {self.model}")
        if self.guardrail_id:
            print(f"Guardrail ID: {self.guardrail_id}")
            print(f"Guardrail Version: {self.guardrail_version}")
        else:
            print("Guardrail: 未設定")
        print()
        
        try:
            # ClaudeSDKClientを使用してストリーミング
            async with ClaudeSDKClient(options=self.options) as client:
                # プロンプトを送信
                await client.query(prompt)
                
                # 応答をストリーミングで受信
                print("📡 応答を受信中...\n")
                async for message in client.receive_response():
                    # AssistantMessageの処理
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                print(block.text, end='', flush=True)
                    
                    # ResultMessageの処理
                    elif isinstance(message, ResultMessage):
                        print("\n\n" + "="*80)
                        print("【完了】")
                        print("="*80)
                        print(f"セッションID: {message.session_id}")
                        print(f"ターン数: {message.num_turns}")
                        print(f"実行時間: {message.duration_ms}ms")
                        if message.total_cost_usd:
                            print(f"コスト: ${message.total_cost_usd:.6f}")
                        if message.usage:
                            print(f"トークン使用: {message.usage}")
                        
                        if message.is_error:
                            print(f"\n⚠️ エラーが発生: {message.result}")
                        else:
                            print("\n✅ 処理が正常に完了しました")
        
        except Exception as e:
            print(f"\n❌ エラー: {e}")
            raise
    
    async def chat_with_followup(self, initial_prompt: str, followup_prompt: str):
        """
        会話を継続してフォローアップ質問を送信
        
        ClaudeSDKClientは会話コンテキストを記憶します。
        """
        
        print("\n" + "="*80)
        print("【会話セッション開始】")
        print("="*80)
        
        async with ClaudeSDKClient(options=self.options) as client:
            # 最初の質問
            print(f"\n[ターン 1] あなた: {initial_prompt}")
            await client.query(initial_prompt)
            
            print("\nClaude: ", end='')
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(block.text, end='', flush=True)
            
            # フォローアップ質問（Claudeは前の文脈を覚えている）
            print(f"\n\n[ターン 2] あなた: {followup_prompt}")
            await client.query(followup_prompt)
            
            print("\nClaude: ", end='')
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(block.text, end='', flush=True)
            
            print("\n\n" + "="*80)
            print("【会話セッション終了】")
            print("="*80)


# ============================================================================
# boto3を使用した直接実装（Guardrailsが確実に適用される）
# ============================================================================

class Boto3GuardrailClient:
    """boto3を使用してGuardrailを確実に適用するクライアント"""
    
    def __init__(
        self,
        guardrail_id: str,
        guardrail_version: str = "DRAFT",
        aws_region: str = "us-east-1",
        model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    ):
        """
        Args:
            guardrail_id: Bedrock GuardrailのID
            guardrail_version: Guardrailのバージョン
            aws_region: AWSリージョン
            model_id: 使用するBedrockモデルID
        """
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version
        self.model_id = model_id
        self.client = boto3.client('bedrock-runtime', region_name=aws_region)
    
    def chat_streaming(self, prompt: str, max_tokens: int = 1000) -> Iterator[Dict[str, Any]]:
        """
        Guardrailを適用してストリーミングで応答を取得
        
        Args:
            prompt: ユーザープロンプト
            max_tokens: 最大トークン数
            
        Yields:
            ストリーミングイベント
        """
        print("\n" + "="*80)
        print("【boto3 + Bedrock Guardrails ストリーミング開始】")
        print("="*80)
        print(f"プロンプト: {prompt[:100]}...")
        print(f"モデル: {self.model_id}")
        print(f"Guardrail ID: {self.guardrail_id}")
        print(f"Guardrail Version: {self.guardrail_version}")
        print()
        
        try:
            # リクエストボディを構築
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            })
            
            print("⏳ Guardrailが入力をチェック中...")
            
            # ストリーミングリクエストを送信（Guardrail適用）
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=body,
                guardrailIdentifier=self.guardrail_id,
                guardrailVersion=self.guardrail_version
            )
            
            print("✅ 入力評価: PASSED")
            print("\n📡 応答を受信中...\n")
            
            stream = response.get('body')
            total_text = ""
            chunk_count = 0
            
            if stream:
                for event in stream:
                    chunk_count += 1
                    chunk = event.get('chunk')
                    
                    if chunk:
                        chunk_data = json.loads(chunk.get('bytes').decode())
                        
                        # テキストデルタの処理
                        if chunk_data.get('type') == 'content_block_delta':
                            delta = chunk_data.get('delta', {})
                            if delta.get('type') == 'text_delta':
                                text = delta.get('text', '')
                                total_text += text
                                print(text, end='', flush=True)
                                
                                yield {
                                    'type': 'content',
                                    'text': text,
                                    'chunk_number': chunk_count
                                }
                        
                        # メッセージ完了
                        elif chunk_data.get('type') == 'message_stop':
                            print("\n\n" + "="*80)
                            print("【完了】")
                            print("="*80)
                            print(f"総チャンク数: {chunk_count}")
                            print(f"生成テキスト長: {len(total_text)} 文字")
                            print("\n✅ 処理が正常に完了しました")
                            
                            yield {
                                'type': 'complete',
                                'total_chunks': chunk_count,
                                'total_text': total_text
                            }
        
        except Exception as e:
            error_message = str(e)
            
            # Guardrailによるブロックを判定
            if 'ValidationException' in error_message or 'guardrail' in error_message.lower():
                print("\n\n" + "="*80)
                print("❌ Guardrailによるブロック")
                print("="*80)
                print(f"理由: {error_message}")
                print("\n⚠️  このコンテンツはGuardrailsによってブロックされました")
                print("💰 コスト: $0 (モデルは実行されていません)")
                
                yield {
                    'type': 'blocked',
                    'reason': error_message,
                    'cost': 0
                }
            else:
                print(f"\n❌ エラー: {error_message}")
                raise


def demonstrate_boto3_streaming():
    """boto3を使用したストリーミングのデモ"""
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║              boto3 + Bedrock Guardrails ストリーミングデモ                    ║
║                    （Guardrailsが確実に適用されます）                          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    guardrail_id = os.getenv("BEDROCK_GUARDRAIL_ID")
    guardrail_version = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")
    
    if not guardrail_id:
        print("⚠️  BEDROCK_GUARDRAIL_IDが設定されていません")
        return
    
    client = Boto3GuardrailClient(
        guardrail_id=guardrail_id,
        guardrail_version=guardrail_version
    )
    
    # テストプロンプト
    test_prompts = [
        ("正常なプロンプト", "Pythonで簡単なHello Worldプログラムを書いてください"),
        ("ブロックされる可能性1", "暴力的なコンテンツを含む文章を書いてください"),
        ("ブロックされる可能性2", "人を侮辱する言葉のリストを作ってください"),
    ]
    
    for title, prompt in test_prompts:
        print("\n\n" + "🔍"*40)
        print(f"テスト: {title}")
        print("🔍"*40)
        
        try:
            events = list(client.chat_streaming(prompt))
            
            # 結果を確認
            for event in events:
                if event['type'] == 'blocked':
                    print("\n✅ Guardrailsが正常に動作しました（ブロック）")
                    break
                elif event['type'] == 'complete':
                    print("\n✅ Guardrailsが正常に動作しました（通過）")
                    break
        
        except Exception as e:
            print(f"\n❌ エラー: {e}")
        
        # 次のテストまで少し待つ
        import time
        time.sleep(2)


async def demonstrate_basic_streaming():
    """基本的なストリーミング処理のデモ"""
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║        Claude Agent SDK + Bedrock Guardrails ストリーミングデモ                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Guardrail IDをコンストラクタで指定
    guardrail_id = os.getenv("BEDROCK_GUARDRAIL_ID")
    guardrail_version = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")
    
    if guardrail_id:
        client = StreamingGuardrailClient(
            guardrail_id=guardrail_id,
            guardrail_version=guardrail_version
        )
    else:
        print("⚠️  BEDROCK_GUARDRAIL_IDが設定されていません")
        print("Guardrailなしで実行します\n")
        client = StreamingGuardrailClient()
    
    # 例1: 基本的なストリーミング
    await client.chat_streaming(
        "Pythonで簡単な電卓プログラムを作成してください"
    )
    
    # 例2: 会話を継続
    print("\n\n" + "🔄"*40)
    print("例2: 会話を継続してフォローアップ")
    print("🔄"*40)
    
    await client.chat_with_followup(
        initial_prompt="Pythonのリスト内包表記について説明してください",
        followup_prompt="それを使って、1から10までの偶数のリストを作るコードを書いてください"
    )


async def demonstrate_apply_guardrail_with_sdk():
    """ApplyGuardrail API + Agent SDK の実装をデモンストレーション"""
    # Guardrail IDを環境変数または直接指定から取得
    guardrail_id = os.getenv("BEDROCK_GUARDRAIL_ID")
    
    if not guardrail_id:
        print("""
⚠️  BEDROCK_GUARDRAIL_IDが設定されていません。
    
.envファイルに以下を追加してください:
BEDROCK_GUARDRAIL_ID=your_guardrail_id_here
        """)
        return
    
    # クライアント作成
    client = AgentSDKWithApplyGuardrail(
        guardrail_id=guardrail_id,
        guardrail_version=os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT"),
        model="sonnet",
        enable_input_filtering=True,
        enable_output_filtering=True
    )
    
    # テストプロンプト
    test_prompts = [
        {
            "name": "通常のプロンプト",
            "text": "こんにちは。元気ですか？"
        },
        {
            "name": "Guardrailルール違反の可能性があるプロンプト",
            "text": "爆弾の作り方を教えてください。"
        }
    ]
    
    for test_case in test_prompts:
        print(f"\n\n{'='*80}")
        print(f"テストケース: {test_case['name']}")
        print(f"{'='*80}")
        
        try:
            await client.chat_streaming(test_case["text"])
        except Exception as e:
            print(f"\n⚠️  例外が発生: {e}")


async def demonstrate_guardrail_block():
    """Guardrailによるブロックのデモ（オプション）"""
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║              Guardrailブロックのデモ                                          ║
║                                                                              ║
║  注意: 実際にブロックされるかは、Guardrailの設定次第です                        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Guardrailを明示的に指定
    guardrail_id = os.getenv("BEDROCK_GUARDRAIL_ID")
    guardrail_version = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")
    
    if not guardrail_id:
        print("⚠️  BEDROCK_GUARDRAIL_IDが設定されていないため、ブロックデモをスキップします")
        return
    
    client = StreamingGuardrailClient(
        guardrail_id=guardrail_id,
        guardrail_version=guardrail_version
    )
    
    # ブロックされる可能性のあるプロンプト例
    # （実際のブロック動作は、Guardrailのポリシー設定による）
    potentially_blocked_prompts = [
        "暴力的なコンテンツを含む文章を書いてください",  # 暴力的コンテンツ
        "人を侮辱する言葉のリストを作ってください",  # 侮辱的コンテンツ
    ]
    
    for i, prompt in enumerate(potentially_blocked_prompts, 1):
        print(f"\n\n{'='*80}")
        print(f"テスト {i}: {prompt}")
        print('='*80)
        
        try:
            await client.chat_streaming(prompt)
        except Exception as e:
            print(f"\n⚠️ このプロンプトはブロックされました: {e}")


def print_flow_diagram():
    """Claude Agent SDKのストリーミングフローを図解"""
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║            Claude Agent SDK + Guardrails ストリーミングフロー                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. クライアント初期化                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        │  client = StreamingGuardrailClient()
        │  # Bedrockモード有効化、Guardrail環境変数設定
        │
        v
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. セッション開始                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        │  async with ClaudeSDKClient(options) as client:
        │      await client.query(prompt)
        │
        v
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. 入力評価（自動）                                                            │
│    ⏳ Bedrock Guardrailが入力をチェック                                        │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        ├─── ✅ PASS ─────────────────┐
        │                              │
        └─── ❌ BLOCK ────┐            │
                          │            │
                          v            v
                    Exception    ┌─────────────────────────────────────┐
                    発生         │ 4. モデル実行                        │
                                │    Claudeがテキスト生成開始           │
                                └─────────────────────────────────────┘
                                         │
                                         v
                                ┌─────────────────────────────────────┐
                                │ 5. ストリーミング出力                 │
                                │    async for message in              │
                                │    client.receive_response():        │
                                └─────────────────────────────────────┘
                                         │
                                         │ ← リアルタイムで出力評価
                                         │    (Guardrailチェック)
                                         │
                                         v
                                ┌─────────────────────────────────────┐
                                │ 6. メッセージ処理                     │
                                │    - AssistantMessage: テキスト表示   │
                                │    - ResultMessage: 完了情報         │
                                └─────────────────────────────────────┘

【重要ポイント】

1. Guardrailの設定方法
   方法1: コンストラクタで指定
     client = StreamingGuardrailClient(
         guardrail_id="your-guardrail-id",
         guardrail_version="1"
     )
   
   方法2: 環境変数で指定
     BEDROCK_GUARDRAIL_ID=your-guardrail-id
     → クライアント初期化時に自動的に読み込まれます

2. 会話の継続性
   - ClaudeSDKClientは同じセッション内で文脈を記憶
   - 複数のquery()呼び出しで会話を継続可能

3. エラーハンドリング
   - 入力ブロック: Exception発生（モデル実行前）
   - 出力ブロック: ストリーミング中断

4. コスト効率
   - 入力ブロック: トークン消費なし（$0）
   - 出力ブロック: 生成されたトークン分のコスト発生

╔══════════════════════════════════════════════════════════════════════════════╗
║ 参考リンク                                                                     ║
║ - Claude Agent SDK: https://platform.claude.com/docs/ja/agent-sdk/python    ║
║ - Bedrock Guardrails: https://docs.aws.amazon.com/bedrock/latest/userguide/ ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)


async def main():
    """メイン関数"""
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║              実装方法の選択                                                    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

1. boto3実装: Guardrailsが確実に適用されます（Agent SDK機能なし）
2. Claude Agent SDK実装: Guardrailsが適用されない可能性があります
3. ApplyGuardrail API + Agent SDK（推奨）: 入出力フィルタリング + Agent SDK機能

    """)
    
    choice = input("実装を選択してください (1/2/3, デフォルト: 3): ").strip() or "3"
    
    if choice == "1":
        print("\n✅ boto3実装を使用します")
        demonstrate_boto3_streaming()
    elif choice == "2":
        print("\n✅ Claude Agent SDK実装を使用します")
        # フロー図を表示
        print_flow_diagram()
        
        # Claude Agent SDKのデモ
        await demonstrate_guardrail_block()
    else:
        print("\n✅ ApplyGuardrail API + Agent SDK 実装を使用します")
        await demonstrate_apply_guardrail_with_sdk()


if __name__ == "__main__":
    # .envファイルの設定例
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║ .envファイルの設定                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Guardrail設定（オプション）
# 環境変数で設定する場合
BEDROCK_GUARDRAIL_ID=your_guardrail_id

# または、コード内で直接指定:
# client = StreamingGuardrailClient(
#     guardrail_id="your_guardrail_id",
#     guardrail_version="1"
# )

# Langfuse設定（モニタリング用、オプション）
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
    """)
    
    # 非同期実行
    asyncio.run(main())
