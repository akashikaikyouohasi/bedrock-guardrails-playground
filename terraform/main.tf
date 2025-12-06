terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Bedrock Guardrail リソース
resource "aws_bedrock_guardrail" "main" {
  name                      = var.guardrail_name
  description              = var.guardrail_description
  blocked_input_messaging  = var.blocked_input_messaging
  blocked_outputs_messaging = var.blocked_outputs_messaging

  # コンテンツポリシー設定
  content_policy_config {
    # 性的コンテンツのフィルタリング
    filters_config {
      input_strength  = var.content_filter_sexual_input_strength
      output_strength = var.content_filter_sexual_output_strength
      type           = "SEXUAL"
    }

    # 暴力的コンテンツのフィルタリング
    filters_config {
      input_strength  = var.content_filter_violence_input_strength
      output_strength = var.content_filter_violence_output_strength
      type           = "VIOLENCE"
    }

    # ヘイトスピーチのフィルタリング
    filters_config {
      input_strength  = var.content_filter_hate_input_strength
      output_strength = var.content_filter_hate_output_strength
      type           = "HATE"
    }

    # 侮辱的コンテンツのフィルタリング
    filters_config {
      input_strength  = var.content_filter_insults_input_strength
      output_strength = var.content_filter_insults_output_strength
      type           = "INSULTS"
    }

    # 違法行為関連のフィルタリング
    filters_config {
      input_strength  = var.content_filter_misconduct_input_strength
      output_strength = var.content_filter_misconduct_output_strength
      type           = "MISCONDUCT"
    }

    # プロンプトインジェクション対策
    filters_config {
      input_strength  = var.content_filter_prompt_attack_input_strength
      output_strength = var.content_filter_prompt_attack_output_strength
      type           = "PROMPT_ATTACK"
    }
  }

  # 機密情報(PII)のフィルタリング設定
  sensitive_information_policy_config {
    # メールアドレス
    pii_entities_config {
      action = var.pii_action_email
      type   = "EMAIL"
    }

    # 電話番号
    pii_entities_config {
      action = var.pii_action_phone
      type   = "PHONE"
    }

    # クレジットカード番号
    pii_entities_config {
      action = var.pii_action_credit_card
      type   = "CREDIT_DEBIT_CARD_NUMBER"
    }

    # 社会保障番号
    pii_entities_config {
      action = var.pii_action_ssn
      type   = "US_SOCIAL_SECURITY_NUMBER"
    }

    # 氏名
    pii_entities_config {
      action = var.pii_action_name
      type   = "NAME"
    }

    # 住所
    pii_entities_config {
      action = var.pii_action_address
      type   = "ADDRESS"
    }

    # カスタム正規表現パターン（例：日本のマイナンバー）
    dynamic "regexes_config" {
      for_each = var.custom_pii_regexes
      content {
        action      = regexes_config.value.action
        description = regexes_config.value.description
        name        = regexes_config.value.name
        pattern     = regexes_config.value.pattern
      }
    }
  }

  # トピック制限設定
  dynamic "topic_policy_config" {
    for_each = length(var.denied_topics) > 0 ? [1] : []
    content {
      dynamic "topics_config" {
        for_each = var.denied_topics
        content {
          name       = topics_config.value.name
          definition = topics_config.value.definition
          examples   = topics_config.value.examples
          type       = "DENY"
        }
      }
    }
  }

  # ワードフィルタリング設定
  dynamic "word_policy_config" {
    for_each = length(var.blocked_words) > 0 || length(var.managed_word_lists) > 0 ? [1] : []
    content {
      # カスタムブロックワード
      dynamic "words_config" {
        for_each = var.blocked_words
        content {
          text = words_config.value
        }
      }

      # 管理されたワードリスト
      dynamic "managed_word_lists_config" {
        for_each = var.managed_word_lists
        content {
          type = managed_word_lists_config.value
        }
      }
    }
  }

  tags = var.tags
}

# Guardrailのバージョン作成
resource "aws_bedrock_guardrail_version" "main" {
  guardrail_arn = aws_bedrock_guardrail.main.guardrail_arn
  description   = "Version ${var.guardrail_version_description}"
}
