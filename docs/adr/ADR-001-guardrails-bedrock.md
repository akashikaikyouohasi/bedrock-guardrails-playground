# ADR-001: Guardrails に AWS Bedrock Guardrails を採用

## ステータス

**採用（Accepted）** - 2024-12-09

## コンテキスト

AI エージェントを本番環境で運用するにあたり、以下の安全性要件を満たす Guardrails ソリューションが必要である：

1. 有害コンテンツ（暴力、性的表現、侮辱等）のフィルタリング
2. 個人情報（PII）の検出・マスキング
3. 特定トピックの拒否（競合他社、機密情報等）
4. プロンプトインジェクション対策
5. 日本語での動作
6. 日本国内でのデータ保存（データレジデンシー要件）

## 検討した選択肢

### 選択肢 1: AWS Bedrock Guardrails

AWS が提供するマネージド Guardrails サービス。

**メリット:**
- 日本語対応が良好（検証済み）
- 東京リージョン（ap-northeast-1）で利用可能
- マネージドサービスで運用負担が低い
- ApplyGuardrail API でリアルタイムチェック可能
- PII 検出が日本の形式（電話番号、住所等）に対応
- INPUT/OUTPUT 両方でチェック可能
- ストリーミング中の検出に対応

**デメリット:**
- 従量課金（1,000 テキストユニットあたり $0.75〜$1.00）
- AWS ロックイン

### 選択肢 2: Azure AI Content Safety

Microsoft が提供するコンテンツ安全性サービス。

**メリット:**
- 日本語対応が良好
- Japan East リージョンで利用可能
- 画像モデレーションにも対応

**デメリット:**
- 現在のインフラが AWS 中心のため、マルチクラウドになる
- Bedrock との統合が必要

### 選択肢 3: Guardrails AI（OSS）

オープンソースの出力検証ライブラリ。

**メリット:**
- 無料（OSS）
- ローカル実行可能
- スキーマ検証に強い

**デメリット:**
- コンテンツ安全性フィルタリングが主目的ではない
- 日本語対応が限定的
- 運用・メンテナンス負担

### 選択肢 4: NeMo Guardrails（NVIDIA）

NVIDIA が提供する対話フロー制御フレームワーク。

**メリット:**
- 複雑な対話フロー制御が可能
- OSS で無料

**デメリット:**
- Colang（独自言語）の学習コスト
- 日本語対応が弱い（英語前提の設計）
- 導入・運用の難易度が高い

### 選択肢 5: Lakera Guard

プロンプトインジェクション検出に特化した商用サービス。

**メリット:**
- プロンプトインジェクション検出の精度が業界最高水準
- API が使いやすい

**デメリット:**
- データロケーションが EU/US のみ（日本国内保存不可）
- 有料サービス
- コンテンツフィルタリングは別途必要

### 選択肢 6: OpenAI Moderation API

OpenAI が提供する無料のモデレーション API。

**メリット:**
- 無料
- 導入が簡単

**デメリット:**
- 日本語対応が限定的
- データが US に送信される
- カスタマイズ性が低い

## 決定

**AWS Bedrock Guardrails を採用する。**

## 理由

1. **日本語対応**: 検証の結果、日本語でのコンテンツフィルタリング、PII 検出が実用レベルで動作することを確認した

2. **データレジデンシー**: 東京リージョン（ap-northeast-1）で利用可能であり、個人情報を含むデータが日本国内に保存される要件を満たす

3. **インフラ統合**: 既にエージェントが AWS Bedrock（Claude）を使用しているため、同一エコシステム内で完結する

4. **運用負担**: マネージドサービスであり、スケーリング、可用性、セキュリティパッチ等を AWS が管理する

5. **リアルタイムチェック**: ApplyGuardrail API を使用することで、ストリーミング出力中にリアルタイムで有害コンテンツを検出・停止できることを実証済み（terraform/examples/streaming_example.py）

6. **コスト**: 従量課金だが、検証の結果、想定トラフィックでは許容範囲内（月額数十ドル程度）

## 結果

- Bedrock Guardrails を使用した INPUT/OUTPUT チェックを実装
- ストリーミング時のリアルタイムチェック機能を実装（AgentSDKWithApplyGuardrail クラス）
- 実装ガイドを docs/apply_guardrails/ に作成

## 参考

- [AWS Bedrock Guardrails Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
- [実装ガイド](../apply_guardrails/implementation-guide.md)
- [ストリーミング検証レポート](../apply_guardrails/streaming-realtime-check-experiment.md)
