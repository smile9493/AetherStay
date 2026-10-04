-- ============================================================================
-- AetherStay Migration 002 — 预订接口幂等键
-- 目标：为 bookings 增加 idempotency_key 列与唯一索引，支撑「接口幂等」能力。
-- 背景：schema.sql 仅在容器初始化时执行，已部署环境（存在 mysql_data 卷）
--       不会自动新增列/索引，故此脚本手动补齐增量。
-- 注意：ALTER TABLE ADD COLUMN / ADD INDEX 非幂等，本脚本仅需执行一次。
-- ============================================================================

USE aetherstay;

ALTER TABLE `bookings`
    ADD COLUMN `idempotency_key` VARCHAR(64) NULL DEFAULT NULL COMMENT 'Idempotency key for duplicate request dedup' AFTER `created_at`,
    ADD UNIQUE INDEX `idx_idempotency_key` (`idempotency_key`);