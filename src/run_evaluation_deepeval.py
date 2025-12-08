"""DeepEval を使用した Claude Agent SDK の評価スクリプト."""

from __future__ import annotations

import asyncio
import json
import os
from typing import List, Dict, Any, Union
from pathlib import Path

# DeepEval imports (インストール後に有効化)
try:
    from deepeval import evaluate
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        FaithfulnessMetric,
        ContextualRelevancyMetric,
        HallucinationMetric,
        GEval,
    )
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False

try:
    from agent import BedrockAgentSDK
except ImportError:
    from src.agent import BedrockAgentSDK

from langfuse import get_client

# Bedrock Evaluator (カスタム評価用LLM)
EVALUATION_MODEL = None
EVALUATION_MODEL_NAME = "unknown"

try:
    try:
        from bedrock_evaluator import create_bedrock_evaluator, LANGCHAIN_AWS_AVAILABLE
    except ImportError:
        from src.bedrock_evaluator import create_bedrock_evaluator, LANGCHAIN_AWS_AVAILABLE

    if LANGCHAIN_AWS_AVAILABLE:
        # DeepEvalBaseLLM 経由で Bedrock Haiku を使用
        EVALUATION_MODEL = create_bedrock_evaluator(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
        )
        EVALUATION_MODEL_NAME = "Bedrock Claude 3 Haiku (via DeepEvalBaseLLM)"
    else:
        # langchain-aws がインストールされていない
        EVALUATION_MODEL = "gpt-4"
        EVALUATION_MODEL_NAME = "OpenAI GPT-4 (langchain-aws not installed)"
except ImportError:
    # Bedrock evaluator がインポートできない
    EVALUATION_MODEL = "gpt-4"
    EVALUATION_MODEL_NAME = "OpenAI GPT-4 (bedrock_evaluator.py not found)"

# Langfuse client
langfuse = get_client()


def load_evaluation_dataset(dataset_path: str) -> List[Dict[str, Any]]:
    """評価用データセットを読み込む.

    Args:
        dataset_path: データセットファイルのパス

    Returns:
        テストケースのリスト
    """
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("test_cases", [])


