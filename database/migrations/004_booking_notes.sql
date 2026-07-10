-- Add optional admin/customer notes on bookings
ALTER TABLE `bookings`
    ADD COLUMN `notes` VARCHAR(512) NULL DEFAULT NULL COMMENT 'Booking notes (admin or customer)' AFTER `status`;
