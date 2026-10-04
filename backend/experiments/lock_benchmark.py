"""意见6·实验：库存并发控制三种策略对照基准。

在真实 MySQL 上，固定数据规模，以并发梯度对「无锁 / 等待锁 / NOWAIT」三种
预订并发控制策略做对照，量化报告 TPS、P50/P95/P99 延迟、锁冲突率、重试成功
率与超售数量，为论文提供证据。

用法（在 backend 目录下）：
    venv/Scripts/python.exe experiments/lock_benchmark.py
"""

import asyncio
import time
from datetime import date, timedelta

import aiomysql
import pymysql

HOST, PORT, USER, PASSWORD = "127.0.0.1", 3307, "root", "root"
BENCH_DB = "aetherstay_bench"

NIGHTS = 1
RETRY_TIMES = 3
RETRY_BASE_MS = 50


def setup() -> None:
    conn = pymysql.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, autocommit=True)
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {BENCH_DB}")
    cur.execute(f"CREATE DATABASE {BENCH_DB} DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_bin")
    cur.execute(f"USE {BENCH_DB}")
    cur.execute(
        """
        CREATE TABLE bench_inv (
            room_id INT NOT NULL,
            date DATE NOT NULL,
            status ENUM('available','booked') NOT NULL DEFAULT 'available',
            booking_id INT NULL,
            PRIMARY KEY (room_id, date)
        ) ENGINE=InnoDB
        """
    )
    cur.execute(
        """
        CREATE TABLE bench_bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            room_id INT NOT NULL,
            check_in DATE NOT NULL,
            check_out DATE NOT NULL
        ) ENGINE=InnoDB
        """
    )
    conn.close()


async def reset_state(pool, rooms, check_in) -> None:
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM bench_bookings")
            await cur.execute("DELETE FROM bench_inv")
            for r in range(1, rooms + 1):
                await cur.execute(
                    "INSERT INTO bench_inv (room_id, date, status) VALUES (%s, %s, 'available')",
                    (r, check_in),
                )
            await conn.commit()


def _is_lock_wait_error(e: Exception) -> bool:
    return "3572" in str(e) or "1205" in str(e) or "1213" in str(e)


# 各策略复用的 SQL
SEL = "SELECT status FROM bench_inv WHERE room_id=%s AND date>=%s AND date<%s"
INS = "INSERT INTO bench_bookings (user_id, room_id, check_in, check_out) VALUES (%s,%s,%s,%s)"
UPD = "UPDATE bench_inv SET status='booked', booking_id=%s WHERE room_id=%s AND date>=%s AND date<%s"


def _ok(msg, ms, ok=True):
    return {"ok": ok, "reason": msg, "ms": ms}


async def book_no_lock(pool, room_id, check_in, user_id):
    co = check_in + timedelta(days=NIGHTS)
    t0 = time.perf_counter()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(SEL, (room_id, check_in, co))
            rows = await cur.fetchall()
            if len(rows) != NIGHTS or any(r[0] != "available" for r in rows):
                return _ok("no_room", (time.perf_counter() - t0) * 1000, ok=False)
            # 无锁：无条件写入（并发下两个请求都读到 available → 双双写入 → 超卖）
            await conn.begin()
            await cur.execute(INS, (user_id, room_id, check_in, co))
            bid = cur.lastrowid
            await cur.execute(UPD, (bid, room_id, check_in, co))
            await conn.commit()
            return _ok("success", (time.perf_counter() - t0) * 1000)


async def book_wait_lock(pool, room_id, check_in, user_id):
    co = check_in + timedelta(days=NIGHTS)
    t0 = time.perf_counter()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await conn.begin()
            await cur.execute(SEL + " FOR UPDATE", (room_id, check_in, co))
            rows = await cur.fetchall()
            if len(rows) != NIGHTS or any(r[0] != "available" for r in rows):
                await conn.rollback()
                return _ok("no_room", (time.perf_counter() - t0) * 1000, ok=False)
            await cur.execute(INS, (user_id, room_id, check_in, co))
            bid = cur.lastrowid
            await cur.execute(UPD, (bid, room_id, check_in, co))
            await conn.commit()
            return _ok("success", (time.perf_counter() - t0) * 1000)


