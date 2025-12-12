"""Bedrock ログから Prompt Caching の効果を確認するスクリプト."""

import boto3
import os
import json
import time
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# 環境変数をロード
load_dotenv()


def check_cache_metrics(
    model_id: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    hours: int = 1
):
    """Prompt Caching メトリクスを確認.

    Args:
        model_id: 確認するモデル ID
        hours: 過去何時間分のメトリクスを取得するか
    """
    print("=" * 70)
    print("Prompt Caching メトリクス確認（Bedrock ログから取得）")
    print("=" * 70)
    print()

    region = os.getenv("AWS_REGION", "us-west-2")
    logs_client = boto3.client('logs', region_name=region)

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)

    print(f"📅 期間: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"      ～ {end_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"🌏 リージョン: {region}")
    print(f"🤖 モデル: {model_id}")
    print()

    # CloudWatch Logs Insights クエリ
    # モデルIDのARN形式とID形式の両方に対応
    # ARN: arn:aws:bedrock:region:account:inference-profile/global.anthropic.claude-haiku-4-5-20251001-v1:0
    query = f"""
    fields @timestamp, input.inputTokenCount, input.cacheReadInputTokenCount, input.cacheWriteInputTokenCount
    | filter modelId like /{model_id}/
    | stats
        sum(input.inputTokenCount) as totalInput,
        sum(input.cacheReadInputTokenCount) as totalCacheRead,
        sum(input.cacheWriteInputTokenCount) as totalCacheWrite,
        count(*) as requestCount
    """

    log_group = 'bedrock-logs'

    try:
        print("🔍 Bedrock ログを検索中...")

        # クエリを開始
        start_query_response = logs_client.start_query(
            logGroupName=log_group,
            startTime=int(start_time.timestamp()),
            endTime=int(end_time.timestamp()),
            queryString=query
        )

        query_id = start_query_response['queryId']

        # クエリ結果を待つ
        response = None
        max_wait = 30  # 最大30秒待つ
        elapsed = 0

        while elapsed < max_wait:
            time.sleep(1)
            elapsed += 1

            response = logs_client.get_query_results(queryId=query_id)

            if response['status'] == 'Complete':
                break
            elif response['status'] == 'Failed':
                print(f"❌ クエリ失敗: {response.get('statistics', {})}")
                return
            elif response['status'] in ['Cancelled', 'Timeout']:
                print(f"❌ クエリがキャンセルまたはタイムアウトしました")
                return

        if response['status'] != 'Complete':
            print(f"⚠️  クエリがタイムアウトしました（{max_wait}秒）")
            return

        results_data = response.get('results', [])

        if not results_data or len(results_data) == 0:
            print("⚠️  入力トークン総数: データなし")
            print("⚠️  キャッシュ読み取り: データなし")
            print("⚠️  キャッシュ書き込み: データなし")
            print()
            print("-" * 70)

            # データがない場合の処理
            print("ℹ️  指定期間にリクエストがありません")
            print()
            print("💡 次のステップ:")
            print("  1. テストスクリプトを実行:")
            print("     python experiments/prompt-caching/test_basic_caching.py")
            print()
            print("  2. 数分待ってから再度このスクリプトを実行")
            print()
            print("=" * 70)
            return

        # 結果を解析
        result_dict = {}
        for field in results_data[0]:
            result_dict[field['field']] = float(field['value']) if field['value'] else 0

        input_tokens = result_dict.get('totalInput', 0)
        cache_read = result_dict.get('totalCacheRead', 0)
        cache_write = result_dict.get('totalCacheWrite', 0)
        request_count = int(result_dict.get('requestCount', 0))

        print(f"✅ 入力トークン総数: {input_tokens:,.0f} トークン")
        print(f"✅ キャッシュ読み取り: {cache_read:,.0f} トークン")
        print(f"✅ キャッシュ書き込み: {cache_write:,.0f} トークン")
        print(f"📊 リクエスト数: {request_count} 件")
        print()
        print("-" * 70)

        results = {
            'InputTokens': input_tokens,
            'CacheReadInputTokens': cache_read,
            'CacheWriteInputTokens': cache_write,
        }

    except logs_client.exceptions.ResourceNotFoundException:
        print(f"❌ ロググループが見つかりません: {log_group}")
        print()
        print("💡 Bedrock のログを有効化する方法:")
        print()
        print("1. AWS コンソールで有効化:")
        print("   - Amazon Bedrock コンソール → Settings → Model invocation logging")
        print("   - CloudWatch Logs にログを送信するように設定")
        print(f"   - ロググループ名: {log_group}")
        print()
        print("2. AWS CLI で有効化:")
        print("   aws bedrock put-model-invocation-logging-configuration \\")
        print("     --logging-config '{")
        print('       "cloudWatchConfig": {')
        print(f'         "logGroupName": "{log_group}",')
        print('         "roleArn": "arn:aws:iam::YOUR_ACCOUNT:role/BedrockLoggingRole"')
        print("       },")
        print('       "textDataDeliveryEnabled": true,')
        print('       "imageDataDeliveryEnabled": false,')
        print('       "embeddingDataDeliveryEnabled": false')
        print("     }'")
        print()
        print("3. ログが有効化されるまで数分かかります")
        print()
        print("=" * 70)
        return
    except Exception as e:
        print(f"❌ ログ取得エラー: {e}")
        print()
        print("💡 トラブルシューティング:")
        print("  - IAM 権限を確認: logs:StartQuery, logs:GetQueryResults")
        print(f"  - リージョンが正しいか確認: AWS_REGION={region}")
        print()
        print("=" * 70)
        return

    # 統計情報を計算
    total_input_tokens = input_tokens + cache_read + cache_write

    if total_input_tokens > 0:
        cache_hit_rate = (cache_read / total_input_tokens) * 100

        # コスト削減率の計算
        # キャッシュ読み取り分は 90% オフ
        cost_reduction = (cache_read * 0.9 / total_input_tokens) * 100

        print("📊 統計情報")
        print("-" * 70)
        print(f"総入力トークン数: {total_input_tokens:,.0f} トークン")
        print(f"  - 新規入力: {input_tokens:,.0f} トークン")
        print(f"  - キャッシュ書き込み: {cache_write:,.0f} トークン")
        print(f"  - キャッシュ読み取り: {cache_read:,.0f} トークン")
        print()
        print(f"キャッシュヒット率: {cache_hit_rate:.2f}%")
        print(f"コスト削減率: 約 {cost_reduction:.1f}%")
        print()

        # 詳細なコスト計算
        non_cached = input_tokens  # 新規入力トークン（キャッシュされていない）

        print("💰 コスト内訳（トークン相当）")
        print("-" * 70)
        print(f"新規入力トークン:        {non_cached:>10,.0f} × 1.00 = {non_cached:>10,.0f}")
        print(f"キャッシュ書き込み:      {cache_write:>10,.0f} × 1.25 = {cache_write * 1.25:>10,.0f}")
        print(f"キャッシュ読み取り:      {cache_read:>10,.0f} × 0.10 = {cache_read * 0.10:>10,.0f}")
        print("-" * 70)

        total_cost = non_cached + (cache_write * 1.25) + (cache_read * 0.10)
        original_cost = total_input_tokens  # キャッシュなしの場合の総コスト
        saved = original_cost - total_cost

        print(f"実質コスト:              {total_cost:>10,.0f} トークン相当")
        print(f"元のコスト:              {original_cost:>10,.0f} トークン相当")
        print(f"削減額:                  {saved:>10,.0f} トークン ({saved/original_cost*100:.1f}%)")
        print()

        if cache_hit_rate > 50:
            print("🎉 キャッシュが効いています！")
            print("   2回目以降のリクエストで大幅なコスト削減とレイテンシ改善が")
            print("   実現されています。")
        elif cache_hit_rate > 0:
            print("✨ キャッシュが部分的に効いています")
            print("   さらに効果を高めるには、システムプロンプトを1,024トークン以上に")
            print("   することをお勧めします。")
        else:
            print("ℹ️  まだキャッシュヒットがありません")
            print("   初回リクエストではキャッシュ書き込みのみが行われます。")
            print("   2回目以降のリクエストでキャッシュヒットが発生します。")

    else:
        print("ℹ️  指定期間にリクエストがありません")
        print()
        print("💡 次のステップ:")
        print("  1. テストスクリプトを実行:")
        print("     python experiments/prompt-caching/test_basic_caching.py")
        print()
        print("  2. 数分待ってから再度このスクリプトを実行")

    print()
    print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prompt Caching メトリクスを確認")
    parser.add_argument(
        "--model-id",
        default="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        help="モデル ID（デフォルト: Claude Haiku 4.5）"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=1,
        help="過去何時間分のメトリクスを取得するか（デフォルト: 1）"
    )

    args = parser.parse_args()
    check_cache_metrics(model_id=args.model_id, hours=args.hours)
