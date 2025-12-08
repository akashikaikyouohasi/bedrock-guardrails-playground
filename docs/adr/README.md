# Architecture Decision Records (ADR)

本ディレクトリには、プロジェクトの重要なアーキテクチャ決定を記録しています。

## ADR 一覧

| ADR | タイトル | ステータス | 日付 |
|-----|---------|----------|------|
| [ADR-001](./ADR-001-guardrails-bedrock.md) | Guardrails に AWS Bedrock Guardrails を採用 | 採用 | 2024-12-09 |
| [ADR-002](./ADR-002-evaluation-deepeval-langfuse.md) | 評価に DeepEval + Langfuse を採用 | 採用 | 2024-12-09 |

## ADR とは

Architecture Decision Record（ADR）は、ソフトウェアアーキテクチャに関する重要な決定を文書化したものです。

各 ADR には以下が含まれます：

- **コンテキスト**: 決定が必要になった背景
- **検討した選択肢**: 比較検討したオプション
- **決定**: 採用した選択肢
- **理由**: その選択肢を採用した理由
- **結果**: 決定による影響

## ステータス

| ステータス | 説明 |
|-----------|------|
| 提案（Proposed） | 検討中 |
| 採用（Accepted） | 採用決定 |
| 非推奨（Deprecated） | 別の決定に置き換え |
| 却下（Rejected） | 採用しないことを決定 |

## 新しい ADR の作成

```bash
# ファイル名形式: ADR-XXX-<短い説明>.md
touch docs/adr/ADR-003-new-decision.md
```

テンプレート:

```markdown
# ADR-XXX: タイトル

## ステータス

**提案（Proposed）** - YYYY-MM-DD

## コンテキスト

[決定が必要になった背景]

## 検討した選択肢

### 選択肢 1: ...

### 選択肢 2: ...

## 決定

[採用した選択肢]

## 理由

[採用理由]

## 結果

[決定による影響]
```