async def book_nowait(pool, room_id, check_in, user_id):
    co = check_in + timedelta(days=NIGHTS)
    t0 = time.perf_counter()
    conflicts = 0
    for attempt in range(RETRY_TIMES):
        retry = False
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await conn.begin()
                try:
                    await cur.execute(SEL + " FOR UPDATE NOWAIT", (room_id, check_in, co))
                except pymysql.err.OperationalError as e:
                    await conn.rollback()
                    if _is_lock_wait_error(e):
                        conflicts += 1
                        if attempt < RETRY_TIMES - 1:
                            retry = True
                        else:
                            return {"ok": False, "reason": "lock_conflict", "ms": (time.perf_counter() - t0) * 1000,
                                    "conflicts": conflicts, "retried_ok": False}
                    else:
                        return {"ok": False, "reason": "error", "ms": (time.perf_counter() - t0) * 1000,
                                "conflicts": conflicts, "retried_ok": False}
                else:
                    rows = await cur.fetchall()
                    if len(rows) != NIGHTS or any(r[0] != "available" for r in rows):
                        await conn.rollback()
                        return {"ok": False, "reason": "no_room", "ms": (time.perf_counter() - t0) * 1000,
                                "conflicts": conflicts, "retried_ok": False}
                    await cur.execute(INS, (user_id, room_id, check_in, co))
                    bid = cur.lastrowid
                    await cur.execute(UPD, (bid, room_id, check_in, co))
                    await conn.commit()
                    return {"ok": True, "reason": "success", "ms": (time.perf_counter() - t0) * 1000,
                            "conflicts": conflicts, "retried_ok": conflicts > 0}
        if retry:
            await asyncio.sleep(RETRY_BASE_MS * (2 ** attempt) / 1000.0)
    return {"ok": False, "reason": "lock_conflict", "ms": (time.perf_counter() - t0) * 1000,
            "conflicts": conflicts, "retried_ok": False}


STRATEGIES = {
    "no_lock": book_no_lock,
    "wait_lock": book_wait_lock,
    "nowait": book_nowait,
}


def _pct(vals, p):
    if not vals:
        return 0.0
    vals = sorted(vals)
    idx = min(len(vals) - 1, int(len(vals) * p))
    return vals[idx]


