# ADR-002: 評価に DeepEval + Langfuse を採用

## ステータス

**採用（Accepted）** - 2024-12-09

## コンテキスト

AI エージェントの品質を継続的に評価・監視するために、以下の要件を満たすツールが必要である：

1. **評価**: エージェント出力の品質を自動評価（回答関連性、幻覚検出、ツール使用正確性等）
2. **監視**: 本番環境でのトレース収集、可視化、異常検知
3. **回帰テスト**: プロンプト変更時の品質劣化検出
4. **日本国内データ保存**: 個人情報を含むトレース情報は日本国内に保存する必要がある
5. **コスト効率**: 評価 LLM のコストを抑える

## 検討した選択肢

### 評価ツール

| ツール | 主な機能 | データロケーション | 日本対応 |
|--------|---------|-------------------|---------|
| **DeepEval** | 汎用 LLM 評価 | ローカル実行 | ✅ |
| **Ragas** | RAG 評価特化 | ローカル実行 | ✅ |
| **promptfoo** | プロンプト A/B テスト | ローカル実行 | ✅ |
| **TruLens** | フィードバック評価 | ローカル実行 | ✅ |
| **Braintrust** | 評価+監視統合 | US のみ | ❌ |
| **Confident AI** | DeepEval クラウド | US のみ | ❌ |

### 監視・トレースツール

| ツール | 主な機能 | データロケーション | 日本対応 |
|--------|---------|-------------------|---------|
| **Langfuse** | トレース・監視 | セルフホスト可 | ✅ |
| **Arize Phoenix** | トレース可視化 | セルフホスト可 | ✅ |
| **LangSmith** | トレース+評価 | US のみ | ❌ |
| **Datadog LLM** | 監視 | Tokyo 有 | △ 要確認 |

## 決定

**評価には DeepEval、監視には Langfuse（セルフホスト）を採用する。**

```
┌─────────────────────────────────────────────────────────────┐
│                    採用構成                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌────────────────┐    │
│  │  DeepEval   │   │  Langfuse   │   │ baseline.json  │    │
│  │ (評価実行)  │   │ (トレース)  │   │ (回帰管理)     │    │
│  │  ローカル   │   │ セルフホスト │   │   git管理      │    │
│  └──────┬──────┘   └──────┬──────┘   └───────┬────────┘    │
│         │                 │                   │             │
│         ▼                 ▼                   ▼             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            AWS Tokyo リージョン                      │   │
│  │  ・Bedrock Haiku (評価 LLM)                         │   │
│  │  ・Langfuse (ECS + RDS)                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ✅ すべてのデータが日本国内に保存される                     │
└─────────────────────────────────────────────────────────────┘
```

## 理由

### DeepEval を採用する理由

1. **ローカル実行**: 評価処理がローカルで実行され、外部サービスへのデータ送信が不要

2. **Bedrock 対応**: DeepEvalBaseLLM を継承したカスタムクラス（BedrockEvaluator）により、評価 LLM として Bedrock Claude 3 Haiku（東京リージョン）を使用可能

3. **豊富なメトリクス**: Answer Relevancy, Faithfulness, Hallucination, Contextual Relevancy 等の組み込みメトリクス + GEval によるカスタムメトリクス

4. **pytest 統合**: CI/CD パイプラインに組み込みやすい

5. **コスト効率**: Bedrock Haiku を評価 LLM として使用することで、GPT-4 比で約 99% のコスト削減

### Langfuse を採用する理由

1. **セルフホスト対応**: AWS Tokyo（ECS + RDS）に構築することで、日本国内データレジデンシー要件を満たす

2. **OSS**: オープンソースで透明性が高く、ベンダーロックインを回避

3. **トレース可視化**: 直感的なダッシュボードでエージェントの動作を可視化

4. **スコア記録**: DeepEval の評価結果を Langfuse に送信し、長期的なトレンドを追跡可能

5. **Python SDK**: `@observe()` デコレーターで簡単にトレーシングを追加可能

### Braintrust / LangSmith を不採用とする理由

1. **データロケーション**: どちらも US にしかデータを保存できない

2. **セルフホスト不可**: オンプレミス/自社クラウドへのデプロイオプションがない

3. **日本国内データレジデンシー要件を満たせない**

機能面では Braintrust が最も優れているが、データレジデンシー要件により採用不可。

## 実装詳細

### 評価メトリクス

```python
# 軽量セット（日常テスト用）
- Response Quality      # 回答品質（GEval）
- Answer Relevancy      # 回答関連性
- Tool Usage Correctness # ツール使用正確性（GEval）
- Japanese Language Quality # 日本語品質（GEval）

# 完全セット（詳細評価用）
- 上記 + Faithfulness, Hallucination, Contextual Relevancy
```

### テスト方式

```
評価パス条件:
├── 絶対閾値:    スコア ≥ 0.75（最低品質保証）
└── 回帰チェック: 前回比 -5% 以内（劣化防止）
```

### コスト試算

| 項目 | 月額 |
|------|------|
| 評価実行（Bedrock Haiku） | ~$30 |
| Langfuse インフラ（ECS + RDS） | ~$50 |
| **合計** | **~$80** |

## 結果

- DeepEval + Bedrock Haiku による評価スクリプトを実装（src/run_evaluation_deepeval.py）
- BedrockEvaluator クラスを実装（src/bedrock_evaluator.py）
- 評価結果を Langfuse に送信する機能を実装
- テスト戦略ドキュメントを作成（docs/evaluation/testing-strategy.md）

## 今後の拡張

| フェーズ | 追加ツール | 用途 |
|---------|-----------|------|
| RAG 機能追加時 | Ragas | RAG 評価（Context Precision/Recall） |
| プロンプト最適化 | promptfoo | A/B テスト |
| セキュリティ強化 | Giskard | プロンプトインジェクション検出 |

## 参考

- [DeepEval Documentation](https://docs.confident-ai.com/)
- [Langfuse Documentation](https://langfuse.com/docs)
- [Langfuse Self-Hosting Guide](https://langfuse.com/docs/deployment/self-host)
- [テスト戦略ドキュメント](../evaluation/testing-strategy.md)
