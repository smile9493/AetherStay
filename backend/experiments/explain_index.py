"""意见2·实验：核心查询的 EXPLAIN ANALYZE 对比。

对预订链路三条核心 SQL，在真实 MySQL 上造数后，用 EXPLAIN ANALYZE
比较「全表扫描 / 不同索引顺序」的执行时间与扫描行数，为论文提供量化证据。

用法（在 backend 目录下）：
    venv/Scripts/python.exe experiments/explain_index.py
"""

import re
from datetime import date, timedelta

import pymysql

HOST, PORT, USER, PASSWORD = "127.0.0.1", 3307, "root", "root"
EXP_DB = "aetherstay_exp"

# 数据规模：ROOMS 间房 × DAYS 天库存
ROOMS = 300
DAYS = 365
STAY_NIGHTS = 3  # 搜索入住晚数

# 每组查询在相同数据与索引条件下重复执行的次数，报告值取中位数以消除单次抖动
REPEAT = 10


def connect(db: str | None = None):
    return pymysql.connect(
        host=HOST, port=PORT, user=USER, password=PASSWORD,
        database=db, autocommit=True, charset="utf8mb4",
    )


def setup() -> None:
    conn = connect()
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {EXP_DB}")
    cur.execute(
        f"CREATE DATABASE {EXP_DB} DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_bin"
    )
    cur.execute(f"USE {EXP_DB}")
    cur.execute(
        """
        CREATE TABLE rooms (
            id INT PRIMARY KEY,
            status ENUM('active','inactive','maintenance') NOT NULL DEFAULT 'active'
        ) ENGINE=InnoDB
        """
    )
    cur.execute(
        """
        CREATE TABLE daily_room_inventories (
            room_id INT NOT NULL,
            date DATE NOT NULL,
            status ENUM('available','held','booked','maintenance') NOT NULL DEFAULT 'available',
            PRIMARY KEY (room_id, date)
        ) ENGINE=InnoDB
        """
    )
    # 造数：ROOMS 间房，DAYS 天；状态分布 available 70% / booked 20% / held 5% / maintenance 5%
    today = date.today()
    for r in range(1, ROOMS + 1):
        cur.execute("INSERT INTO rooms (id, status) VALUES (%s, 'active')", (r,))
    rows = []
    for r in range(1, ROOMS + 1):
        for d in range(DAYS):
            day = today + timedelta(days=d)
            stamp = (r * 31 + d) % 20
            status = "available" if stamp < 14 else "booked" if stamp < 18 else "held" if stamp < 19 else "maintenance"
            rows.append((r, day.isoformat(), status))
    cur.executemany(
        "INSERT INTO daily_room_inventories (room_id, date, status) VALUES (%s, %s, %s)",
        rows,
    )
    conn.close()
    print(f"[setup] 已造数：{ROOMS} 间房 × {DAYS} 天 = {len(rows):,} 条库存行\n")


def explain(cur, sql: str, params=()) -> tuple[str, float, str, str]:
    """返回 (完整EXPLAIN文本, cost_ms, 最外层rows, 叶子扫描行数)。"""
    cur.execute("EXPLAIN ANALYZE " + sql, params)
    text = "\n".join(str(r[0]) for r in cur.fetchall())
    m = re.search(r"actual time=([\d.]+)\.\.([\d.]+)", text)
    cost = float(m.group(2)) if m else 0.0
    first = text.splitlines()[0] if text else ""
    mrows = re.search(r"rows=(\d+)", first)
    outer_rows = mrows.group(1) if mrows else "?"
    # 叶子扫描行数：取树中所有 "rows=N" 的最大值（近似表/索引实际读取行数）
    all_rows = [int(x) for x in re.findall(r"rows=(\d+)", text)]
    leaf_rows = str(max(all_rows)) if all_rows else "?"
    return text, cost, outer_rows, leaf_rows


def median(vals):
    vals = sorted(vals)
    n = len(vals)
    mid = n // 2
    return vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2


def measure(cur, sql: str, params=()) -> tuple[float, str]:
    """重复测量 REPEAT 次，返回 (cost_ms 中位数, 叶子扫描行数中位数)。"""
    costs, leaves = [], []
    for _ in range(REPEAT):
        _, cost, _, leaf = explain(cur, sql, params)
        costs.append(cost)
        leaves.append(int(leaf))
    return median(costs), str(int(median([float(x) for x in leaves])))


