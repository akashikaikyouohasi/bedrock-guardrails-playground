"""Example usage of Claude Agent SDK with Bedrock and Langfuse integration."""

import anyio
from agent import BedrockAgentSDK, BedrockAgentSDKWithClient, simple_query
from langfuse import get_client

# Initialize Langfuse client
langfuse = get_client()


async def example_simple_query():
    """Example 1: Simple query using convenience function."""
    print("=== Example 1: Simple Query (Streaming) ===\n")

    prompt = "2 + 2は？計算を説明してください。"
    print(f"User: {prompt}\n")
    print("Assistant: ", end="", flush=True)

    response = await simple_query(prompt)
    print(response)
    print("\n")


async def example_streaming_chat():
    """Example 2: Streaming chat with Claude Agent SDK."""
    print("=== Example 2: Streaming Chat ===\n")

    agent = BedrockAgentSDK()

    prompt = "量子コンピューティングを3文で説明してください。"
    print(f"User: {prompt}\n")
    print("Assistant:\n")

    async for chunk in agent.chat_streaming(prompt):
        print(chunk)
        print("---")

    print("\n")


async def example_non_streaming_chat():
    """Example 3: Non-streaming chat (collects all messages)."""
    print("=== Example 3: Non-Streaming Chat ===\n")

    agent = BedrockAgentSDK()

    prompt = "ロボット工学の三原則とは何ですか？"
    print(f"User: {prompt}\n")

    response = await agent.chat(prompt)
    print(f"Assistant: {response}\n")


async def example_with_tools():
    """Example 4: Chat with allowed tools."""
    print("=== Example 4: Chat with Tools ===\n")

    agent = BedrockAgentSDK()

    # エージェントにReadとBashツールの使用を許可
    prompt = "カレントディレクトリのファイル一覧を表示して、プロジェクト構造について教えてください。"
    tools = ["Read", "Bash"]

    print(f"User: {prompt}\n")
    print(f"Allowed Tools: {tools}\n")
    print("Assistant:\n")

    async for chunk in agent.chat_streaming(prompt, tools=tools):
        print(chunk)
        print("---")

    print("\n")


async def example_with_client():
    """Example 5: Using ClaudeSDKClient for advanced usage."""
    print("=== Example 5: Using ClaudeSDKClient ===\n")

    prompt = "「Claude Agent SDKからこんにちは！」と出力するシンプルなhello.pyファイルを作成してください。"
    tools = ["Write"]

    print(f"User: {prompt}\n")
    print(f"Allowed Tools: {tools}\n")
    print("Assistant:\n")

    async with BedrockAgentSDKWithClient() as agent_client:
        async for chunk in agent_client.chat_with_client(prompt, tools=tools):
            print(chunk)
            print("---")

    print("\n")


async def example_code_execution():
    """Example 6: Agent that can execute code."""
    print("=== Example 6: Code Execution ===\n")

    agent = BedrockAgentSDK()

    prompt = "Pythonを使って5の階乗を計算してください。コードを示して実行してください。"
    tools = ["Bash"]  # コード実行のためBashを許可

    print(f"User: {prompt}\n")
    print(f"Allowed Tools: {tools}\n")
    print("Assistant:\n")

    async for chunk in agent.chat_streaming(prompt, tools=tools):
        print(chunk)
        print("---")

    print("\n")


async def example_read_file():
    """Example 7: Agent that reads project files."""
    print("=== Example 7: Reading Project Files ===\n")

    agent = BedrockAgentSDK()

    prompt = "README.mdファイルを読んで、このプロジェクトが何をするのか要約してください。"
    tools = ["Read"]

    print(f"User: {prompt}\n")
    print(f"Allowed Tools: {tools}\n")
    print("Assistant:\n")

    async for chunk in agent.chat_streaming(prompt, tools=tools):
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
        await example_simple_query()
        await example_streaming_chat()
        # await example_non_streaming_chat()
        # await example_with_tools()
        # await example_with_client()
        # await example_code_execution()
        # await example_read_file()

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