async def count_oversell(pool, rooms, check_in) -> tuple[int, int]:
    """返回 (超订组数, 总超售量)。容量为 1，同 (room, 入住/离店) 出现 c>1 条即超订 c 组，
    总超售量 = Σ(c-1)。"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) g, COALESCE(SUM(c - 1), 0) e FROM "
                "(SELECT room_id, COUNT(*) c FROM bench_bookings "
                "GROUP BY room_id, check_in, check_out HAVING c > 1) t"
            )
            row = await cur.fetchone()
            return int(row[0]), int(row[1])


async def main():
    setup()
    check_in = date.today() + timedelta(days=30)
    pool = await aiomysql.create_pool(
        host=HOST, port=PORT, user=USER, password=PASSWORD, db=BENCH_DB,
        autocommit=True, minsize=1, maxsize=200, charset="utf8mb4",
    )

    # ---- 场景 1：热点争抢（同一房间，容量 1）验证防超卖正确性 ----
    print("=" * 92)
    print("场景1 热点争抢（1 间房 1 晚，容量 1）：防超卖正确性（C=50）")
    print("=" * 92)
    C = 50
    for name, fn in STRATEGIES.items():
        await reset_state(pool, 1, check_in)
        tasks = [(1, check_in, i + 1) for i in range(C)]
        start = time.perf_counter()
        results = await asyncio.gather(*[fn(pool, r, ci, u) for (r, ci, u) in tasks])
        elapsed = time.perf_counter() - start
        groups, excess = await count_oversell(pool, 1, check_in)
        reasons = {}
        for r in results:
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
        line = (
            f"  {name:10s} 成功={sum(1 for r in results if r['ok']):3d}  "
            f"超售组数={groups} 总超售量={excess}  耗时={elapsed:5.2f}s  分布={reasons}"
        )
        if name == "nowait":
            conflicted = sum(1 for r in results if r.get("conflicts", 0) > 0)
            retry_ok = sum(1 for r in results if r.get("retried_ok"))
            line += f" | 首轮锁冲突率={reasons.get('lock_conflict', 0)}/50  重试成功={retry_ok}/{conflicted}"
        print(line)

    # ---- 场景 2：吞吐与延迟（50 间房，轮转分配，低争用） ----
    print()
    print("=" * 92)
    print("场景2 吞吐与延迟（50 间房 × 500 请求，轮转分配低争用：TPS / P50 / P95 / P99）")
    print("=" * 92)
    ROOMS = 50
    room_cycle = [(i % ROOMS) + 1 for i in range(500)]
    for concurrency in (10, 50, 100):
        print(f"  并发 C={concurrency}")
        for name, fn in STRATEGIES.items():
            await reset_state(pool, ROOMS, check_in)
            sem = asyncio.Semaphore(concurrency)

            async def limited(room_id, i):
                async with sem:
                    return await fn(pool, room_id, check_in, i + 1)

            start = time.perf_counter()
            results = await asyncio.gather(
                *[limited(room_id, i) for i, room_id in enumerate(room_cycle)]
            )
            elapsed = time.perf_counter() - start
            lats = [r["ms"] for r in results]
            ok = sum(1 for r in results if r["ok"])
            total = len(results)
            print(
                f"    {name:10s} TPS={total/elapsed:7.1f}/s  P50={_pct(lats,.5):7.1f}ms  "
                f"P95={_pct(lats,.95):7.1f}ms  P99={_pct(lats,.99):7.1f}ms  成功={ok:3d}"
            )

    # ---- 场景 3：高争用（50 间房随机分配，500 请求，C=100）暴露锁冲突 ----
    print()
    print("=" * 92)
    print("场景3 高争用（50 间房随机分配 × 500 请求，C=100：锁冲突率 / 重试）")
    print("=" * 92)
    import random as _r
    _r.seed(42)
    random_rooms = [_r.randint(1, ROOMS) for _ in range(500)]
    for name, fn in STRATEGIES.items():
        await reset_state(pool, ROOMS, check_in)
        sem = asyncio.Semaphore(100)

        async def limited_rand(room_id, i):
            async with sem:
                return await fn(pool, room_id, check_in, i + 1)

        start = time.perf_counter()
        results = await asyncio.gather(
            *[limited_rand(room_id, i) for i, room_id in enumerate(random_rooms)]
        )
        elapsed = time.perf_counter() - start
        lats = [r["ms"] for r in results]
        ok = sum(1 for r in results if r["ok"])
        total = len(results)
        groups, excess = await count_oversell(pool, ROOMS, check_in)
        lock_c = sum(1 for r in results if r["reason"] == "lock_conflict")
        line = (
            f"  {name:10s} TPS={total/elapsed:7.1f}/s  P95={_pct(lats,.95):7.1f}ms  "
            f"P99={_pct(lats,.99):7.1f}ms  成功={ok:3d}  锁冲突率={lock_c/total*100:4.1f}%  "
            f"超售量={excess}"
        )
        if name == "nowait":
            conflicted = sum(1 for r in results if r.get("conflicts", 0) > 0)
            retry_ok = sum(1 for r in results if r.get("retried_ok"))
            line += f"  重试成功={retry_ok}/{conflicted}"
        print(line)

    pool.close()
    await pool.wait_closed()
    print("\n[done] 数据保留在库 aetherstay_bench，可复用或手动删除。")


if __name__ == "__main__":
    asyncio.run(main())