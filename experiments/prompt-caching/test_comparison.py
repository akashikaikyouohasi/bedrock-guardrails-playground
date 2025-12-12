"""Prompt Caching あり・なしの比較テスト.

このスクリプトは、同じ質問をキャッシュ有効・無効で実行し、
レイテンシとコストの違いを確認します。
"""

import asyncio
import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent import BedrockAgentSDK


async def test_comparison():
    """キャッシュあり・なしの比較テスト."""
    print("=" * 70)
    print("Prompt Caching 比較テスト")
    print("=" * 70)
    print()

    # 長いシステムプロンプト
    long_system_prompt = """あなたは技術文書の専門家です。

以下の AWS Bedrock に関する詳細なドキュメントに基づいて回答してください。

【AWS Bedrock 完全ガイド】

## 第1章: Bedrock の概要

Amazon Bedrock は、高性能な基盤モデル（FM）を API 経由で利用できる
フルマネージドサービスです。Claude、Llama、Stable Diffusion など、
複数のモデルプロバイダーのモデルにアクセスできます。

主な特徴:
- マネージドサービス: インフラ管理不要
- セキュアなアクセス: VPC エンドポイント対応
- スケーラブル: 自動スケーリング
- 複数モデル対応: 用途に応じて選択可能

## 第2章: Claude モデルファミリー

Anthropic が開発した Claude モデルは、以下の特徴があります:

1. Claude 3 Opus: 最高性能モデル
   - 複雑な推論タスクに最適
   - 200K コンテキストウィンドウ
   - 多言語対応

2. Claude 3.5 Sonnet: バランスモデル
   - コストとパフォーマンスのバランス
   - 200K コンテキストウィンドウ
   - ストリーミング対応

3. Claude 3 Haiku: 高速モデル
   - 低レイテンシ
   - コスト効率的
   - リアルタイム用途に最適

## 第3章: Prompt Caching

Prompt Caching は、頻繁に使用されるプロンプトをキャッシュして、
レイテンシとコストを削減する機能です。

主な効果:
- レイテンシ: 最大 85% 削減
- コスト: 最大 90% 削減
- TTL: 5分間

適用条件:
- 最小トークン数: 1,024 トークン以上
- 静的コンテンツ: プレフィックスが同一
- リクエスト間隔: 5分以内

## 第4章: Bedrock Guardrails

責任ある AI を実現するための包括的なツールセット:

1. コンテンツフィルタ
2. PII 検出・マスキング
3. トピック拒否
4. ワードフィルター
5. 文脈グラウンディング

## 第5章: ベストプラクティス

1. モデル選択
   - タスクの複雑さに応じて選択
   - コストとパフォーマンスのバランス

2. プロンプト設計
   - 明確な指示
   - 具体的な例の提供
   - システムプロンプトの活用

3. エラーハンドリング
   - リトライロジック
   - タイムアウト設定
   - エラーログの記録

4. コスト最適化
   - Prompt Caching の活用
   - 適切なモデル選択
   - バッチ処理の検討

---
このドキュメントは約1,500トークンです。
"""

    # 短いシステムプロンプト（キャッシュされない）
    short_system_prompt = "あなたは技術アシスタントです。"

    question = "Prompt Caching の効果について教えてください"

    print("テスト1: 短いシステムプロンプト（キャッシュなし）")
    print("-" * 70)
    print(f"システムプロンプト: {len(short_system_prompt)} 文字")
    print(f"質問: {question}")
    print()

    agent_short = BedrockAgentSDK(
        system_prompt=short_system_prompt,
        model="anthropic.claude-3-7-sonnet-20250219-v1:0"
    )

    # 短いプロンプトで3回実行
    short_times = []
    for i in range(3):
        start = time.time()

        response = await agent_short.chat(
            prompt=question,
            session_id=f"short-{i}",
            user_id="tester"
        )

        elapsed = time.time() - start
        short_times.append(elapsed)
        print(f"  実行{i+1}: {elapsed:.2f}秒")

    avg_short = sum(short_times) / len(short_times)
    print(f"\n平均実行時間: {avg_short:.2f}秒")
    print()

    await asyncio.sleep(2)

    print("=" * 70)
    print("テスト2: 長いシステムプロンプト（キャッシュあり）")
    print("-" * 70)
    print(f"システムプロンプト: {len(long_system_prompt)} 文字")
    print(f"質問: {question}")
    print()

    agent_long = BedrockAgentSDK(
        system_prompt=long_system_prompt,
        model="anthropic.claude-3-7-sonnet-20250219-v1:0"
    )

    # 長いプロンプトで3回実行
    long_times = []
    for i in range(3):
        start = time.time()

        response = await agent_long.chat(
            prompt=question,
            session_id=f"long-{i}",
            user_id="tester"
        )

        elapsed = time.time() - start
        long_times.append(elapsed)

        if i == 0:
            print(f"  実行{i+1}: {elapsed:.2f}秒 （キャッシュ書き込み）")
        else:
            print(f"  実行{i+1}: {elapsed:.2f}秒 （キャッシュ読み取り）")

        if i < 2:
            await asyncio.sleep(2)  # TTL 内で実行

    avg_long = sum(long_times) / len(long_times)
    avg_long_cached = sum(long_times[1:]) / len(long_times[1:])

    print(f"\n平均実行時間（全体）: {avg_long:.2f}秒")
    print(f"平均実行時間（キャッシュ読み取りのみ）: {avg_long_cached:.2f}秒")
    print()

    print("=" * 70)
    print("📊 結果サマリー")
    print("=" * 70)
    print()

    print(f"短いプロンプト（キャッシュなし）:")
    print(f"  平均実行時間: {avg_short:.2f}秒")
    print()

    print(f"長いプロンプト（キャッシュあり）:")
    print(f"  初回（書き込み）: {long_times[0]:.2f}秒")
    print(f"  2回目以降（読み取り）: {avg_long_cached:.2f}秒")
    print()

    if avg_long_cached < long_times[0]:
        improvement = ((long_times[0] - avg_long_cached) / long_times[0]) * 100
        print(f"🎉 キャッシュヒットによる高速化: {improvement:.1f}%")
    else:
        print("ℹ️  キャッシュ効果は個別のメトリクスで確認してください")

    print()
    print("💡 詳細なキャッシュメトリクスを確認:")
    print("   python experiments/prompt-caching/check_cache_metrics.py")
    print()


if __name__ == "__main__":
    asyncio.run(test_comparison())
