-- AetherStay Hotel Booking System - Database Schema
-- MySQL 8.0+

CREATE DATABASE IF NOT EXISTS aetherstay
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_bin;

USE aetherstay;

-- 1. Users
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT COMMENT 'User primary key',
    `username` VARCHAR(64) NOT NULL UNIQUE COMMENT 'Login username',
    `password_hash` VARCHAR(255) NOT NULL COMMENT 'Argon2id password hash',
    `role` ENUM('customer', 'admin') NOT NULL DEFAULT 'customer' COMMENT 'System role',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Account creation time',
    PRIMARY KEY (`id`),
    INDEX `idx_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT='User authentication table';

-- 2. Room Types
CREATE TABLE IF NOT EXISTS `room_types` (
    `id` INT AUTO_INCREMENT COMMENT 'Room type primary key',
    `name` VARCHAR(64) NOT NULL COMMENT 'Room type name',
    `base_price` DECIMAL(10, 2) NOT NULL COMMENT 'Base price per night',
    `capacity` TINYINT NOT NULL DEFAULT 2 COMMENT 'Max guests',
    `total_rooms` INT NOT NULL DEFAULT 0 COMMENT 'Total rooms of this type',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Room type definitions';

-- 3. Rooms
CREATE TABLE IF NOT EXISTS `rooms` (
    `id` INT AUTO_INCREMENT COMMENT 'Room primary key',
    `room_number` VARCHAR(16) NOT NULL UNIQUE COMMENT 'Physical room number',
    `room_type_id` INT NOT NULL COMMENT 'Room type ID',
    `status` ENUM('active', 'inactive', 'maintenance') NOT NULL DEFAULT 'active' COMMENT 'Physical status',
    PRIMARY KEY (`id`),
    CONSTRAINT `fk_rooms_room_type` FOREIGN KEY (`room_type_id`) REFERENCES `room_types` (`id`) ON DELETE RESTRICT,
    INDEX `idx_room_type` (`room_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Physical room entities';

-- 4. Bookings (created before daily_room_inventories due to FK)
CREATE TABLE IF NOT EXISTS `bookings` (
    `id` INT AUTO_INCREMENT COMMENT 'Booking primary key',
    `user_id` INT NOT NULL COMMENT 'Booking user ID',
    `room_id` INT NOT NULL COMMENT 'Booked room ID',
    `check_in` DATE NOT NULL COMMENT 'Check-in date',
    `check_out` DATE NOT NULL COMMENT 'Check-out date',
    `total_price` DECIMAL(10, 2) NOT NULL COMMENT 'Total booking price',
    `status` ENUM('pending', 'confirmed', 'checked_in', 'checked_out', 'cancelled') NOT NULL DEFAULT 'pending' COMMENT 'Booking status',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Booking creation time',
    PRIMARY KEY (`id`),
    CONSTRAINT `fk_bookings_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_bookings_room` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`id`) ON DELETE RESTRICT,
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_room_dates_status` (`room_id`, `status`, `check_in`, `check_out`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Booking records';

-- 5. Daily Room Inventories
CREATE TABLE IF NOT EXISTS `daily_room_inventories` (
    `room_id` INT NOT NULL COMMENT 'Room ID',
    `date` DATE NOT NULL COMMENT 'Inventory date',
    `status` ENUM('available', 'held', 'booked', 'maintenance') NOT NULL DEFAULT 'available' COMMENT 'Daily inventory status',
    `held_until` TIMESTAMP NULL DEFAULT NULL COMMENT 'Hold expiration timestamp',
    `booking_id` INT NULL DEFAULT NULL COMMENT 'Associated booking ID',
    PRIMARY KEY (`room_id`, `date`),
    INDEX `idx_date_status` (`date`, `status`),
    CONSTRAINT `fk_dri_room` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_dri_booking` FOREIGN KEY (`booking_id`) REFERENCES `bookings` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Daily room inventory';

-- Seed data
INSERT INTO `room_types` (`name`, `base_price`, `capacity`, `total_rooms`) VALUES
    ('Standard Twin', 299.00, 2, 10),
    ('Deluxe King', 499.00, 2, 8),
    ('Executive Suite', 899.00, 4, 4);

INSERT INTO `rooms` (`room_number`, `room_type_id`, `status`) VALUES
    ('101', 1, 'active'), ('102', 1, 'active'), ('103', 1, 'active'),
    ('201', 2, 'active'), ('202', 2, 'active'),
    ('301', 3, 'active'), ('302', 3, 'active');

-- Generate 90 days of inventory for each room
INSERT INTO `daily_room_inventories` (`room_id`, `date`, `status`)
SELECT r.id, DATE_ADD(CURDATE(), INTERVAL d.n DAY), 'available'
FROM `rooms` r
CROSS JOIN (
    SELECT a.N + b.N * 10 + c.N * 100 AS n
    FROM (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
          UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) a,
         (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
          UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) b,
         (SELECT 0 AS N) c
    WHERE a.N + b.N * 10 + c.N * 100 < 90
) d;
