-- Verify no room/date has more than one active hold or booked inventory row
-- Expected: empty result set after S1 contention test

SELECT room_id, date, COUNT(*) AS cnt
FROM daily_room_inventories
WHERE status IN ('held', 'booked')
GROUP BY room_id, date
HAVING COUNT(*) > 1;
