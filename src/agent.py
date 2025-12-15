"""Claude Agent SDK implementation with Bedrock and Langfuse integration.

Langfuse トレーシングは langfuse_tracer.py に分離。
このファイルはエージェント実装のみを含む。
"""

import os
from typing import AsyncIterator, Optional
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeSDKClient
from claude_agent_sdk.types import (
    Message,
    ClaudeAgentOptions,
    ResultMessage,
    AssistantMessage,
    ToolUseBlock,
)

try:
    # When running from project root
    from src.langfuse_tracer import (
        LangfuseTracer,
        TracingConfig,
        AgentMetrics,
        extract_metrics_from_result,
        create_tracer,
        APP_VERSION,
    )
except ImportError:
    # When running from src directory
    from langfuse_tracer import (  # type: ignore
        LangfuseTracer,
        TracingConfig,
        AgentMetrics,
        extract_metrics_from_result,
        create_tracer,
        APP_VERSION,
    )

# Load environment variables
load_dotenv()


def extract_message_text(message: Message, include_result: bool = False) -> str:
    """Extract text from a Message object.

    Args:
        message: Message from Claude Agent SDK
        include_result: Whether to include ResultMessage (default: False for streaming)

    Returns:
        Text content of the message
    """
    # AssistantMessageの場合、contentからテキストを抽出
    if hasattr(message, "content") and isinstance(message.content, list):
        text_parts = []
        for block in message.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "\n".join(text_parts) if text_parts else ""

    # ResultMessageの場合、include_resultがTrueの場合のみresultを返す
    if include_result and hasattr(message, "result") and message.result:
        return message.result

    # その他のメッセージタイプはスキップ
    return ""


def setup_bedrock_env():
    """Setup environment variables for Bedrock integration."""
    # Enable Bedrock mode
    os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"

    # Set AWS credentials from .env if available
    if os.getenv("AWS_ACCESS_KEY_ID"):
        os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
    if os.getenv("AWS_SECRET_ACCESS_KEY"):
        os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
    if os.getenv("AWS_REGION"):
        os.environ["AWS_REGION"] = os.getenv("AWS_REGION")


