# AIエージェント評価・テスト戦略

## 概要

本ドキュメントでは、Claude Agent SDK で構築した AI エージェントの評価・テスト戦略を定義します。

**前提条件: 日本国内データレジデンシー要件**

個人情報を含むトレース情報は日本国内に保存する必要があるため、この制約を満たすツール選定・構成を採用しています。

---

## 目次

1. [制約条件とツール選定](#制約条件とツール選定)
2. [推奨構成](#推奨構成)
3. [全体アーキテクチャ](#全体アーキテクチャ)
4. [開発フェーズ](#開発フェーズ)
5. [本番フェーズ](#本番フェーズ)
6. [評価指標](#評価指標)
7. [データセット管理](#データセット管理)
8. [CI/CD統合](#cicd統合)
9. [KPI設定](#kpi設定)
10. [コスト試算](#コスト試算)

---

## 制約条件とツール選定

### データレジデンシー要件

```
┌─────────────────────────────────────────────────────────┐
│  必須要件                                               │
│  ─────────────────────────────────────────────────────  │
│  ・個人情報を含むトレース情報は日本国内に保存            │
│  ・海外 SaaS へのデータ送信は不可                       │
│  ・評価データも同様に国内保存が望ましい                  │
└─────────────────────────────────────────────────────────┘
```

### ツール比較（データロケーション観点）

#### 評価ツール

| ツール | 主な機能 | データロケーション | セルフホスト | 採用可否 |
|--------|---------|-------------------|-------------|---------|
| **DeepEval** | 汎用LLM評価 | ローカル実行 | ✅ | ✅ **採用（メイン）** |
| **Ragas** | RAG評価特化 | ローカル実行 | ✅ | ✅ RAG使用時 |
| **promptfoo** | プロンプト比較・A/Bテスト | ローカル実行 | ✅ | ✅ プロンプト最適化時 |
| **TruLens** | フィードバック評価 | ローカル実行 | ✅ | △ 代替候補 |
| **Giskard** | ML/LLMテスト・脆弱性検出 | ローカル実行 | ✅ | △ セキュリティテスト時 |
| **Braintrust** | 評価+監視統合 | US のみ | ❌ 不可 | ❌ 不可 |
| **Confident AI** | DeepEval クラウド | US のみ | ❌ 不可 | ❌ 不可 |

#### 監視・トレースツール

| ツール | 主な機能 | データロケーション | セルフホスト | 採用可否 |
|--------|---------|-------------------|-------------|---------|
| **Langfuse** | トレース・監視・スコア | セルフホスト可 | ✅ | ✅ **採用（メイン）** |
| **Arize Phoenix** | トレース・可視化 | セルフホスト可 | ✅ | △ 代替候補 |
| **MLflow** | 実験管理・LLM評価 | セルフホスト可 | ✅ | △ ML統合が必要な場合 |
| **OpenLLMetry** | OpenTelemetry for LLM | ローカル実行 | ✅ | △ 既存OTel環境がある場合 |
| **LangSmith** | トレース+評価統合 | US のみ | ❌ 不可 | ❌ 不可 |
| **Datadog LLM** | 監視 | リージョン選択可 | ❌ 不可 | △ 要確認（Tokyo有） |
| **Helicone** | LLMプロキシ・監視 | US のみ | ❌ 不可 | ❌ 不可 |

### 各ツール詳細

#### DeepEval（✅ 採用：メイン評価ツール）

- ローカルで評価実行（外部へのデータ送信なし）
- 評価用 LLM に Bedrock（東京リージョン）を使用可能
- カスタムメトリクス定義が柔軟（GEval）
- pytest 統合で CI/CD に組み込みやすい
- 豊富な組み込みメトリクス（Answer Relevancy, Faithfulness, Hallucination 等）

#### Langfuse（✅ 採用：メイン監視ツール）

- **セルフホスト対応**（AWS Tokyo 等に構築可能）
- OSS で透明性が高い
- トレース可視化機能が充実
- スコア記録・ダッシュボード機能
- Python SDK が使いやすい

#### Ragas（✅ 採用：RAG評価時）

- RAG パイプライン評価に特化
- Context Precision, Context Recall, Answer Correctness 等
- ローカル実行で日本対応 ✅
- DeepEval と併用可能
- **用途:** RAG 機能を実装する場合に追加

#### promptfoo（✅ 採用：プロンプト最適化時）

- プロンプトの A/B テスト・比較評価
- 複数モデル間の比較が容易
- YAML ベースの設定で簡単
- ローカル CLI 実行で日本対応 ✅
- **用途:** プロンプト改善・最適化フェーズ

#### TruLens（△ 代替候補）

- フィードバック関数ベースの評価
- RAG トライアド（Context Relevance, Groundedness, Answer Relevance）
- ローカル実行可能
- **検討理由:** DeepEval と機能が重複するため、必要に応じて

#### Giskard（△ セキュリティテスト時）

- LLM の脆弱性検出（プロンプトインジェクション等）
- バイアス検出
- ローカル実行可能
- **用途:** セキュリティ・安全性テストが必要な場合

#### MLflow（△ ML統合時）

- ML 実験管理の定番
- LLM 評価機能を追加（MLflow 2.8+）
- セルフホスト可能（AWS Tokyo）
- **検討理由:** 既に MLflow を使用している場合は統合が容易

#### OpenLLMetry（△ 既存OTel環境時）

- OpenTelemetry ベースの LLM トレーシング
- 既存の Observability スタックと統合
- ベンダーロックインなし
- **検討理由:** 既に OpenTelemetry 環境がある場合

#### Arize Phoenix（△ 代替候補）

- トレース可視化
- セルフホスト可能
- **検討理由:** Langfuse の代替として

### 不採用ツールと理由

| ツール | 不採用理由 |
|--------|-----------|
| **Braintrust** | データが US のみ、セルフホスト不可 |
| **LangSmith** | データが US のみ、セルフホスト不可 |
| **Confident AI** | DeepEval のクラウド版、US のみ |
| **Helicone** | クラウドのみ、US データセンター |

※ 機能面では優れているが、日本国内データレジデンシー要件を満たせない

---

## 推奨構成

### 基本構成（必須）

```
┌─────────────────────────────────────────────────────────────────┐
│                    日本国内データレジデンシー対応構成             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│  │  DeepEval   │   │  Langfuse   │   │  ローカルファイル    │   │
│  │ (評価実行)  │   │ (トレース)  │   │  (回帰管理)         │   │
│  └──────┬──────┘   └──────┬──────┘   └──────────┬──────────┘   │
│         │                 │                      │              │
│         ▼                 ▼                      ▼              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               AWS Tokyo リージョン                       │   │
│  │  ・Bedrock Claude (評価LLM / エージェント)              │   │
│  │  ・Langfuse セルフホスト (ECS + RDS)                    │   │
│  │  ・評価結果は S3 Tokyo にバックアップ                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               git リポジトリ                             │   │
│  │  ・baseline_scores.json (回帰テスト用)                  │   │
│  │  ・datasets/*.json (テストケース)                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ✅ すべてのデータが日本国内に保存される                        │
└─────────────────────────────────────────────────────────────────┘
```

### 用途別ツール構成

| 用途 | メインツール | 補助ツール | 備考 |
|------|-------------|-----------|------|
| **汎用エージェント評価** | DeepEval | - | 常時使用 |
| **RAG 評価** | DeepEval + Ragas | - | RAG 実装時に追加 |
| **プロンプト最適化** | promptfoo | DeepEval | A/B テスト時 |
| **セキュリティテスト** | Giskard | DeepEval | プロンプトインジェクション対策時 |
| **トレース・監視** | Langfuse | - | 常時使用（セルフホスト） |
| **ML 実験管理統合** | MLflow | Langfuse | 既存 ML 環境がある場合 |

### フェーズ別構成

```
Phase 1: MVP（最小構成）
├── DeepEval（ローカル評価）
├── Langfuse（セルフホスト監視）
└── baseline_scores.json（回帰管理）

Phase 2: プロンプト最適化
├── + promptfoo（A/B テスト追加）
└── プロンプトバージョン比較

Phase 3: RAG 機能追加時
├── + Ragas（RAG 評価追加）
└── Context/Retrieval 評価

Phase 4: セキュリティ強化
├── + Giskard（脆弱性検出追加）
└── プロンプトインジェクション対策
```

### Langfuse セルフホスト構成

```yaml
# docker-compose.yml（AWS Tokyo ECS / EC2）
version: '3.8'
services:
  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://user:pass@rds-tokyo.amazonaws.com:5432/langfuse
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
      - NEXTAUTH_URL=https://langfuse.your-domain.jp
      - SALT=${SALT}
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=langfuse
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=langfuse
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### デプロイ先オプション

| 環境 | 構成 | 難易度 | 推奨度 |
|------|------|--------|--------|
| AWS Tokyo | ECS Fargate + RDS | 中 | ★★★ |
| AWS Tokyo | EC2 + Docker Compose | 低 | ★★☆ |
| Azure Japan East | Container Apps + PostgreSQL | 中 | ★★☆ |
| オンプレミス | Docker Compose | 低 | ★☆☆ |

---

## 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────┐
│                        開発フェーズ                                   │
├─────────────────────────────────────────────────────────────────────┤
│  [データセット作成] → [自動テスト] → [回帰テスト]                      │
│        ↓                  ↓              ↓                          │
│  手動で初期ケース    CI/CDで定期実行   プロンプト/Tool変更時           │
│                                                                     │
│  評価実行: DeepEval + Bedrock Haiku (Tokyo)                         │
│  回帰管理: baseline_scores.json (git)                               │
│  可視化: Langfuse セルフホスト (Tokyo)                               │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        本番フェーズ                                   │
├─────────────────────────────────────────────────────────────────────┤
│  [トレース収集] → [異常検知] → [データセット拡充] → [再評価]          │
│        ↓              ↓              ↓                              │
│   Langfuse        低スコア検出    問題ケースを追加                    │
│   (Tokyo)                                                           │
│                                                                     │
│  モニタリング: Langfuse ダッシュボード                               │
│  品質改善: 問題トレース → データセット追加 → 回帰テスト              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 開発フェーズ

### 目的

- プロンプト変更やツール追加による品質劣化を防止
- 最低品質基準の担保
- 高速かつ低コストなフィードバックループ

### テスト方式: 閾値 + 回帰チェック

単純な閾値チェックだけでは微妙な劣化を見逃すため、**2つの条件を組み合わせ**ます。

```
┌─────────────────────────────────────────────┐
│           評価パス条件                       │
├─────────────────────────────────────────────┤
│  ① 絶対閾値:  スコア ≥ 0.75 (最低品質保証)  │
│        AND                                  │
│  ② 回帰チェック: 前回比 -5% 以内            │
└─────────────────────────────────────────────┘
```

#### 判定例

| 前回 | 今回 | 閾値チェック | 回帰チェック | 結果 |
|------|------|-------------|-------------|------|
| 0.95 | 0.92 | ✅ (≥0.75) | ✅ (-3.2%) | ✅ PASS |
| 0.95 | 0.81 | ✅ (≥0.75) | ❌ (-14.7%) | ❌ FAIL |
| 0.70 | 0.70 | ❌ (<0.75) | ✅ (±0%) | ❌ FAIL |
| 0.80 | 0.90 | ✅ (≥0.75) | ✅ (+12.5%) | ✅ PASS |

### 回帰テストに Langfuse を使わない理由

| 観点 | 説明 |
|------|------|
| 設計思想 | Langfuse は可視化・モニタリングがメイン |
| 速度 | 毎回 API コールが必要で CI が遅くなる |
| オフライン | セルフホストでも API 依存 |
| 比較機能 | 自動回帰比較の組み込み機能がない |

**結論:** 回帰テストはローカルファイル（git管理）、可視化・長期トレンドは Langfuse という役割分担

### テスト実行タイミング

| タイミング | データセット | 指標 | 目的 |
|-----------|-------------|------|------|
| PR作成時 | core (10ケース) | 軽量4指標 | 早期フィードバック |
| mainマージ後 | 全て (30ケース) | 軽量4指標 | ベースライン更新 |
| 週次 | 全て | 全指標 | 詳細品質確認 |
| モデル更新時 | 全て | 全指標 | 互換性確認 |

### ベースライン管理

```
datasets/
├── baseline_scores.json       # 前回スコア（git管理）
└── evaluation_history/        # 履歴（オプション）
    ├── 2024-01-15.json
    └── 2024-01-16.json
```

**baseline_scores.json の例:**

```json
{
  "updated_at": "2024-01-15T10:30:00Z",
  "commit": "abc1234",
  "scores": {
    "Answer Relevancy": 0.92,
    "Response Quality": 0.88,
    "Tool Usage Correctness": 0.95,
    "Japanese Language Quality": 0.90
  },
  "test_cases": {
    "core-001": {
      "Answer Relevancy": 0.95,
      "Response Quality": 0.90
    }
  }
}
```

---

## 本番フェーズ

### 目的

- リアルタイムでの品質監視
- 問題トレースの早期発見
- 継続的なデータセット改善

### Langfuse によるモニタリング

#### 監視項目

| 項目 | 閾値 | アラート条件 |
|------|------|-------------|
| エラー率 | < 1% | > 5% |
| p95 レイテンシ | < 5秒 | > 10秒 |
| ユーザー満足度 (👍率) | ≥ 90% | < 80% |
| 日次スコア平均 | ≥ 0.80 | < 0.70 |

#### 問題発見 → 改善フロー

```
1. Langfuse でフィルタリング
   - ユーザーが👎をつけたトレース
   - エラーが発生したトレース
   - スコアが低いトレース

2. 問題ケースをレビュー
   - 何が問題だったか分析
   - 期待する出力を定義

3. データセットに追加
   - production_issues.json に追加
   - 再現テストケースとして登録

4. 回帰テストに組み込み
   - 次回以降のテストで検証
   - 同じ問題の再発を防止
```

---

## 評価指標

### 指標一覧

| 指標 | 説明 | コスト | 優先度 | 用途 |
|------|------|--------|--------|------|
| **Response Quality** | 回答の明確性・簡潔性・有用性 | 低 | ★★★ | 常時 |
| **Answer Relevancy** | 質問への関連性 | 低 | ★★★ | 常時 |
| **Tool Usage Correctness** | ツール選択・実行の適切性 | 低 | ★★★ | 常時 |
| **Japanese Language Quality** | 日本語の文法・自然さ | 低 | ★★☆ | 常時 |
| **Faithfulness** | 提供情報への忠実性 | 中 | ★★☆ | 週次 |
| Hallucination | 幻覚（事実と異なる内容）検出 | 高 | ★☆☆ | 週次 |
| Contextual Relevancy | コンテキストとの関連性 | 高 | ★☆☆ | 週次 |

### 指標セット

#### 軽量セット（日常テスト用）

- Response Quality
- Answer Relevancy
- Tool Usage Correctness
- Japanese Language Quality

**特徴:** 高速・低コスト、CI/CD に適する

#### 完全セット（詳細評価用）

- 軽量セット + Faithfulness + Hallucination + Contextual Relevancy

**特徴:** 網羅的、週次や重要リリース前に実行

---

## データセット管理

### ディレクトリ構成

```
datasets/
├── core_scenarios.json        # 必須機能テスト (10-20ケース)
├── edge_cases.json            # エッジケース (5-10ケース)
├── regression.json            # 過去のバグ修正確認
├── production_issues.json     # 本番で発見した問題
├── baseline_scores.json       # 前回評価スコア
└── evaluation_history/        # 履歴保存（オプション）
```

### データセット構造

```json
{
  "version": "1.0",
  "description": "コアシナリオテストケース",
  "test_cases": [
    {
      "id": "core-001",
      "category": "knowledge",
      "priority": "high",
      "input": "量子コンピューティングとは？",
      "expected_output": "量子力学の原理を利用した計算技術...",
      "context": [],
      "retrieval_context": [],
      "evaluation_criteria": {
        "must_contain": ["量子ビット", "重ね合わせ"],
        "must_not_contain": ["わかりません", "できません"],
        "tone": "professional"
      },
      "metadata": {
        "created_at": "2024-01-15",
        "source": "manual",
        "related_issue": null
      }
    }
  ]
}
```

### カテゴリ分類

| カテゴリ | 説明 | 例 |
|---------|------|-----|
| knowledge | 知識質問 | 「〜とは？」「〜の違いは？」 |
| task | タスク実行 | 「ファイルを作成して」「コードを書いて」 |
| tool_use | ツール使用 | 「検索して」「計算して」 |
| conversation | 対話 | 「こんにちは」「ありがとう」 |
| edge_case | エッジケース | 長文入力、特殊文字、曖昧な指示 |

---

## CI/CD統合

### コマンド体系

```makefile
# Makefile

# 軽量テスト（PR時）
eval-quick:
	uv run python src/run_evaluation.py --dataset core --metrics lightweight

# 完全テスト（マージ後）
eval-full:
	uv run python src/run_evaluation.py --dataset all --metrics full

# 回帰チェック（CI用）
eval-check:
	uv run python src/run_evaluation.py --check-regression

# ベースライン更新（マージ後）
eval-baseline:
	uv run python src/run_evaluation.py --update-baseline
```

### GitHub Actions 例

```yaml
name: Evaluation

on:
  pull_request:
    paths:
      - 'src/**'
      - 'prompts/**'

  push:
    branches: [main]

jobs:
  eval-pr:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup
        run: |
          pip install uv
          uv sync
      - name: Run evaluation check
        run: make eval-check
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: ap-northeast-1  # Tokyo

  eval-baseline:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup
        run: |
          pip install uv
          uv sync
      - name: Update baseline
        run: make eval-baseline
        env:
          AWS_REGION: ap-northeast-1  # Tokyo
      - name: Commit baseline
        run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add datasets/baseline_scores.json
          git commit -m "chore: update evaluation baseline" || exit 0
          git push
```

---

## KPI設定

### 開発フェーズ KPI

| KPI | 目標値 | アラート閾値 | 測定頻度 |
|-----|--------|-------------|---------|
| Response Quality 平均 | ≥ 0.85 | < 0.75 | PR毎 |
| Answer Relevancy 平均 | ≥ 0.80 | < 0.70 | PR毎 |
| Tool Usage 平均 | ≥ 0.85 | < 0.75 | PR毎 |
| 全体パス率 | ≥ 80% | < 70% | PR毎 |
| 回帰発生率 | 0% | > 0% | PR毎 |

### 本番フェーズ KPI

| KPI | 目標値 | アラート閾値 | 測定頻度 |
|-----|--------|-------------|---------|
| ユーザー満足度 (👍率) | ≥ 90% | < 80% | 日次 |
| エラー率 | < 1% | > 5% | リアルタイム |
| p95 レイテンシ | < 5秒 | > 10秒 | リアルタイム |
| 週次スコア変動 | ±5%以内 | ±10%超 | 週次 |

---

## コスト試算

### 評価コスト（Bedrock Haiku Tokyo 使用）

| テストタイプ | ケース数 | 指標数 | コスト/回 | 頻度 | 月額目安 |
|-------------|---------|--------|----------|------|---------|
| Quick (PR時) | 10 | 4 | ~$0.05 | 10回/日 | ~$15 |
| Full (日次) | 30 | 7 | ~$0.50 | 1回/日 | ~$15 |
| **評価合計** | - | - | - | - | **~$30** |

### インフラコスト（Langfuse セルフホスト）

| リソース | 構成 | 月額目安 |
|---------|------|---------|
| ECS Fargate | 0.5 vCPU, 1GB | ~$15 |
| RDS PostgreSQL | db.t3.micro | ~$15 |
| ALB | 1台 | ~$20 |
| **インフラ合計** | - | **~$50** |

### 総コスト

| 項目 | 月額 |
|------|------|
| 評価実行 (Bedrock Haiku) | ~$30 |
| Langfuse インフラ | ~$50 |
| **合計** | **~$80** |

### 比較

| 構成 | 月額コスト | 備考 |
|------|-----------|------|
| **本構成** | ~$80 | 日本国内データ ✅ |
| Braintrust (有料) | ~$100+ | 日本対応 ❌ |
| LangSmith (有料) | ~$40+ | 日本対応 ❌ |
| GPT-4 評価 | ~$3,000+ | 100倍高コスト |

---

## 実装ロードマップ

### Phase 1: 基盤構築（1週目）

- [ ] データセット構造の定義
- [ ] core_scenarios.json の作成（10-20ケース）
- [ ] 軽量評価スクリプトの実装
- [ ] baseline_scores.json の初期化

### Phase 2: CI/CD統合（2週目）

- [ ] 回帰チェック機能の実装
- [ ] GitHub Actions ワークフロー作成
- [ ] Makefile コマンド整備

### Phase 3: Langfuse セルフホスト（2-3週目）

- [ ] AWS Tokyo に Langfuse 構築
- [ ] RDS PostgreSQL セットアップ
- [ ] HTTPS / 認証設定
- [ ] 既存コードの接続先変更

### Phase 4: 本番準備（3週目）

- [ ] Langfuse ダッシュボード設定
- [ ] アラート設定（Slack連携等）
- [ ] 運用ドキュメント作成

### Phase 5: 運用開始（リリース後）

- [ ] 本番トレースのモニタリング開始
- [ ] 問題ケースの収集・分析
- [ ] データセットの継続的拡充

---

## 参考リンク

- [DeepEval Documentation](https://docs.confident-ai.com/)
- [Langfuse Documentation](https://langfuse.com/docs)
- [Langfuse Self-Hosting Guide](https://langfuse.com/docs/deployment/self-host)
- [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Ragas Documentation](https://docs.ragas.io/)
- [promptfoo Documentation](https://www.promptfoo.dev/docs/intro/)
- [TruLens Documentation](https://www.trulens.org/trulens_eval/getting_started/)
- [Giskard Documentation](https://docs.giskard.ai/)
- [MLflow LLM Evaluate](https://mlflow.org/docs/latest/llms/llm-evaluate/index.html)
- [OpenLLMetry](https://github.com/traceloop/openllmetry)
- [Arize Phoenix](https://docs.arize.com/phoenix)

---

## 更新履歴

| 日付 | 内容 |
|------|------|
| 2024-12-09 | Ragas, promptfoo, TruLens, Giskard, MLflow, OpenLLMetry 追加。用途別構成を追記 |
| 2024-12-09 | 初版作成（日本国内データレジデンシー要件対応） |