def create_custom_metrics():
    """カスタム評価メトリクスを作成.

    Returns:
        カスタムメトリクスのリスト
    """
    if not DEEPEVAL_AVAILABLE:
        return []

    # 1. ツール使用の正確性
    tool_usage_metric = GEval(
        name="Tool Usage Correctness",
        criteria=(
            "エージェントが適切なツールを選択し、正しく実行したかを評価します。"
            "評価基準:"
            "- ツール選択の妥当性（タスクに適したツールか）"
            "- ツール実行の成功（エラーなく完了したか）"
            "- 期待される結果の生成（意図した出力が得られたか）"
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.CONTEXT,
        ],
        threshold=0.8,
        model=EVALUATION_MODEL,  # Bedrock Haiku を使用
    )

    # 2. レスポンス品質
    response_quality_metric = GEval(
        name="Response Quality",
        criteria=(
            "回答の総合的な品質を評価します。"
            "評価基準:"
            "- 明確性: 回答は理解しやすいか"
            "- 簡潔性: 冗長でないか"
            "- 有用性: ユーザーの問題を解決するか"
            "- 正確性: 事実に基づいているか"
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=0.75,
        model=EVALUATION_MODEL,  # Bedrock Haiku を使用
    )

    # 3. 日本語品質
    japanese_quality_metric = GEval(
        name="Japanese Language Quality",
        criteria=(
            "日本語の品質を評価します。"
            "評価基準:"
            "- 文法の正確性"
            "- 自然な表現"
            "- 敬語の適切な使用"
            "- 文脈に応じた言葉遣い"
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=0.8,
        model=EVALUATION_MODEL,  # Bedrock Haiku を使用
    )

    return [
        tool_usage_metric,
        response_quality_metric,
        japanese_quality_metric,
    ]


def create_standard_metrics():
    """標準評価メトリクスを作成.

    Returns:
        標準メトリクスのリスト
    """
    if not DEEPEVAL_AVAILABLE:
        return []

    return [
        AnswerRelevancyMetric(
            threshold=0.7,
            model=EVALUATION_MODEL,  # Bedrock Haiku を使用
        ),
        FaithfulnessMetric(
            threshold=0.8,
            model=EVALUATION_MODEL,  # Bedrock Haiku を使用
        ),
        ContextualRelevancyMetric(
            threshold=0.7,
            model=EVALUATION_MODEL,  # Bedrock Haiku を使用
        ),
        HallucinationMetric(
            threshold=0.5,
            model=EVALUATION_MODEL,  # Bedrock Haiku を使用
        ),
    ]


async def run_agent_on_test_case(
    agent: BedrockAgentSDK,
    test_case: Dict[str, Any],
    index: int,
) -> tuple[Union[LLMTestCase, Dict[str, Any]], str]:
    """テストケースに対してエージェントを実行.

    Args:
        agent: Bedrock エージェント
        test_case: テストケースデータ
        index: テストケースのインデックス

    Returns:
        (LLMTestCase オブジェクト, trace_id)
    """
    print(f"  Running test case {index + 1}: {test_case['input'][:50]}...")

    # 手動でトレースを作成して trace_id を取得
    trace = langfuse.start_span(
        name=f"Evaluation Test Case {index + 1}",
        input=test_case["input"],
        metadata={
            "test_case_index": index,
            "expected_output": test_case.get("expected_output"),
        }
    )

    # エージェント実行
    actual_output = await agent.chat(
        prompt=test_case["input"],
        session_id=f"eval-{index}",
        user_id="evaluator",
    )

    # トレースを更新して終了
    trace.update(output=actual_output)
    trace.end()

    if not DEEPEVAL_AVAILABLE:
        # DeepEval が利用不可の場合はダミーオブジェクトを返す
        return {
            "input": test_case["input"],
            "actual_output": actual_output,
            "expected_output": test_case.get("expected_output"),
        }, trace.id

    # LLMTestCase 作成
    test_case_obj = LLMTestCase(
        input=test_case["input"],
        actual_output=actual_output,
        expected_output=test_case.get("expected_output"),
        context=test_case.get("context", []),
        retrieval_context=test_case.get("retrieval_context", []),
    )

    return test_case_obj, trace.id


async def run_evaluation_simple(
    dataset_path: str = "datasets/evaluation_dataset.json",
    use_custom_metrics: bool = True,
):
    """シンプルな評価を実行.

    Args:
        dataset_path: 評価データセットのパス
        use_custom_metrics: カスタムメトリクスを使用するか
    """
    if not DEEPEVAL_AVAILABLE:
        print("\n" + "=" * 60)
        print("❌ DeepEval が見つかりません")
        print("=" * 60)
        print("\n以下のコマンドでインストールしてください：")
        print("  make eval-setup")
        print("\nまたは手動で：")
        print("  uv pip install -e \".[evaluation]\"")
        print("\n" + "=" * 60)
        return

    print("=" * 60)
    print("DeepEval による Claude Agent SDK 評価")
    print("=" * 60)
    print(f"\n🤖 評価用LLM: {EVALUATION_MODEL_NAME}")

    # データセット読み込み
    print(f"\n📁 Loading dataset: {dataset_path}")
    test_data = load_evaluation_dataset(dataset_path)
    print(f"   Loaded {len(test_data)} test cases")

    # エージェント初期化
    print("\n🤖 Initializing agent...")
    agent = BedrockAgentSDK()

    # テストケース実行
    print("\n🚀 Running test cases...")
    test_cases = []
    trace_ids = []
    for i, test_item in enumerate(test_data):
        test_case, trace_id = await run_agent_on_test_case(agent, test_item, i)
        test_cases.append(test_case)
        trace_ids.append(trace_id)
        break  # デバッグ用に1ケースのみ実行

    # メトリクス準備
    print("\n📊 Preparing metrics...")
    metrics = create_standard_metrics()

    if use_custom_metrics:
        custom_metrics = create_custom_metrics()
        metrics.extend(custom_metrics)
        print(f"   Using {len(metrics)} metrics ({len(custom_metrics)} custom)")
    else:
        print(f"   Using {len(metrics)} standard metrics")

    # 評価実行
    print("\n⚙️  Evaluating...")
    results = evaluate(test_cases=test_cases, metrics=metrics)

    # 結果を Langfuse に送信
    print("\n📤 Sending evaluation scores to Langfuse...")
    test_results = getattr(results, 'test_results', [])

    scores_sent = 0
    for idx, test_result in enumerate(test_results):
        if idx >= len(trace_ids):
            break

        trace_id = trace_ids[idx]

        # 各メトリクスのスコアを送信
        if hasattr(test_result, 'metrics_data'):
            for metric_data in test_result.metrics_data:
                langfuse.create_score(
                    name=metric_data.name,
                    value=metric_data.score,
                    trace_id=trace_id,
                    comment=metric_data.reason if hasattr(metric_data, 'reason') else None,
                )
                scores_sent += 1

    langfuse.flush()
    print(f"   Sent {scores_sent} scores to Langfuse across {len(test_results)} test cases")

    # 結果サマリー
    print("\n" + "=" * 60)
    print("評価結果サマリー")
    print("=" * 60)

    print(f"テストケース数: {len(test_cases)}")
    print(f"メトリクス数: {len(metrics)}")
    print(f"評価モデル: {EVALUATION_MODEL_NAME}")
    print(f"Langfuse スコア: {scores_sent} 件")

    # 詳細な結果は DeepEval のコンソール出力に表示されています
    print("\n✅ Evaluation completed!")
    print(f"📊 詳細な結果は上記の DeepEval 出力を参照してください")
    print(f"\n💡 結果の確認方法:")
    print(f"  - DeepEval ダッシュボード: deepeval view")
    print(f"  - Langfuse ダッシュボード: https://cloud.langfuse.com")
    print(f"\n✨ 評価スコアは Langfuse のトレースに記録されました！")


async def run_evaluation_with_report(
    dataset_path: str = "datasets/evaluation_dataset.json",
    output_path: str = "evaluation_report.json",
):
    """詳細レポート付きの評価を実行.

    Args:
        dataset_path: 評価データセットのパス
        output_path: レポート出力パス
    """
    await run_evaluation_simple(dataset_path)

    # レポート作成（実装は省略）
    print(f"\n📄 Report saved to: {output_path}")


async def main():
    """メイン関数."""
    # 環境変数チェック
    required_vars = [
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_PUBLIC_KEY",
        #"AWS_ACCESS_KEY_ID",     # Bedrock 用
        #"AWS_SECRET_ACCESS_KEY",  # Bedrock 用
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("   Please set them in .env file")
        return

    # 評価実行
    await run_evaluation_simple(
        dataset_path="datasets/evaluation_dataset.json",
        use_custom_metrics=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