class BedrockAgentSDK:
    """Agent using Claude Agent SDK with Bedrock backend and Langfuse monitoring."""

    def __init__(
        self,
        aws_region: Optional[str] = None,
        cwd: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        tags: Optional[list[str]] = None,
        environment: str = "development",
    ):
        """Initialize the Bedrock Agent SDK.

        Args:
            aws_region: AWS region where Bedrock is available
            cwd: Working directory for the agent
            model: Model identifier (e.g., "anthropic.claude-3-5-sonnet-20241022-v2:0")
            temperature: Temperature for sampling (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            system_prompt: System prompt for the agent (supports Prompt Caching)
            tags: Custom tags for tracing
            environment: Environment name (development, staging, production)
        """
        self.aws_region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        self.cwd = cwd or os.getcwd()
        self.model = model or os.getenv(
            "MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.tags = tags or []
        self.environment = environment

        # Setup Bedrock environment
        setup_bedrock_env()

    def _create_tracer(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> LangfuseTracer:
        """トレーサーを作成."""
        config = TracingConfig(
            session_id=session_id,
            user_id=user_id,
            tags=self.tags,
            environment=self.environment,
            aws_region=self.aws_region,
            cwd=self.cwd,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=None,
        )
        return LangfuseTracer(config)

    async def chat_streaming(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Send a chat message and stream the response using Claude Agent SDK.

        Note: This method does NOT support tools. Use BedrockAgentSDKWithClient for tool support.

        Args:
            prompt: User prompt
            session_id: Optional session ID for conversation tracking
            user_id: Optional user ID for user-level metrics

        Yields:
            Messages from the agent
        """
        tracer = self._create_tracer(session_id, user_id)

        with tracer.trace_span(
            name="chat_streaming",
            input=prompt,
            metadata={"streaming": "true"},
            tags=["streaming"],
        ) as span:
            full_response = ""
            metrics: Optional[AgentMetrics] = None

            # Create options with system_prompt if provided
            options = None
            if self.system_prompt:
                options = ClaudeAgentOptions(system_prompt=self.system_prompt)

            # Use Claude Agent SDK query function with streaming
            async for message in query(prompt=prompt, options=options):
                # ResultMessage からメトリクスを抽出
                if isinstance(message, ResultMessage):
                    metrics = extract_metrics_from_result(message)
                    continue

                message_text = extract_message_text(message)
                if message_text:
                    full_response += message_text
                    yield message_text

            # Generation を作成
            tracer.create_generation(
                parent=span,
                name="llm_response",
                input=prompt,
                output=full_response,
                metrics=metrics,
            )

            span.set_output(full_response)
            span.update_metadata({"response_length": len(full_response)})

    async def chat(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Send a chat message and get the complete response.

        Note: This method does NOT support tools. Use BedrockAgentSDKWithClient for tool support.

        Args:
            prompt: User prompt
            session_id: Optional session ID for conversation tracking
            user_id: Optional user ID for user-level metrics

        Returns:
            Complete response text
        """
        tracer = self._create_tracer(session_id, user_id)

        with tracer.trace_span(
            name="chat",
            input=prompt,
            metadata={"streaming": "false"},
        ) as span:
            full_response = ""
            message_count = 0
            metrics: Optional[AgentMetrics] = None

            # Create options with system_prompt if provided
            options = None
            if self.system_prompt:
                options = ClaudeAgentOptions(system_prompt=self.system_prompt)

            async for message in query(prompt=prompt, options=options):
                # ResultMessage からメトリクスを抽出
                if isinstance(message, ResultMessage):
                    metrics = extract_metrics_from_result(message)
                    continue

                message_text = extract_message_text(message)
                if message_text:
                    message_count += 1
                    full_response += message_text + "\n"

            # Generation を作成
            tracer.create_generation(
                parent=span,
                name="llm_response",
                input=prompt,
                output=full_response.strip(),
                metrics=metrics,
            )

            span.set_output(full_response.strip())
            span.update_metadata(
                {
                    "message_count": message_count,
                    "response_length": len(full_response),
                }
            )

        return full_response.strip()


class BedrockAgentSDKWithClient:
    """Advanced agent using ClaudeSDKClient with custom tools."""

    def __init__(
        self,
        aws_region: Optional[str] = None,
        cwd: Optional[str] = None,
        tools: Optional[list[str]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tags: Optional[list[str]] = None,
        environment: str = "development",
    ):
        """Initialize the Bedrock Agent SDK with ClaudeSDKClient.

        Args:
            aws_region: AWS region where Bedrock is available
            cwd: Working directory for the agent
            tools: List of allowed tools (e.g., ["Read", "Write", "Bash"])
            model: Model identifier (e.g., "anthropic.claude-3-5-sonnet-20241022-v2:0")
            temperature: Temperature for sampling (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            tags: Custom tags for tracing
            environment: Environment name (development, staging, production)
        """
        self.aws_region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        self.cwd = cwd or os.getcwd()
        self.tools = tools
        self.model = model or os.getenv(
            "MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.tags = tags or []
        self.environment = environment

        # Setup Bedrock environment
        setup_bedrock_env()

        self.client: Optional[ClaudeSDKClient] = None

    def _create_tracer(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> LangfuseTracer:
        """トレーサーを作成."""
        config = TracingConfig(
            session_id=session_id,
            user_id=user_id,
            tags=self.tags,
            environment=self.environment,
            aws_region=self.aws_region,
            cwd=self.cwd,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=self.tools,
        )
        return LangfuseTracer(config)

    async def __aenter__(self):
        """Async context manager entry."""
        # Create options with allowed tools and cwd
        options = ClaudeAgentOptions(
            allowed_tools=self.tools or [],
            cwd=self.cwd,
        )
        self.client = ClaudeSDKClient(options=options)
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def chat_with_client(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Send a chat using ClaudeSDKClient for bidirectional conversation.

        Args:
            prompt: User prompt
            session_id: Optional session ID for conversation tracking
            user_id: Optional user ID for user-level metrics

        Yields:
            Response messages
        """
        if not self.client:
            raise RuntimeError(
                "Client not initialized. Use async with context manager."
            )

        tracer = self._create_tracer(session_id, user_id)

        with tracer.trace_agent(
            name="chat_with_client",
            input=prompt,
            metadata={
                "tools": str(self.tools) if self.tools else "none",
                "tools_count": str(len(self.tools)) if self.tools else "0",
            },
            tags=["with-tools"] if self.tools else [],
        ) as span:
            full_response = ""
            metrics: Optional[AgentMetrics] = None
            tool_call_count = 0

            try:
                # Send query to Claude
                await self.client.query(prompt)

                # 現在のツールを追跡（ToolResultBlockは受信ストリームに含まれないため）
                current_tool_ids: list[str] = []

                # Receive response messages
                async for message in self.client.receive_response():
                    # ResultMessage からメトリクスを抽出
                    if isinstance(message, ResultMessage):
                        metrics = extract_metrics_from_result(message)
                        # 最終メッセージ時に未終了のツールを正常終了
                        for tool_id in current_tool_ids:
                            tracer.end_tool_span(
                                tool_use_id=tool_id,
                                output="(tool executed by SDK)",
                                is_error=False,
                            )
                        current_tool_ids.clear()
                        continue

                    # AssistantMessage からツール使用を検出
                    if isinstance(message, AssistantMessage):
                        # 新しいAssistantMessage到着時、前のツールを終了
                        # （SDKが内部でツールを実行し、次のメッセージが来たということは実行完了）
                        for tool_id in current_tool_ids:
                            tracer.end_tool_span(
                                tool_use_id=tool_id,
                                output="(tool executed by SDK)",
                                is_error=False,
                            )
                        current_tool_ids.clear()

                        for block in message.content:
                            # ツール使用の検出
                            if isinstance(block, ToolUseBlock):
                                tool_call_count += 1
                                tracer.start_tool_span(
                                    parent=span,
                                    tool_name=block.name,
                                    tool_use_id=block.id,
                                    tool_call_number=tool_call_count,
                                    input=block.input,
                                )
                                current_tool_ids.append(block.id)

                    # テキスト抽出
                    message_text = extract_message_text(message)
                    if message_text:
                        full_response += message_text
                        yield message_text

                # 残った未終了のツール span を終了（正常終了として）
                for tool_id in current_tool_ids:
                    tracer.end_tool_span(
                        tool_use_id=tool_id,
                        output="(tool executed by SDK)",
                        is_error=False,
                    )
                current_tool_ids.clear()

                # 万が一の未終了スパンを終了
                tracer.end_all_pending_spans("no result received")

                # Generation を作成
                tracer.create_generation(
                    parent=span,
                    name="llm_response",
                    input=prompt,
                    output=full_response,
                    metrics=metrics,
                    tool_call_count=tool_call_count,
                )

                span.set_output(full_response)
                span.update_metadata(
                    {
                        "tool_calls": tool_call_count,
                        "response_length": len(full_response),
                    }
                )

            except Exception as e:
                # エラー時は未終了スパンをクリーンアップ
                tracer.end_all_pending_spans(f"error: {str(e)}")
                # スタックトレースを含めてエラーを記録
                span.set_error_with_traceback(e)
                raise


# Convenience function for simple usage
async def simple_query(
    prompt: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    tags: Optional[list[str]] = None,
    environment: str = "development",
) -> str:
    """Simple query function using Claude Agent SDK with Bedrock.

    Note: This function does NOT support tools. Use BedrockAgentSDKWithClient for tool support.

    Args:
        prompt: User prompt
        session_id: Optional session ID for conversation tracking
        user_id: Optional user ID for user-level metrics
        model: Model identifier (e.g., "anthropic.claude-3-5-sonnet-20241022-v2:0")
        temperature: Temperature for sampling (0.0 - 1.0)
        max_tokens: Maximum tokens to generate
        tags: Custom tags for tracing
        environment: Environment name (development, staging, production)

    Returns:
        Complete response
    """
    setup_bedrock_env()

    model_id = model or os.getenv(
        "MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    tracer = create_tracer(
        session_id=session_id,
        user_id=user_id,
        tags=tags,
        environment=environment,
        aws_region=aws_region,
        model=model_id,
    )

    with tracer.trace_span(
        name="simple_query",
        input=prompt,
        metadata={"streaming": "false"},
    ) as span:
        full_response = ""
        metrics: Optional[AgentMetrics] = None

        async for message in query(prompt=prompt):
            # ResultMessage からメトリクスを抽出
            if isinstance(message, ResultMessage):
                metrics = extract_metrics_from_result(message)
                continue

            message_text = extract_message_text(message)
            if message_text:
                full_response += message_text + "\n"

        # Generation を作成
        tracer.create_generation(
            parent=span,
            name="llm_response",
            input=prompt,
            output=full_response.strip(),
            metrics=metrics,
        )

        span.set_output(full_response.strip())
        span.update_metadata({"response_length": len(full_response)})

    return full_response.strip()
