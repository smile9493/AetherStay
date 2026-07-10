-- Migration: add description, amenities, image_url to room_types
-- Run manually on existing databases (Docker volumes do not re-apply schema.sql)
-- Safe to skip if columns already exist (MySQL will error on duplicate column)

USE aetherstay;

ALTER TABLE `room_types`
    ADD COLUMN `description` VARCHAR(512) DEFAULT NULL COMMENT 'Room type description',
    ADD COLUMN `amenities`   VARCHAR(512) DEFAULT NULL COMMENT 'Amenities (comma-separated)',
    ADD COLUMN `image_url`   VARCHAR(256) DEFAULT NULL COMMENT 'Room type cover image URL';

-- Seed Unsplash images for default room types (only updates rows with NULL description)
UPDATE `room_types` SET
    `description` = '舒适的标准双床房，配备两张单人床，适合商务出差或亲友同行。',
    `amenities` = 'WiFi,空调,电视,吹风机',
    `image_url` = 'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80'
WHERE `name` = 'Standard Twin' AND `description` IS NULL;

UPDATE `room_types` SET
    `description` = '宽敞的大床房，配备 King Size 舒适大床，享受优质睡眠体验。',
    `amenities` = 'WiFi,空调,电视,迷你吧,保险箱',
    `image_url` = 'https://images.unsplash.com/photo-1611892440504-42a792e56d4b?w=800&q=80'
WHERE `name` = 'Deluxe King' AND `description` IS NULL;

UPDATE `room_types` SET
    `description` = '豪华行政套房，配备独立客厅与卧室，适合家庭入住或高端商务接待。',
    `amenities` = 'WiFi,空调,电视,迷你吧,浴缸,客厅,咖啡机',
    `image_url` = 'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&q=80'
WHERE `name` = 'Executive Suite' AND `description` IS NULL;
