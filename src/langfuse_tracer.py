"""Langfuse tracing utilities for Claude Agent SDK.

デコレーター非対応のエージェントフレームワーク用のマニュアルトレーシング実装。

主な機能:
1. try/finally でスパンの確実終了
2. flush() の適切な呼び出し
3. エラーレベル設定（ERROR, WARNING, DEFAULT）
4. タグによるフィルタリング支援
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional, Any
from dotenv import load_dotenv
from claude_agent_sdk.types import ResultMessage

# Load environment variables BEFORE initializing Langfuse
load_dotenv()

from langfuse import get_client

# Initialize Langfuse client (after dotenv is loaded)
_langfuse = get_client()

# Application version
APP_VERSION = "1.2.0"  # Langfuse分離版


@dataclass
class AgentMetrics:
    """Claude Agent SDKから取得したメトリクス."""

    # トークン使用量（ResultMessage.usageから取得）
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    # コストと時間（ResultMessageから取得）
    total_cost_usd: Optional[float] = None
    duration_ms: Optional[int] = None
    duration_api_ms: Optional[int] = None

    # セッション情報
    session_id: Optional[str] = None
    num_turns: int = 0

    def to_langfuse_usage(self) -> dict:
        """Langfuse用のusage辞書を生成."""
        usage = {
            "input": self.input_tokens,
            "output": self.output_tokens,
            "total": self.input_tokens + self.output_tokens,
        }
        # キャッシュメトリクスを追加
        if self.cache_creation_input_tokens > 0:
            usage["cache_creation_input_tokens"] = self.cache_creation_input_tokens
        if self.cache_read_input_tokens > 0:
            usage["cache_read_input_tokens"] = self.cache_read_input_tokens
        return usage

    def to_langfuse_metadata(self) -> dict:
        """Langfuse用のメタデータ辞書を生成."""
        metadata = {
            "num_turns": self.num_turns,
        }
        if self.duration_ms is not None:
            metadata["duration_ms"] = self.duration_ms
        if self.duration_api_ms is not None:
            metadata["duration_api_ms"] = self.duration_api_ms
        if self.total_cost_usd is not None:
            metadata["total_cost_usd"] = self.total_cost_usd
        if self.session_id:
            metadata["claude_session_id"] = self.session_id
        return metadata


def extract_metrics_from_result(result_message: ResultMessage) -> AgentMetrics:
    """ResultMessageからメトリクスを抽出.

    Args:
        result_message: Claude Agent SDKからのResultMessage

    Returns:
        AgentMetrics: 抽出されたメトリクス
    """
    metrics = AgentMetrics()

    # セッション情報
    metrics.session_id = getattr(result_message, "session_id", None)
    metrics.num_turns = getattr(result_message, "num_turns", 0)

    # コストと時間
    metrics.total_cost_usd = getattr(result_message, "total_cost_usd", None)
    metrics.duration_ms = getattr(result_message, "duration_ms", None)
    metrics.duration_api_ms = getattr(result_message, "duration_api_ms", None)

    # トークン使用量
    usage = getattr(result_message, "usage", None)
    if usage:
        # usage は辞書またはオブジェクトの可能性がある
        if isinstance(usage, dict):
            metrics.input_tokens = usage.get("input_tokens", 0)
            metrics.output_tokens = usage.get("output_tokens", 0)
            metrics.cache_creation_input_tokens = usage.get(
                "cache_creation_input_tokens", 0
            )
            metrics.cache_read_input_tokens = usage.get("cache_read_input_tokens", 0)
        else:
            metrics.input_tokens = getattr(usage, "input_tokens", 0)
            metrics.output_tokens = getattr(usage, "output_tokens", 0)
            metrics.cache_creation_input_tokens = getattr(
                usage, "cache_creation_input_tokens", 0
            )
            metrics.cache_read_input_tokens = getattr(usage, "cache_read_input_tokens", 0)

    return metrics


@dataclass
class TracingConfig:
    """トレーシング設定."""

    # 基本設定
    session_id: Optional[str] = None
    user_id: Optional[str] = None

    # タグ（フィルタリング用）
    tags: list[str] = field(default_factory=list)

    # 環境情報
    environment: str = "development"
    aws_region: str = "us-east-1"
    cwd: str = ""

    # モデル情報
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096

    # ツール情報
    tools: Optional[list[str]] = None

    def get_base_metadata(self) -> dict:
        """基本メタデータを生成."""
        return {
            "version": APP_VERSION,
            "environment": self.environment,
            "aws_region": self.aws_region,
            "cwd": self.cwd,
            "sdk": "claude-agent-sdk",
            "session_id": self.session_id,
            "user_id": self.user_id,
        }

    def get_base_tags(self) -> list[str]:
        """基本タグを生成."""
        base_tags = [
            f"env:{self.environment}",
            f"region:{self.aws_region}",
        ]
        if self.model:
            # モデル名からタグを生成（例: claude-3-5-sonnet）
            model_short = self.model.split("/")[-1].split(":")[0]
            if "." in model_short:
                model_short = model_short.split(".")[-1]
            base_tags.append(f"model:{model_short}")

        if self.tools:
            base_tags.append("with-tools")
        else:
            base_tags.append("no-tools")

        # ユーザー指定のタグを追加
        base_tags.extend(self.tags)

        return base_tags


class LangfuseTracer:
    """Langfuse トレーシングマネージャー.

    デコレーター非対応フレームワーク用のマニュアルトレーシング実装。
    try/finally によるスパン確実終了、エラーレベル設定、タグ管理を提供。

    使用例:
        config = TracingConfig(
            session_id="session-123",
            user_id="user-456",
            tags=["production", "api-v2"],
        )
        tracer = LangfuseTracer(config)

        with tracer.trace_span("chat_session", input=prompt) as span:
            # 処理
            with tracer.trace_tool(span, "Read", input={"path": "/file"}) as tool_span:
                # ツール実行
                tool_span.set_output(result)

            span.set_output(response)
    """

    def __init__(self, config: Optional[TracingConfig] = None):
        """初期化.

        Args:
            config: トレーシング設定（Noneの場合はデフォルト設定）
        """
        self.config = config or TracingConfig()
        self._pending_spans: dict[str, Any] = {}

    @contextmanager
    def trace_span(
        self,
        name: str,
        input: Any = None,
        metadata: Optional[dict] = None,
        tags: Optional[list[str]] = None,
    ):
        """スパンをトレース（コンテキストマネージャー）.

        try/finally でスパンの確実終了を保証。

        Args:
            name: スパン名
            input: 入力データ
            metadata: 追加メタデータ
            tags: 追加タグ（metadata内のtagsフィールドに格納）

        Yields:
            SpanWrapper: スパンラッパー
        """
        # メタデータとタグをマージ
        merged_metadata = {**self.config.get_base_metadata()}
        if metadata:
            merged_metadata.update(metadata)

        # タグはメタデータ内に格納（Langfuse 3.10.5はstart_spanでtagsをサポートしない）
        merged_tags = self.config.get_base_tags()
        if tags:
            merged_tags.extend(tags)
        merged_metadata["tags"] = merged_tags

        span = _langfuse.start_span(
            name=name,
            input=input,
            metadata=merged_metadata,
        )

        wrapper = SpanWrapper(span, self)

        try:
            yield wrapper
        except Exception as e:
            wrapper.set_error(str(e))
            raise
        finally:
            wrapper.end()
            self.flush()

    @contextmanager
    def trace_tool(
        self,
        parent: "SpanWrapper",
        tool_name: str,
        tool_use_id: str,
        input: Any = None,
    ):
        """ツール呼び出しをトレース（コンテキストマネージャー）.

        Args:
            parent: 親スパンラッパー
            tool_name: ツール名
            tool_use_id: ツール使用ID
            input: ツール入力

        Yields:
            SpanWrapper: ツールスパンラッパー
        """
        tool_span = parent._span.start_span(
            name=f"tool:{tool_name}",
            input=input,
            metadata={
                "tool_name": tool_name,
                "tool_use_id": tool_use_id,
            },
        )

        wrapper = SpanWrapper(tool_span, self, is_tool=True)

        try:
            yield wrapper
        except Exception as e:
            wrapper.set_error(str(e))
            raise
        finally:
            wrapper.end()

    def start_tool_span(
        self,
        parent: "SpanWrapper",
        tool_name: str,
        tool_use_id: str,
        tool_call_number: int,
        input: Any = None,
    ) -> "SpanWrapper":
        """ツールスパンを開始（非同期処理用）.

        コンテキストマネージャーが使えない場合に使用。
        必ず end_tool_span() または set_error() + end() を呼ぶこと。

        Args:
            parent: 親スパンラッパー
            tool_name: ツール名
            tool_use_id: ツール使用ID
            tool_call_number: ツール呼び出し番号
            input: ツール入力

        Returns:
            SpanWrapper: ツールスパンラッパー
        """
        tool_span = parent._span.start_span(
            name=f"tool:{tool_name}",
            input=input,
            metadata={
                "tool_name": tool_name,
                "tool_use_id": tool_use_id,
                "tool_call_number": tool_call_number,
            },
        )

        wrapper = SpanWrapper(tool_span, self, is_tool=True)
        self._pending_spans[tool_use_id] = wrapper
        return wrapper

    def end_tool_span(
        self,
        tool_use_id: str,
        output: Any = None,
        is_error: bool = False,
    ) -> Optional["SpanWrapper"]:
        """ツールスパンを終了.

        Args:
            tool_use_id: ツール使用ID
            output: ツール出力
            is_error: エラーかどうか

        Returns:
            終了したスパンラッパー（存在しない場合はNone）
        """
        wrapper = self._pending_spans.pop(tool_use_id, None)
        if wrapper:
            if is_error:
                wrapper.set_error(str(output) if output else "Tool execution failed")
            else:
                wrapper.set_output(output)
            wrapper.end()
        return wrapper

    def end_all_pending_spans(self, reason: str = "interrupted"):
        """すべての未終了スパンを終了.

        エラー発生時のクリーンアップ用。

        Args:
            reason: 終了理由
        """
        for tool_use_id, wrapper in list(self._pending_spans.items()):
            wrapper.set_warning(f"Span ended due to: {reason}")
            wrapper.set_output(f"(no result - {reason})")
            wrapper.end()
        self._pending_spans.clear()

    def create_generation(
        self,
        parent: "SpanWrapper",
        name: str = "llm_response",
        input: Any = None,
        output: Any = None,
        model: Optional[str] = None,
        metrics: Optional[AgentMetrics] = None,
        tool_call_count: int = 0,
    ):
        """LLM Generation を作成・終了.

        Args:
            parent: 親スパンラッパー
            name: Generation名
            input: 入力
            output: 出力
            model: モデル名
            metrics: メトリクス
            tool_call_count: ツール呼び出し数
        """
        generation = parent._span.start_generation(
            name=name,
            model=model or self.config.model,
            input=input,
            output=output,
            model_parameters={
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            },
        )

        if metrics:
            generation.update(
                usage=metrics.to_langfuse_usage(),
                metadata={
                    **metrics.to_langfuse_metadata(),
                    "response_length": len(str(output)) if output else 0,
                    "tool_calls": tool_call_count,
                },
            )
        else:
            generation.update(
                metadata={
                    "response_length": len(str(output)) if output else 0,
                    "tool_calls": tool_call_count,
                    "metrics_available": False,
                },
            )

        generation.end()

    def flush(self):
        """トレースをフラッシュ."""
        _langfuse.flush()

    def shutdown(self):
        """クライアントをシャットダウン."""
        _langfuse.shutdown()


class SpanWrapper:
    """スパンラッパー.

    スパンの操作を簡略化し、レベル設定などを統一的に扱う。
    """

    def __init__(
        self,
        span: Any,
        tracer: LangfuseTracer,
        is_tool: bool = False,
    ):
        """初期化.

        Args:
            span: Langfuse スパン
            tracer: トレーサー
            is_tool: ツールスパンかどうか
        """
        self._span = span
        self._tracer = tracer
        self._is_tool = is_tool
        self._ended = False
        self._level = "DEFAULT"
        self._status_message: Optional[str] = None

    def set_output(self, output: Any):
        """出力を設定.

        Args:
            output: 出力データ
        """
        self._span.update(output=output)

    def set_error(self, message: str):
        """エラーを設定.

        Args:
            message: エラーメッセージ
        """
        self._level = "ERROR"
        self._status_message = message
        self._span.update(level="ERROR", status_message=message)

    def set_warning(self, message: str):
        """警告を設定.

        Args:
            message: 警告メッセージ
        """
        self._level = "WARNING"
        self._status_message = message
        self._span.update(level="WARNING", status_message=message)

    def update_metadata(self, metadata: dict):
        """メタデータを更新.

        Args:
            metadata: 追加メタデータ
        """
        self._span.update(metadata=metadata)

    def score(self, name: str, value: float, comment: Optional[str] = None):
        """スコアを設定.

        Args:
            name: スコア名
            value: スコア値（0.0-1.0）
            comment: コメント
        """
        self._span.score(name=name, value=value, comment=comment)

    def start_child_span(
        self,
        name: str,
        input: Any = None,
        metadata: Optional[dict] = None,
    ) -> "SpanWrapper":
        """子スパンを開始.

        Args:
            name: スパン名
            input: 入力データ
            metadata: メタデータ

        Returns:
            SpanWrapper: 子スパンラッパー
        """
        child_span = self._span.start_span(
            name=name,
            input=input,
            metadata=metadata,
        )
        return SpanWrapper(child_span, self._tracer)

    def end(self):
        """スパンを終了."""
        if not self._ended:
            self._span.end()
            self._ended = True


# シンプルなファクトリー関数
def create_tracer(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tags: Optional[list[str]] = None,
    environment: str = "development",
    aws_region: str = "us-east-1",
    model: str = "",
    tools: Optional[list[str]] = None,
) -> LangfuseTracer:
    """トレーサーを作成.

    Args:
        session_id: セッションID
        user_id: ユーザーID
        tags: タグ
        environment: 環境名
        aws_region: AWSリージョン
        model: モデル名
        tools: ツールリスト

    Returns:
        LangfuseTracer: トレーサー
    """
    config = TracingConfig(
        session_id=session_id,
        user_id=user_id,
        tags=tags or [],
        environment=environment,
        aws_region=aws_region,
        model=model,
        tools=tools,
    )
    return LangfuseTracer(config)
