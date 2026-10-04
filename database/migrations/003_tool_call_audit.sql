-- ============================================================================
-- AetherStay Migration 003 — MCP/Agent 工具调用审计日志
-- 目标：新增 tool_call_audit_logs 表，支撑「工具调用审计」能力。
-- 背景：schema.sql 仅在容器初始化时执行，已部署环境需手动建表。
-- 注意：CREATE TABLE IF NOT EXISTS 幂等，可安全重复执行。
-- ============================================================================

USE aetherstay;

CREATE TABLE IF NOT EXISTS `tool_call_audit_logs` (
    `id` INT AUTO_INCREMENT COMMENT 'Audit log primary key',
    `user_id` INT NULL DEFAULT NULL COMMENT 'Calling user ID (NULL for anonymous)',
    `tool_name` VARCHAR(64) NOT NULL COMMENT 'Tool name invoked',
    `arguments` TEXT NULL DEFAULT NULL COMMENT 'Serialized tool arguments',
    `result` TEXT NULL DEFAULT NULL COMMENT 'Serialized tool result',
    `success` TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'Whether the call succeeded',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Invocation time',
    PRIMARY KEY (`id`),
    INDEX `idx_audit_user_created` (`user_id`, `created_at`),
    INDEX `idx_audit_tool` (`tool_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='MCP/agent tool call audit log';