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
    ):
        """Initialize the Bedrock Agent SDK.

        Args:
            aws_region: AWS region where Bedrock is available
            cwd: Working directory for the agent
        """
        self.aws_region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        self.cwd = cwd or os.getcwd()

        # Setup Bedrock environment
        setup_bedrock_env()

    async def chat_streaming(
        self,
        prompt: str,
    ) -> AsyncIterator[str]:
        """Send a chat message and stream the response using Claude Agent SDK.

        Note: This method does NOT support tools. Use BedrockAgentSDKWithClient for tool support.

        Args:
            prompt: User prompt

        Yields:
            Messages from the agent
        """
        # Manual Langfuse tracing: Create generation object
        generation = langfuse.start_generation(
            name="chat_streaming",
            model="bedrock-claude",
            input=prompt,
            metadata={
                "cwd": self.cwd,
            },
        )

        full_response = ""

        try:
            # Use Claude Agent SDK query function with streaming
            # Note: query() does not support tools or cwd parameters in current version
            async for message in query(prompt=prompt):
                message_text = self._extract_message_text(message)
                if message_text:  # 空文字列はスキップ
                    full_response += message_text
                    yield message_text

            # Update generation with output
            generation.update(output=full_response)

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
    ) -> str:
        """Send a chat message and get the complete response.

        Note: This method does NOT support tools. Use BedrockAgentSDKWithClient for tool support.

        Args:
            prompt: User prompt

        Returns:
            Complete response text
        """
        # Update Langfuse context
        langfuse.update_current_generation(
            model="bedrock-claude",
            input=prompt,
            metadata={
                "cwd": self.cwd,
            },
        )

        full_response = ""
        message_count = 0

        try:
            # Note: query() does not support tools or cwd parameters in current version
            async for message in query(prompt=prompt):
                message_text = self._extract_message_text(message)
                if message_text:  # 空文字列はスキップ
                    message_count += 1
                    full_response += message_text + "\n"

        except Exception as e:
            langfuse.update_current_generation(
                level="ERROR",
                status_message=str(e),
            )
            raise

        # Update Langfuse
        langfuse.update_current_generation(
            output=full_response,
            metadata={
                "message_count": message_count,
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
    ):
        """Initialize the Bedrock Agent SDK with ClaudeSDKClient.

        Args:
            aws_region: AWS region where Bedrock is available
            cwd: Working directory for the agent
            tools: List of allowed tools (e.g., ["Read", "Write", "Bash"])
        """
        self.aws_region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        self.cwd = cwd or os.getcwd()
        self.tools = tools

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
    ) -> AsyncIterator[str]:
        """Send a chat using ClaudeSDKClient for bidirectional conversation.

        Args:
            prompt: User prompt

        Yields:
            Response messages
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use async with context manager.")

        # Manual Langfuse tracing: Create generation object
        generation = langfuse.start_generation(
            name="chat_with_client",
            model="bedrock-claude",
            input=prompt,
            metadata={
                "tools": self.tools,
                "cwd": self.cwd,
            },
        )

        full_response = ""

        try:
            # Send query to Claude
            await self.client.query(prompt)

            # Receive response messages
            async for message in self.client.receive_response():
                message_text = self._extract_message_text(message)
                if message_text:  # 空文字列はスキップ
                    full_response += message_text
                    yield message_text

            # Update generation with output
            generation.update(output=full_response)

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
async def simple_query(prompt: str) -> str:
    """Simple query function using Claude Agent SDK with Bedrock.

    Note: This function does NOT support tools. Use BedrockAgentSDKWithClient for tool support.

    Args:
        prompt: User prompt

    Returns:
        Complete response
    """
    setup_bedrock_env()

    # Manual Langfuse tracing: Create generation object
    generation = langfuse.start_generation(
        name="simple_query",
        model="bedrock-claude",
        input=prompt,
    )

    full_response = ""

    try:
        # query() does not support tools parameter
        async for message in query(prompt=prompt):
            message_text = extract_message_text(message)
            if message_text:  # 空文字列はスキップ
                full_response += message_text + "\n"

        # Update generation with output
        generation.update(output=full_response)

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
