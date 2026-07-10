-- User profile and membership tier fields
ALTER TABLE `users`
    ADD COLUMN `display_name` VARCHAR(64) NULL DEFAULT NULL COMMENT 'Display name' AFTER `username`,
    ADD COLUMN `phone` VARCHAR(20) NULL DEFAULT NULL COMMENT 'Contact phone' AFTER `is_active`,
    ADD COLUMN `email` VARCHAR(128) NULL DEFAULT NULL COMMENT 'Contact email' AFTER `phone`,
    ADD COLUMN `membership_tier` ENUM('standard', 'silver', 'gold', 'platinum') NOT NULL DEFAULT 'standard' COMMENT 'Membership level' AFTER `email`,
    ADD COLUMN `membership_points` INT NOT NULL DEFAULT 0 COMMENT 'Loyalty points' AFTER `membership_tier`,
    ADD COLUMN `admin_notes` VARCHAR(512) NULL DEFAULT NULL COMMENT 'Admin-only notes' AFTER `membership_points`;
