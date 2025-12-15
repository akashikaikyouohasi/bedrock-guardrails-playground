"""Example usage of Claude Agent SDK with Bedrock and Langfuse integration."""

import uuid
import anyio
from agent import BedrockAgentSDK, BedrockAgentSDKWithClient, simple_query
from langfuse import get_client

# Initialize Langfuse client
langfuse = get_client()

# デモ用の session_id と user_id
# 実際のアプリでは、session_id はセッション開始時に1回だけ生成し、
# user_id はログインユーザーIDなどを使用する
DEMO_SESSION_ID = f"demo-{uuid.uuid4().hex[:8]}"
DEMO_USER_ID = "demo-user"


# async def example_simple_query():
#     """Example 1: Simple query using convenience function."""
#     print("=== Example 1: Simple Query (Streaming) ===\n")

#     prompt = "2 + 2は？計算を説明してください。"
#     print(f"User: {prompt}\n")
#     print("Assistant: ", end="", flush=True)

#     response = await simple_query(prompt)
#     print(response)
#     print("\n")


# async def example_streaming_chat():
#     """Example 2: Streaming chat with Claude Agent SDK."""
#     print("=== Example 2: Streaming Chat ===\n")

#     agent = BedrockAgentSDK()

#     prompt = "量子コンピューティングを3文で説明してください。"
#     print(f"User: {prompt}\n")
#     print("Assistant:\n")

#     async for chunk in agent.chat_streaming(prompt):
#         print(chunk)
#         print("---")

#     print("\n")


# async def example_non_streaming_chat():
#     """Example 3: Non-streaming chat (collects all messages)."""
#     print("=== Example 3: Non-Streaming Chat ===\n")

#     agent = BedrockAgentSDK()

#     prompt = "ロボット工学の三原則とは何ですか？"
#     print(f"User: {prompt}\n")

#     response = await agent.chat(prompt)
#     print(f"Assistant: {response}\n")


async def example_with_client():
    """Example 4: Using ClaudeSDKClient with tools."""
    print("=== Example 4: ClaudeSDKClientでツールを使用 ===\n")

    prompt = "「Claude Agent SDKからこんにちは！」と出力するシンプルなhello.pyファイルを作成してください。"
    tools = ["Write"]

    print(f"User: {prompt}\n")
    print(f"Allowed Tools: {tools}\n")
    print(f"Session ID: {DEMO_SESSION_ID}\n")
    print(f"User ID: {DEMO_USER_ID}\n")
    print("Assistant:\n")

    async with BedrockAgentSDKWithClient(tools=tools) as agent_client:
        async for chunk in agent_client.chat_with_client(
            prompt,
            session_id=DEMO_SESSION_ID,
            user_id=DEMO_USER_ID,
        ):
            print(chunk)
            print("---")

    print("\n")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Claude Agent SDK with Bedrock & Langfuse - サンプル")
    print("=" * 60 + "\n")

    try:
        # Run examples sequentially
        # await example_simple_query()
        # await example_streaming_chat()
        # await example_non_streaming_chat()
        await example_with_client()

        print("=" * 60)
        print("すべてのサンプルが正常に完了しました！")
        print("監視データはLangfuseダッシュボードで確認できます。")
        print("=" * 60 + "\n")

        # Flush Langfuse to ensure all traces are sent
        langfuse.flush()

    except Exception as e:
        print(f"\nエラー: {e}")
        print(f"\nエラータイプ: {type(e).__name__}")
        print("\n設定を確認してください:")
        print("1. AWS認証情報が正しく設定されている")
        print("2. Bedrockがリージョンで利用可能")
        print("3. Langfuse APIキーが設定されている")
        print("4. .envファイルが正しくセットアップされている")
        print("5. CLAUDE_CODE_USE_BEDROCK=1が設定されている")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    anyio.run(main)
