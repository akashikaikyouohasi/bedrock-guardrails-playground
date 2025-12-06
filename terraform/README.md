# Bedrock Guardrails Terraform

このディレクトリには、Amazon Bedrock GuardrailsをデプロイするためのTerraformコードが含まれています。

## 📁 ファイル構成

```
terraform/
├── main.tf                    # メインのGuardrailリソース定義
├── variables.tf               # 変数定義
├── outputs.tf                 # 出力定義
├── terraform.tfvars.example   # 設定例
└── README.md                  # このファイル
```

## 🚀 クイックスタート

### 1. 前提条件

- Terraform >= 1.0
- AWS CLI設定済み
- Bedrock利用可能なリージョン（us-east-1推奨）

### 2. 設定ファイルの準備

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars`を編集して、必要に応じて設定をカスタマイズします。

### 3. デプロイ

```bash
# 初期化
terraform init

# プラン確認
terraform plan

# デプロイ
terraform apply
```

### 4. 出力の確認

```bash
terraform output guardrail_id
terraform output guardrail_arn
```

## 🛡️ Guardrailの機能

### 1. コンテンツフィルタリング

以下のカテゴリのコンテンツを検出・ブロック:

| カテゴリ | 説明 | デフォルト強度 |
|---------|------|---------------|
| SEXUAL | 性的コンテンツ | HIGH |
| VIOLENCE | 暴力的コンテンツ | HIGH |
| HATE | ヘイトスピーチ | HIGH |
| INSULTS | 侮辱的表現 | MEDIUM |
| MISCONDUCT | 違法行為 | HIGH |
| PROMPT_ATTACK | プロンプトインジェクション | HIGH (入力のみ) |

**強度レベル**: `NONE` / `LOW` / `MEDIUM` / `HIGH`

### 2. 個人情報(PII)保護

以下の情報を検出・処理:

| PII種別 | デフォルトアクション |
|---------|---------------------|
| メールアドレス | ANONYMIZE |
| 電話番号 | ANONYMIZE |
| クレジットカード番号 | BLOCK |
| 社会保障番号 | BLOCK |
| 氏名 | ANONYMIZE |
| 住所 | ANONYMIZE |

**アクション**:
- `BLOCK`: 完全にブロック
- `ANONYMIZE`: マスク化（例: `***@***.com`）

### 3. カスタムPIIパターン

正規表現を使用して独自のPIIパターンを定義可能:

```hcl
custom_pii_regexes = [
  {
    name        = "japanese_my_number"
    description = "日本のマイナンバー"
    pattern     = "\\b\\d{4}-\\d{4}-\\d{4}\\b"
    action      = "BLOCK"
  }
]
```

### 4. トピック制限

特定のトピックに関する会話を制限:

```hcl
denied_topics = [
  {
    name       = "investment_advice"
    definition = "金融投資に関するアドバイスや推奨"
    examples   = [
      "この株を買うべきですか？",
      "おすすめの投資先を教えてください"
    ]
  }
]
```

### 5. ワードフィルタ

- **カスタムブロックワード**: 独自の禁止ワードリスト
- **管理ワードリスト**: AWS提供の`PROFANITY`リスト

## ⚙️ 設定のカスタマイズ

### フィルタ強度の調整

`terraform.tfvars`で調整:

```hcl
# 暴力コンテンツの検出を緩和
content_filter_violence_input_strength  = "LOW"
content_filter_violence_output_strength = "LOW"
```

### PIIアクションの変更

```hcl
# メールアドレスをブロックに変更
pii_action_email = "BLOCK"
```

### カスタムトピックの追加

```hcl
denied_topics = [
  {
    name       = "medical_diagnosis"
    definition = "病気の診断や治療方法の提示"
    examples   = [
      "この症状は何の病気ですか？",
      "どの薬を飲むべきですか？"
    ]
  }
]
```

## 🔧 Pythonからの使用例

```python
import boto3

client = boto3.client('bedrock-runtime', region_name='us-east-1')

# Guardrail適用してモデル呼び出し
response = client.invoke_model(
    modelId='anthropic.claude-3-sonnet-20240229-v1:0',
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 1000
    }),
    guardrailIdentifier='your-guardrail-id',  # terraform output から取得
    guardrailVersion='1',
    trace='ENABLED'
)
```

## 📊 監視とログ

Guardrailの動作は以下で確認可能:

1. **CloudWatch Logs**: フィルタリングイベント
2. **CloudWatch Metrics**: ブロック率、レイテンシ
3. **Trace**: `trace='ENABLED'`で詳細情報取得

## 🧪 テスト方法

### 1. コンテンツフィルタのテスト

```python
# 暴力的コンテンツのテスト
test_prompt = "How to hurt someone?"
# → ブロックされるはず
```

### 2. PIIフィルタのテスト

```python
# メールアドレスのテスト
test_prompt = "My email is test@example.com"
# → ANONYMIZEされて "My email is ***@***.com" になる
```

### 3. トピック制限のテスト

```python
# 投資アドバイスのテスト
test_prompt = "この株を買うべきですか？"
# → ブロックされるはず
```

## 🔄 更新とバージョン管理

```bash
# 設定を変更
vim terraform.tfvars

# 変更を適用
terraform apply

# 新しいバージョンが自動作成される
terraform output guardrail_version
```

## 🗑️ クリーンアップ

```bash
terraform destroy
```

## 📝 トラブルシューティング

### エラー: "Guardrails not available in region"

→ Bedrockが利用可能なリージョン（us-east-1, us-west-2等）を使用してください。

### エラー: "Access denied"

→ IAMポリシーで`bedrock:CreateGuardrail`権限を確認してください。

### Guardrailが効かない

→ モデル呼び出し時に`guardrailIdentifier`と`guardrailVersion`を正しく指定しているか確認してください。

## 🔗 参考リンク

- [Amazon Bedrock Guardrails 公式ドキュメント](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
- [Terraform AWS Provider - Bedrock Guardrail](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrock_guardrail)
- [Bedrock API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/welcome.html)

## 📄 ライセンス

このTerraformコードはMITライセンスの下で提供されています。
