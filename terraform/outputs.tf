output "guardrail_id" {
  description = "ID of the created Bedrock Guardrail"
  value       = aws_bedrock_guardrail.main.guardrail_id
}

output "guardrail_arn" {
  description = "ARN of the created Bedrock Guardrail"
  value       = aws_bedrock_guardrail.main.guardrail_arn
}

output "guardrail_version" {
  description = "Version number of the Guardrail"
  value       = aws_bedrock_guardrail_version.main.version
}

output "guardrail_version_arn" {
  description = "ARN of the Guardrail version"
  value       = aws_bedrock_guardrail_version.main.guardrail_arn
}

output "guardrail_created_at" {
  description = "Timestamp when the Guardrail was created"
  value       = aws_bedrock_guardrail.main.created_at
}

output "guardrail_status" {
  description = "Current status of the Guardrail"
  value       = aws_bedrock_guardrail.main.status
}
