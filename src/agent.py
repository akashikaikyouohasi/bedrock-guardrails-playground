"""Claude Agent SDK implementation with Bedrock and Langfuse integration."""

import os
from typing import AsyncIterator, Optional
from dotenv import load_dotenv
import anyio
from claude_agent_sdk import query, ClaudeSDKClient
from claude_agent_sdk.types import Message, ClaudeAgentOptions
from langfuse import observe, get_client

# Load environment variables
load_dotenv()

# Initialize Langfuse client
langfuse = get_client()

# Application version
APP_VERSION = "1.0.0"

# Try to import tiktoken for token estimation
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """Estimate token count for given text.

    Args:
        text: Text to estimate tokens for
        model: Model name for encoding (default: gpt-4 for Claude compatibility)

    Returns:
        Estimated token count
    """
    if not TIKTOKEN_AVAILABLE:
        # Fallback: rough estimation (1 token ≈ 4 characters for English)
        return len(text) // 4

    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback if model not found
        return len(text) // 4


def extract_message_text(message: Message, include_result: bool = False) -> str:
    """Extract text from a Message object.

    Args:
        message: Message from Claude Agent SDK
        include_result: Whether to include ResultMessage (default: False for streaming)

    Returns:
        Text content of the message
    """
    # AssistantMessageの場合、contentからテキストを抽出
    if hasattr(message, 'content') and isinstance(message.content, list):
        text_parts = []
        for block in message.content:
            if hasattr(block, 'text'):
                text_parts.append(block.text)
        return '\n'.join(text_parts) if text_parts else ''

    # ResultMessageの場合、include_resultがTrueの場合のみresultを返す
    if include_result and hasattr(message, 'result') and message.result:
        return message.result

    # その他のメッセージタイプはスキップ
    return ''


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
    ):
        """Initialize the Bedrock Agent SDK.

        Args:
            aws_region: AWS region where Bedrock is available
            cwd: Working directory for the agent
            model: Model identifier (e.g., "anthropic.claude-3-5-sonnet-20241022-v2:0")
            temperature: Temperature for sampling (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            system_prompt: System prompt for the agent (supports Prompt Caching)
        """
        self.aws_region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        self.cwd = cwd or os.getcwd()
        self.model = model or os.getenv("MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt

        # Setup Bedrock environment
        setup_bedrock_env()

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
        # Manual Langfuse tracing: Create generation object
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
            # Estimate input tokens
            input_tokens = estimate_tokens(prompt)

            # Create options with system_prompt if provided
            options = None
            if self.system_prompt:
                options = ClaudeAgentOptions(system_prompt=self.system_prompt)

            # Use Claude Agent SDK query function with streaming
            # Note: query() does not support tools or cwd parameters in current version
            async for message in query(prompt=prompt, options=options):
                message_text = self._extract_message_text(message)
                if message_text:  # 空文字列はスキップ
                    full_response += message_text
                    yield message_text

            # Estimate output tokens
            output_tokens = estimate_tokens(full_response)

            # Update generation with output and usage
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
            # End the generation
            generation.end()
            langfuse.flush()

    @observe(as_type="generation")
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
        # Update Langfuse context
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
        message_count = 0
        input_tokens = 0
        output_tokens = 0

        try:
            # Estimate input tokens
            input_tokens = estimate_tokens(prompt)

            # Create options with system_prompt if provided
            options = None
            if self.system_prompt:
                options = ClaudeAgentOptions(system_prompt=self.system_prompt)

            # Note: query() does not support tools or cwd parameters in current version
            async for message in query(prompt=prompt, options=options):
                message_text = self._extract_message_text(message)
                if message_text:  # 空文字列はスキップ
                    message_count += 1
                    full_response += message_text + "\n"

            # Estimate output tokens
            output_tokens = estimate_tokens(full_response)

        except Exception as e:
            langfuse.update_current_generation(
                level="ERROR",
                status_message=str(e),
            )
            raise

        # Update Langfuse
        langfuse.update_current_generation(
            output=full_response.strip(),
            usage_details={
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens,
            },
            metadata={
                "message_count": message_count,
                "response_length": len(full_response),
            },
        )

        return full_response.strip()

    def _extract_message_text(self, message: Message) -> str:
        """Extract text from a Message object.

        Args:
            message: Message from Claude Agent SDK

        Returns:
            Text content of the message
        """
        return extract_message_text(message)


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
    ):
        """Initialize the Bedrock Agent SDK with ClaudeSDKClient.

        Args:
            aws_region: AWS region where Bedrock is available
            cwd: Working directory for the agent
            tools: List of allowed tools (e.g., ["Read", "Write", "Bash"])
            model: Model identifier (e.g., "anthropic.claude-3-5-sonnet-20241022-v2:0")
            temperature: Temperature for sampling (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
        """
        self.aws_region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        self.cwd = cwd or os.getcwd()
        self.tools = tools
        self.model = model or os.getenv("MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Setup Bedrock environment
        setup_bedrock_env()

        self.client: Optional[ClaudeSDKClient] = None

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
            raise RuntimeError("Client not initialized. Use async with context manager.")

        # Manual Langfuse tracing: Create generation object
        metadata = {
            "tools": str(self.tools) if self.tools else "none",
            "tools_count": str(len(self.tools)) if self.tools else "0",
            "cwd": self.cwd,
            "aws_region": self.aws_region,
            "version": APP_VERSION,
            "streaming": "true",
            "sdk": "claude-agent-sdk-with-client",
        }
        if session_id:
            metadata["session_id"] = session_id
        if user_id:
            metadata["user_id"] = user_id

        generation = langfuse.start_generation(
            name="chat_with_client",
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
            # Estimate input tokens
            input_tokens = estimate_tokens(prompt)

            # Send query to Claude
            await self.client.query(prompt)

            # Receive response messages
            async for message in self.client.receive_response():
                message_text = self._extract_message_text(message)
                if message_text:  # 空文字列はスキップ
                    full_response += message_text
                    yield message_text

            # Estimate output tokens
            output_tokens = estimate_tokens(full_response)

            # Update generation with output and usage
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
            # End the generation
            generation.end()
            langfuse.flush()

    def _extract_message_text(self, message: Message) -> str:
        """Extract text from a Message object."""
        return extract_message_text(message)


# Convenience function for simple usage
async def simple_query(
    prompt: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
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

    Returns:
        Complete response
    """
    setup_bedrock_env()

    model_id = model or os.getenv("MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    # Manual Langfuse tracing: Create generation object
    metadata = {
        "aws_region": aws_region,
        "version": APP_VERSION,
        "streaming": "false",
        "sdk": "claude-agent-sdk",
    }
    if session_id:
        metadata["session_id"] = session_id
    if user_id:
        metadata["user_id"] = user_id

    generation = langfuse.start_generation(
        name="simple_query",
        model=model_id,
        input=prompt,
        model_parameters={
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        metadata=metadata,
    )

    full_response = ""
    input_tokens = 0
    output_tokens = 0

    try:
        # Estimate input tokens
        input_tokens = estimate_tokens(prompt)

        # query() does not support tools parameter
        async for message in query(prompt=prompt):
            message_text = extract_message_text(message)
            if message_text:  # 空文字列はスキップ
                full_response += message_text + "\n"

        # Estimate output tokens
        output_tokens = estimate_tokens(full_response)

        # Update generation with output and usage
        generation.update(
            output=full_response.strip(),
            usage_details={
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens,
            },
            metadata={
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
        # End the generation
        generation.end()
        langfuse.flush()

    return full_response.strip()
