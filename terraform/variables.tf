variable "aws_region" {
  description = "AWS region where Bedrock Guardrails will be created"
  type        = string
  default     = "us-west-2"
}

variable "guardrail_name" {
  description = "Name of the Bedrock Guardrail"
  type        = string
  default     = "bedrock-guardrail-playground"
}

variable "guardrail_description" {
  description = "Description of the Bedrock Guardrail"
  type        = string
  default     = "Guardrail for testing Bedrock content filtering and safety features"
}

variable "blocked_input_messaging" {
  description = "Message to return when input is blocked"
  type        = string
  default     = "申し訳ありません。この入力は当社のコンテンツポリシーに違反しているため処理できません。"
}

variable "blocked_outputs_messaging" {
  description = "Message to return when output is blocked"
  type        = string
  default     = "申し訳ありません。生成されたコンテンツが当社のポリシーに違反しているため表示できません。"
}

# Content Filter Strengths
# Options: NONE, LOW, MEDIUM, HIGH
variable "content_filter_sexual_input_strength" {
  description = "Strength of sexual content filtering for input"
  type        = string
  default     = "HIGH"
  validation {
    condition     = contains(["NONE", "LOW", "MEDIUM", "HIGH"], var.content_filter_sexual_input_strength)
    error_message = "Must be one of: NONE, LOW, MEDIUM, HIGH"
  }
}

variable "content_filter_sexual_output_strength" {
  description = "Strength of sexual content filtering for output"
  type        = string
  default     = "HIGH"
  validation {
    condition     = contains(["NONE", "LOW", "MEDIUM", "HIGH"], var.content_filter_sexual_output_strength)
    error_message = "Must be one of: NONE, LOW, MEDIUM, HIGH"
  }
}

variable "content_filter_violence_input_strength" {
  description = "Strength of violence content filtering for input"
  type        = string
  default     = "HIGH"
}

variable "content_filter_violence_output_strength" {
  description = "Strength of violence content filtering for output"
  type        = string
  default     = "HIGH"
}

variable "content_filter_hate_input_strength" {
  description = "Strength of hate speech filtering for input"
  type        = string
  default     = "HIGH"
}

variable "content_filter_hate_output_strength" {
  description = "Strength of hate speech filtering for output"
  type        = string
  default     = "HIGH"
}

variable "content_filter_insults_input_strength" {
  description = "Strength of insults filtering for input"
  type        = string
  default     = "HIGH"
}

variable "content_filter_insults_output_strength" {
  description = "Strength of insults filtering for output"
  type        = string
  default     = "HIGH"
}

variable "content_filter_misconduct_input_strength" {
  description = "Strength of misconduct filtering for input"
  type        = string
  default     = "HIGH"
}

variable "content_filter_misconduct_output_strength" {
  description = "Strength of misconduct filtering for output"
  type        = string
  default     = "HIGH"
}

variable "content_filter_prompt_attack_input_strength" {
  description = "Strength of prompt attack filtering for input"
  type        = string
  default     = "HIGH"
}

variable "content_filter_prompt_attack_output_strength" {
  description = "Strength of prompt attack filtering for output"
  type        = string
  default     = "NONE"
}

# PII Actions
# Options: BLOCK, ANONYMIZE
variable "pii_action_email" {
  description = "Action for email addresses (BLOCK or ANONYMIZE)"
  type        = string
  default     = "ANONYMIZE"
  validation {
    condition     = contains(["BLOCK", "ANONYMIZE"], var.pii_action_email)
    error_message = "Must be either BLOCK or ANONYMIZE"
  }
}

variable "pii_action_phone" {
  description = "Action for phone numbers"
  type        = string
  default     = "ANONYMIZE"
}

variable "pii_action_credit_card" {
  description = "Action for credit card numbers"
  type        = string
  default     = "BLOCK"
}

variable "pii_action_ssn" {
  description = "Action for social security numbers"
  type        = string
  default     = "BLOCK"
}

variable "pii_action_name" {
  description = "Action for names"
  type        = string
  default     = "ANONYMIZE"
}

variable "pii_action_address" {
  description = "Action for addresses"
  type        = string
  default     = "ANONYMIZE"
}

# Custom PII Regexes
variable "custom_pii_regexes" {
  description = "Custom regex patterns for PII detection"
  type = list(object({
    name        = string
    description = string
    pattern     = string
    action      = string
  }))
  default = [
    {
      name        = "japanese_my_number"
      description = "日本のマイナンバー（12桁）"
      pattern     = "\\b\\d{4}-\\d{4}-\\d{4}\\b"
      action      = "BLOCK"
    }
  ]
}

# Topic Policy
variable "denied_topics" {
  description = "Topics to deny in conversations"
  type = list(object({
    name       = string
    definition = string
    examples   = list(string)
  }))
  default = [
    {
      name       = "investment_advice"
      definition = "金融投資に関するアドバイスや推奨"
      examples = [
        "この株を買うべきですか？",
        "おすすめの投資先を教えてください",
        "暗号通貨に投資すべきですか？"
      ]
    },
    {
      name       = "medical_advice"
      definition = "医療診断や治療に関する具体的なアドバイス"
      examples = [
        "この症状は何の病気ですか？",
        "薬を飲むべきですか？",
        "手術が必要ですか？"
      ]
    }
  ]
}

# Word Filters
variable "blocked_words" {
  description = "List of custom words to block"
  type        = list(string)
  default     = []
}

variable "managed_word_lists" {
  description = "Managed word lists to use (e.g., PROFANITY)"
  type        = list(string)
  default     = ["PROFANITY"]
}

# Version
variable "guardrail_version_description" {
  description = "Description for the guardrail version"
  type        = string
  default     = "Initial version"
}

# Tags
variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default = {
    Project     = "bedrock-guardrails-playground"
    Environment = "development"
    ManagedBy   = "terraform"
  }
}
