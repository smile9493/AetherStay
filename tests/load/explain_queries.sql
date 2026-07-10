-- EXPLAIN queries for Week 6 index optimization
-- Run before/after adding idx_status_held_until

-- Q1: release_expired_holds scheduler scan
EXPLAIN ANALYZE
SELECT room_id, date, status, held_until, booking_id
FROM daily_room_inventories
WHERE status = 'held'
  AND held_until IS NOT NULL
  AND held_until < UTC_TIMESTAMP();

-- Q2: lock_inventory_for_update (pessimistic lock)
-- Replace room_id and dates with sample values from seed data
EXPLAIN ANALYZE
SELECT room_id, date, status, held_until, booking_id
FROM daily_room_inventories
WHERE room_id = 1
  AND date >= CURDATE() + INTERVAL 90 DAY
  AND date < CURDATE() + INTERVAL 92 DAY
FOR UPDATE;
