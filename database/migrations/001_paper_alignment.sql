-- ============================================================================
-- AetherStay Migration 001 — 对齐论文描述的功能改动
-- 目标：让「已存在」的 aetherstay 数据库追上 schema.sql 的最新结构。
--
-- 背景：schema.sql 仅在容器初始化时执行，已部署环境（存在 mysql_data 卷）
--       不会自动新增列/表/索引，故此脚本手动补齐增量。
--
-- 变更清单：
--   1. users            新增 phone / email / membership_tier / membership_points / admin_notes
--   2. room_types       新增 description / amenities / image_url
--   3. room_types       回填三条种子房型的媒体字段（与 schema.sql 种子一致）
--   4. bookings         新增复合索引 idx_user_created（优化「我的订单」查询）
--   5. daily_room_inventories  新增复合索引 idx_status_held_until
--   6. system_settings  新建单行设置表 + 种子行 (id=1)
--
-- 注意：ALTER TABLE 中的 ADD COLUMN / ADD INDEX 非幂等，本脚本仅需执行一次。
-- ============================================================================

USE aetherstay;

-- ----------------------------------------------------------------------------
-- 1. users：会员等级与联系方式字段
-- ----------------------------------------------------------------------------
ALTER TABLE `users`
    ADD COLUMN `phone` VARCHAR(32) NULL DEFAULT NULL COMMENT 'Contact phone' AFTER `is_active`,
    ADD COLUMN `email` VARCHAR(128) NULL DEFAULT NULL COMMENT 'Contact email' AFTER `phone`,
    ADD COLUMN `membership_tier` ENUM('regular', 'silver', 'gold', 'diamond') NOT NULL DEFAULT 'regular' COMMENT 'Membership tier' AFTER `email`,
    ADD COLUMN `membership_points` INT NOT NULL DEFAULT 0 COMMENT 'Membership points' AFTER `membership_tier`,
    ADD COLUMN `admin_notes` TEXT NULL DEFAULT NULL COMMENT 'Internal admin notes' AFTER `membership_points`;

-- ----------------------------------------------------------------------------
-- 2. room_types：房型描述/设施/图片字段
-- ----------------------------------------------------------------------------
ALTER TABLE `room_types`
    ADD COLUMN `description` TEXT NULL DEFAULT NULL COMMENT 'Room type description' AFTER `total_rooms`,
    ADD COLUMN `amenities` TEXT NULL DEFAULT NULL COMMENT 'Amenities (JSON array text)' AFTER `description`,
    ADD COLUMN `image_url` VARCHAR(512) NULL DEFAULT NULL COMMENT 'Room type image URL' AFTER `amenities`;

-- ----------------------------------------------------------------------------
-- 3. room_types：回填种子房型媒体字段（对齐 schema.sql 种子数据）
-- ----------------------------------------------------------------------------
UPDATE `room_types` SET
    `description` = '舒适标准双床房，适合商旅与结伴出行',
    `amenities` = '["免费Wi-Fi","空调","电视","24小时热水"]',
    `image_url` = '/images/standard-twin.jpg'
WHERE `name` = '标准双床房';

UPDATE `room_types` SET
    `description` = '豪华大床房，配备高端寝具与办公区',
    `amenities` = '["免费Wi-Fi","空调","智能电视","迷你吧"]',
    `image_url` = '/images/deluxe-king.jpg'
WHERE `name` = '豪华大床房';

UPDATE `room_types` SET
    `description` = '行政套房，独立起居室，尊享行政礼遇',
    `amenities` = '["免费Wi-Fi","中央空调","客厅","浴缸","行政酒廊"]',
    `image_url` = '/images/executive-suite.jpg'
WHERE `name` = '行政套房';

-- ----------------------------------------------------------------------------
-- 4. bookings：优化「我的订单」查询的复合索引
-- ----------------------------------------------------------------------------
ALTER TABLE `bookings`
    ADD INDEX `idx_user_created` (`user_id`, `created_at`);

-- ----------------------------------------------------------------------------
-- 5. daily_room_inventories：过期 Hold 扫描索引
-- ----------------------------------------------------------------------------
ALTER TABLE `daily_room_inventories`
    ADD INDEX `idx_status_held_until` (`status`, `held_until`);

-- ----------------------------------------------------------------------------
-- 6. system_settings：系统设置单行表 + 种子
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `system_settings` (
    `id` INT AUTO_INCREMENT COMMENT 'Settings primary key (single row)',
    `auto_checkout_enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'Auto checkout switch',
    `auto_checkout_time` VARCHAR(5) NOT NULL DEFAULT '12:00' COMMENT 'Daily auto checkout time (HH:MM)',
    `timezone` VARCHAR(64) NOT NULL DEFAULT 'Asia/Shanghai' COMMENT 'Timezone for checkout time comparison',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Global system settings';

INSERT INTO `system_settings` (`id`, `auto_checkout_enabled`, `auto_checkout_time`, `timezone`)
SELECT 1, 1, '12:00', 'Asia/Shanghai'
WHERE NOT EXISTS (SELECT 1 FROM `system_settings` WHERE `id` = 1);