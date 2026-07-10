-- Migration 003: system_settings table for admin-configurable runtime settings
USE aetherstay;

CREATE TABLE IF NOT EXISTS `system_settings` (
    `key` VARCHAR(64) NOT NULL COMMENT 'Setting key',
    `value` VARCHAR(512) NOT NULL COMMENT 'Setting value',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time',
    PRIMARY KEY (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Runtime system settings';

INSERT INTO `system_settings` (`key`, `value`) VALUES
    ('auto_checkout_enabled', 'true'),
    ('auto_checkout_time', '12:00'),
    ('timezone', 'Asia/Shanghai')
ON DUPLICATE KEY UPDATE `value` = VALUES(`value`);
