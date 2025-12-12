"""Prompt Caching の基本的な動作確認スクリプト.

このスクリプトは、同一のシステムプロンプトで複数回リクエストを送信し、
Prompt Caching の効果を確認します。
"""

import asyncio
import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent import BedrockAgentSDK


async def test_basic_caching():
    """基本的な Prompt Caching テスト."""
    print("=" * 70)
    print("Prompt Caching 基本テスト")
    print("=" * 70)
    print()

    # 長いシステムプロンプト（1,024トークン以上でキャッシュされる）
    system_prompt = """あなたは AWS Bedrock の専門家です。

以下のドキュメントに基づいて、ユーザーの質問に回答してください。

【AWS Bedrock Guardrails 詳細ドキュメント】

## 概要
Amazon Bedrock Guardrails は、生成AIアプリケーションに責任あるAI
ポリシーを実装するための包括的なツールセットです。有害なコンテンツの
フィルタリング、個人情報の保護、トピックの制限など、複数の機能を提供します。

## 主な機能

### 1. コンテンツフィルタ
以下のカテゴリで有害コンテンツをフィルタリング：
- 暴力的な表現
- 性的なコンテンツ
- 侮辱的な言葉
- ヘイトスピーチ

各カテゴリについて、LOW、MEDIUM、HIGH の3つの閾値を設定可能です。

### 2. PII（個人情報）検出とマスキング
以下の個人情報を検出・マスキング：
- 氏名
- メールアドレス
- 電話番号
- 住所
- クレジットカード番号
- 運転免許証番号

日本の個人情報形式（電話番号、住所等）にも対応しています。

### 3. トピック拒否
特定のトピックに関する質問をブロック：
- 競合他社に関する情報
- 機密情報
- 禁止された話題

### 4. ワードフィルター
特定の単語やフレーズをブロックまたは置換：
- 禁止語句リスト
- 正規表現パターン
- 大文字小文字の区別

### 5. 文脈グラウンディング
モデルの出力が提供されたコンテキストに基づいているかを検証：
- 幻覚（Hallucination）の検出
- 情報源との整合性確認

## ApplyGuardrail API

リアルタイムでコンテンツをチェックするための API です。

### INPUT チェック
ユーザーのプロンプトを LLM に送信する前にチェックします。
ブロックされた場合、LLM の実行コストが発生しません。

### OUTPUT チェック
LLM の出力をユーザーに返す前にチェックします。
ストリーミング中にもリアルタイムでチェック可能です。

## 料金
Guardrails の使用料金は、処理されるテキストユニット数に基づきます：
- INPUT チェック: $0.75/1,000 テキストユニット
- OUTPUT チェック: $1.00/1,000 テキストユニット

テキストユニット = 1,000文字（または画像の場合は異なる単位）

## ベストプラクティス

1. **段階的な導入**: まず低い閾値から開始し、徐々に調整
2. **複数の機能を組み合わせる**: コンテンツフィルタ + PII + トピック拒否
3. **定期的な見直し**: フィルタの効果を確認し、調整
4. **ログの監視**: ブロックされたケースを分析し、改善

## 制限事項

- 最大テキストサイズ: 1 MB
- バッチ処理: 未対応（1リクエストずつ処理）
- リージョン: 特定のリージョンでのみ利用可能

---

このドキュメントは約1,200トークンあり、Prompt Caching の対象となります。
"""

    # BedrockAgentSDK を初期化（system_prompt 付き）
    print("📝 BedrockAgentSDK を初期化中...")
    agent = BedrockAgentSDK(
        system_prompt=system_prompt,
        model="anthropic.claude-3-7-sonnet-20250219-v1:0"
    )
    print("✅ 初期化完了")
    print()

    # 質問リスト
    questions = [
        "Guardrails のコンテンツフィルタについて教えて",
        "PII 検出機能はどのような個人情報に対応していますか？",
        "ApplyGuardrail API の料金体系は？",
    ]

    # 各質問を実行
    for i, question in enumerate(questions, 1):
        print("-" * 70)
        print(f"質問 {i}/{len(questions)}: {question}")
        print("-" * 70)

        start_time = time.time()

        # BedrockAgentSDK の chat() メソッドを使用
        response = await agent.chat(
            prompt=question,
            session_id=f"cache-test-{i}",
            user_id="tester"
        )

        elapsed = time.time() - start_time

        print(f"\n📊 実行時間: {elapsed:.2f}秒")
        print(f"\n💬 回答:\n{response}\n")

        if i == 1:
            print("ℹ️  1回目: キャッシュ書き込み（+25% コスト）")
        else:
            print("ℹ️  2回目以降: キャッシュ読み取り（-90% コスト、高速）")
        print()

        # 2回目以降のリクエストでキャッシュヒットを待つ
        if i < len(questions):
            print("⏳ 次の質問まで3秒待機...")
            await asyncio.sleep(3)

    print("=" * 70)
    print("✅ テスト完了")
    print("=" * 70)
    print()
    print("📈 キャッシュ効果の確認方法:")
    print("  1. CloudWatch メトリクスで確認:")
    print("     python experiments/prompt-caching/check_cache_metrics.py")
    print()
    print("  2. AWS CLI で確認:")
    print("     aws cloudwatch get-metric-statistics \\")
    print("       --namespace AWS/Bedrock \\")
    print("       --metric-name CacheReadInputTokens \\")
    print("       --dimensions Name=ModelId,Value=anthropic.claude-3-7-sonnet-20250219-v1:0 \\")
    print("       --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \\")
    print("       --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \\")
    print("       --period 3600 \\")
    print("       --statistics Sum \\")
    print("       --region ap-northeast-1")
    print()


if __name__ == "__main__":
    asyncio.run(test_basic_caching())
