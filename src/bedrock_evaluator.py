"""Bedrock Haiku を評価用LLMとして使用するためのカスタムクラス.

DeepEvalBaseLLM を継承して、LangChain の ChatBedrock を
DeepEval で使用できるようにラップします。
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# DeepEval と LangChain のインポート
try:
    from deepeval.models.base_model import DeepEvalBaseLLM
    DEEPEVAL_BASE_AVAILABLE = True
except ImportError:
    DEEPEVAL_BASE_AVAILABLE = False
    # フォールバック用のダミークラス
    class DeepEvalBaseLLM:
        pass

try:
    from langchain_aws import ChatBedrock
    LANGCHAIN_AWS_AVAILABLE = True
except ImportError:
    LANGCHAIN_AWS_AVAILABLE = False


class BedrockEvaluator(DeepEvalBaseLLM):
    """AWS Bedrock を DeepEval で使用するためのラッパークラス.

    DeepEvalBaseLLM を継承し、LangChain の ChatBedrock を
    DeepEval のメトリクスで使用できるようにします。

    Example:
        >>> evaluator = BedrockEvaluator(
        ...     model_id="anthropic.claude-3-haiku-20240307-v1:0"
        ... )
        >>> from deepeval.metrics import AnswerRelevancyMetric
        >>> metric = AnswerRelevancyMetric(model=evaluator, threshold=0.7)
    """

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        region_name: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ):
        """Initialize Bedrock Evaluator.

        Args:
            model_id: Bedrock モデルID
            region_name: AWS リージョン
            temperature: サンプリング温度（評価は決定論的に0.0推奨）
            max_tokens: 最大トークン数
        """
        if not LANGCHAIN_AWS_AVAILABLE:
            raise ImportError(
                "langchain-aws is required. Install with: uv pip install langchain-aws"
            )

        self.model_id = model_id
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self.temperature = temperature
        self.max_tokens = max_tokens

        # ChatBedrock インスタンスを作成
        self._model = ChatBedrock(
            model_id=model_id,
            region_name=self.region_name,
            model_kwargs={
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )

    def load_model(self) -> ChatBedrock:
        """モデルオブジェクトを返す（DeepEvalBaseLLM 必須メソッド）.

        Returns:
            ChatBedrock インスタンス
        """
        return self._model

    def generate(self, prompt: str, schema: Optional[type] = None):
        """テキスト生成（DeepEvalBaseLLM 必須メソッド）.

        Args:
            prompt: 生成プロンプト
            schema: Pydantic モデル（オプション、structured output用）

        Returns:
            生成されたテキスト（schema が None の場合）
            または Pydantic モデルインスタンス（schema が指定された場合）
        """
        chat_model = self.load_model()

        # schema が指定されている場合は structured output を使用
        if schema is not None:
            structured_model = chat_model.with_structured_output(schema)
            response = structured_model.invoke(prompt)
            # Pydantic モデルインスタンスをそのまま返す
            return response

        # 通常の生成
        response = chat_model.invoke(prompt)
        return response.content

    async def a_generate(self, prompt: str, schema: Optional[type] = None):
        """非同期テキスト生成（DeepEvalBaseLLM 必須メソッド）.

        Args:
            prompt: 生成プロンプト
            schema: Pydantic モデル（オプション、structured output用）

        Returns:
            生成されたテキスト（schema が None の場合）
            または Pydantic モデルインスタンス（schema が指定された場合）
        """
        chat_model = self.load_model()

        # schema が指定されている場合は structured output を使用
        if schema is not None:
            structured_model = chat_model.with_structured_output(schema)
            response = await structured_model.ainvoke(prompt)
            # Pydantic モデルインスタンスをそのまま返す
            return response

        # 通常の生成
        response = await chat_model.ainvoke(prompt)
        return response.content

    def get_model_name(self) -> str:
        """モデル名を返す（DeepEvalBaseLLM 必須メソッド）.

        Returns:
            モデル名
        """
        return f"AWS Bedrock {self.model_id}"


def create_bedrock_evaluator(
    model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
    temperature: float = 0.0,
) -> BedrockEvaluator:
    """DeepEval で使用する Bedrock 評価器を作成.

    Args:
        model_id: Bedrock モデルID
        temperature: サンプリング温度

    Returns:
        BedrockEvaluator インスタンス

    Example:
        >>> evaluator = create_bedrock_evaluator()
        >>> from deepeval.metrics import AnswerRelevancyMetric
        >>> metric = AnswerRelevancyMetric(model=evaluator, threshold=0.7)
    """
    return BedrockEvaluator(
        model_id=model_id,
        temperature=temperature,
    )


if __name__ == "__main__":
    # テスト
    if DEEPEVAL_BASE_AVAILABLE and LANGCHAIN_AWS_AVAILABLE:
        evaluator = create_bedrock_evaluator()
        print(f"Model name: {evaluator.get_model_name()}")

        # 同期テスト
        response = evaluator.generate("Say 'Hello, World!' in Japanese")
        print(f"Response: {response}")
    else:
        if not DEEPEVAL_BASE_AVAILABLE:
            print("❌ DeepEval not installed. Run: uv pip install deepeval")
        if not LANGCHAIN_AWS_AVAILABLE:
            print("❌ langchain-aws not installed. Run: uv pip install langchain-aws")