SEARCH_SQL = (
    "SELECT room_id FROM daily_room_inventories "
    "WHERE date >= %s AND date < %s AND status = 'available' "
    "GROUP BY room_id HAVING COUNT(*) = %s"
)
LOCK_SQL = (
    "SELECT room_id, date, status FROM daily_room_inventories "
    "WHERE room_id = %s AND date >= %s AND date < %s FOR UPDATE"
)
MYBOOKINGS_SQL = (
    "SELECT id FROM bookings WHERE user_id = %s ORDER BY created_at DESC LIMIT 50"
)


def _hinted(sql: str, table: str, hint: str) -> str:
    """在 FROM <table> 后插入索引 hint（FORCE/IGNORE INDEX）。"""
    return sql.replace(f"FROM {table}", f"FROM {table} {hint}", 1)


def main():
    setup()
    conn = connect(EXP_DB)
    cur = conn.cursor()

    today = date.today()
    ci = (today + timedelta(days=30)).isoformat()
    co = (today + timedelta(days=30 + STAY_NIGHTS)).isoformat()

    print("=" * 92)
    print(f"Q1 搜索可用房间（{STAY_NIGHTS} 晚，date 范围 + status 过滤 + GROUP BY）")
    print("=" * 92)

    def run_q1(label, hint):
        cost, leaf = measure(cur, _hinted(SEARCH_SQL, "daily_room_inventories", hint), (ci, co, STAY_NIGHTS))
        print(f"  {label:34s} cost={cost:9.3f}ms  scanned_rows={leaf}  (中位数, N={REPEAT})")

    run_q1("全表扫描", "IGNORE INDEX (PRIMARY)")
    cur.execute("CREATE INDEX idx_date_status ON daily_room_inventories (date, status)")
    run_q1("idx_date_status(date,status)", "FORCE INDEX (idx_date_status)")
    cur.execute("DROP INDEX idx_date_status ON daily_room_inventories")
    cur.execute("CREATE INDEX idx_status_date ON daily_room_inventories (status, date)")
    run_q1("idx_status_date(status,date)", "FORCE INDEX (idx_status_date)")
    cur.execute("DROP INDEX idx_status_date ON daily_room_inventories")

    print()
    print("=" * 92)
    print("Q2 预订加锁（room_id 等值 + date 范围 FOR UPDATE）")
    print("=" * 92)
    room_pick = ROOMS // 2

    def run_q2(label, hint):
        cost, leaf = measure(cur, _hinted(LOCK_SQL, "daily_room_inventories", hint), (room_pick, ci, co))
        print(f"  {label:34s} cost={cost:9.3f}ms  scanned_rows={leaf}  (中位数, N={REPEAT})")

    run_q2("全表扫描", "IGNORE INDEX (PRIMARY)")
    run_q2("主键 PRIMARY(room_id,date)", "FORCE INDEX (PRIMARY)")

    print()
    print("=" * 92)
    print("Q3 我的订单（user_id 等值 + created_at 排序，20 万行 bookings）")
    print("=" * 92)
    cur.execute(
        """
        CREATE TABLE bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            created_at DATETIME NOT NULL
        ) ENGINE=InnoDB
        """
    )
    b = []
    for i in range(200_000):
        uid = (i % 5000) + 1
        b.append((uid, f"2026-01-{(i % 28) + 1:02d} {(i % 24):02d}:{(i % 60):02d}:00"))
    cur.executemany("INSERT INTO bookings (user_id, created_at) VALUES (%s, %s)", b)
    target_uid = 1234

    def run_q3(label, hint):
        cost, leaf = measure(cur, _hinted(MYBOOKINGS_SQL, "bookings", hint), (target_uid,))
        print(f"  {label:34s} cost={cost:9.3f}ms  scanned_rows={leaf}  (中位数, N={REPEAT})")

    run_q3("无复合索引（全表扫描）", "IGNORE INDEX (PRIMARY)")
    cur.execute("CREATE INDEX idx_user_created ON bookings (user_id, created_at)")
    run_q3("idx_user_created(user_id,created_at)", "FORCE INDEX (idx_user_created)")

    conn.close()
    print("\n[done] 数据保留在库 aetherstay_exp，可复用或手动删除。")


if __name__ == "__main__":
    main()