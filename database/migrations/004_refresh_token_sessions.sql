-- ============================================================================
-- AetherStay Migration 004 — Refresh Token 轮换会话
-- 目标：新增 refresh_token_sessions 表，支撑「刷新令牌轮换 + 失效/吊销」能力。
-- 背景：schema.sql 仅在容器初始化时执行，已部署环境需手动建表。
-- 注意：CREATE TABLE IF NOT EXISTS 幂等，可安全重复执行。
-- ============================================================================

USE aetherstay;

CREATE TABLE IF NOT EXISTS `refresh_token_sessions` (
    `jti` VARCHAR(36) NOT NULL COMMENT 'JWT ID (UUID) as session primary key',
    `user_id` INT NOT NULL COMMENT 'Owning user ID',
    `expires_at` DATETIME NOT NULL COMMENT 'Refresh token expiry',
    `revoked_at` DATETIME NULL DEFAULT NULL COMMENT 'Revocation time (NULL = active)',
    PRIMARY KEY (`jti`),
    INDEX `idx_refresh_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Refresh token sessions for rotation/revocation';