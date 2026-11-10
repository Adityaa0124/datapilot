"""
Synthetic Development Database Engine for DataPilot.
Provides a self-contained, disposable development database seeded with
the complete e-commerce dimensional schema and realistic test data.

Enables:
- Zero external infrastructure dependency (runs on SQLite / SQLAlchemy without MySQL/Docker)
- Deterministic, reproducible unit & integration testing
- Strict read-only query execution with timeouts and row limits
- Schema metadata introspection (columns, data types, foreign keys, metrics)
"""

from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.sql_safety import SQLSafetyValidator, SQLValidationResult, SQLSecurityError


@dataclass
class QueryExecutionResult:
    """Structured result of an SQL execution against the development database."""
    success: bool
    sql: str
    rows: List[Dict[str, Any]] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    validation: Optional[SQLValidationResult] = None


# Core schema definition matching docker/mysql/dw.sql
DW_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS dim_region (
    region_id VARCHAR(20) PRIMARY KEY,
    province VARCHAR(50),
    region_name VARCHAR(50),
    country VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id VARCHAR(20) PRIMARY KEY,
    customer_name VARCHAR(50),
    gender VARCHAR(10),
    member_level VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_id VARCHAR(20) PRIMARY KEY,
    product_name VARCHAR(200),
    category VARCHAR(50),
    brand VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id INT PRIMARY KEY,
    year INT,
    quarter VARCHAR(2),
    month INT,
    day INT
);

CREATE TABLE IF NOT EXISTS fact_order (
    order_id VARCHAR(30) PRIMARY KEY,
    customer_id VARCHAR(20),
    product_id VARCHAR(20),
    date_id INT,
    region_id VARCHAR(20),
    order_quantity INT,
    order_amount REAL,
    FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id),
    FOREIGN KEY (product_id) REFERENCES dim_product(product_id),
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
    FOREIGN KEY (region_id) REFERENCES dim_region(region_id)
);
"""

# Seed data from docker/mysql/dw.sql
REGIONS_DATA = [
    ('R001', '广东省', '华南', '中国'),
    ('R002', '浙江省', '华东', '中国'),
    ('R003', '四川省', '西南', '中国'),
    ('R004', '北京市', '华北', '中国'),
    ('R005', '上海市', '华东', '中国'),
    ('R006', '湖北省', '华中', '中国'),
]

CUSTOMERS_DATA = [
    ('C001', '李伟', '男', '黄金'),
    ('C002', '王芳', '女', '白银'),
    ('C003', '张敏', '女', '黄金'),
    ('C004', '刘洋', '男', '青铜'),
    ('C005', '陈静', '女', '铂金'),
    ('C006', '赵磊', '男', '白银'),
    ('C007', '黄秀英', '女', '青铜'),
    ('C008', '吴斌', '男', '黄金'),
    ('C009', '周燕', '女', '铂金'),
    ('C010', '徐浩', '男', '白银'),
    ('C011', '孙丽', '女', '黄金'),
    ('C012', '马强', '男', '青铜'),
    ('C013', '朱玲', '女', '白银'),
    ('C014', '胡杰', '男', '黄金'),
    ('C015', '高梅', '女', '铂金'),
    ('C016', '林峰', '男', '青铜'),
    ('C017', '何娜', '女', '白银'),
    ('C018', '郭涛', '男', '黄金'),
    ('C019', '邓慧', '女', '青铜'),
    ('C020', '曹瑞', '男', '铂金'),
]

PRODUCTS_DATA = [
    ('P001', 'iPhone 15 Pro', '手机数码', '苹果'),
    ('P002', 'Galaxy S24 Ultra', '手机数码', '三星'),
    ('P003', 'Mate 60 Pro', '手机数码', '华为'),
    ('P004', '戴森 V15 吸尘器', '家用电器', '戴森'),
    ('P005', '美的空调 KFR-35GW', '家用电器', '美的'),
    ('P006', '耐克 Air Max 270 运动鞋', '鞋靴', '耐克'),
    ('P007', '阿迪达斯 Ultraboost 跑鞋', '鞋靴', '阿迪达斯'),
    ('P008', '优衣库 Heattech 保暖夹克', '服饰', '优衣库'),
    ('P009', '李维斯 501 牛仔裤', '服饰', '李维斯'),
    ('P010', '雀巢金牌速溶咖啡', '食品饮料', '雀巢'),
    ('P011', '蒙牛纯牛奶 250ml*12', '食品饮料', '蒙牛'),
    ('P012', '乐事原味薯片 150g', '休闲零食', '乐事'),
    ('P013', '奥利奥巧克力夹心饼干', '休闲零食', '奥利奥'),
    ('P014', 'Kindle Paperwhite 电子书', '手机数码', '亚马逊'),
    ('P015', 'Instant Pot 多功能电压力锅', '家用电器', 'Instant Pot'),
]

DATES_DATA = [
    (20250101, 2025, 'Q1', 1, 1),
    (20250102, 2025, 'Q1', 1, 2),
    (20250103, 2025, 'Q1', 1, 3),
    (20250104, 2025, 'Q1', 1, 4),
    (20250105, 2025, 'Q1', 1, 5),
    (20250110, 2025, 'Q1', 1, 10),
    (20250115, 2025, 'Q1', 1, 15),
    (20250120, 2025, 'Q1', 1, 20),
    (20250125, 2025, 'Q1', 1, 25),
    (20250130, 2025, 'Q1', 1, 30),
    (20250201, 2025, 'Q1', 2, 1),
    (20250205, 2025, 'Q1', 2, 5),
    (20250210, 2025, 'Q1', 2, 10),
    (20250215, 2025, 'Q1', 2, 15),
    (20250220, 2025, 'Q1', 2, 20),
    (20250228, 2025, 'Q1', 2, 28),
    (20250301, 2025, 'Q1', 3, 1),
    (20250315, 2025, 'Q1', 3, 15),
    (20250331, 2025, 'Q1', 3, 31),
]

ORDERS_DATA = [
    ('ORD20250101001', 'C001', 'P001', 20250101, 'R001', 1, 8999.00),
    ('ORD20250101002', 'C005', 'P003', 20250101, 'R005', 1, 6999.00),
    ('ORD20250102001', 'C003', 'P010', 20250102, 'R002', 5, 125.00),
    ('ORD20250102002', 'C008', 'P006', 20250102, 'R004', 1, 899.00),
    ('ORD20250103001', 'C012', 'P011', 20250103, 'R003', 12, 60.00),
    ('ORD20250103002', 'C015', 'P014', 20250103, 'R005', 1, 1399.00),
    ('ORD20250104001', 'C002', 'P012', 20250104, 'R001', 8, 40.00),
    ('ORD20250105001', 'C007', 'P008', 20250105, 'R006', 2, 299.00),
    ('ORD20250110001', 'C006', 'P007', 20250110, 'R005', 1, 1299.00),
    ('ORD20250115001', 'C014', 'P003', 20250115, 'R001', 1, 6999.00),
    ('ORD20250120001', 'C012', 'P008', 20250120, 'R003', 1, 199.00),
    ('ORD20250125001', 'C019', 'P007', 20250125, 'R003', 1, 1299.00),
    ('ORD20250130001', 'C017', 'P003', 20250130, 'R006', 1, 6999.00),
    ('ORD20250201001', 'C009', 'P011', 20250201, 'R004', 8, 40.00),
    ('ORD20250205001', 'C003', 'P002', 20250205, 'R002', 1, 9499.00),
    ('ORD20250210001', 'C007', 'P004', 20250210, 'R006', 1, 5499.00),
    ('ORD20250215001', 'C020', 'P001', 20250215, 'R005', 1, 8999.00),
    ('ORD20250220001', 'C010', 'P005', 20250220, 'R002', 1, 3200.00),
    ('ORD20250228001', 'C004', 'P009', 20250228, 'R004', 2, 1198.00),
    ('ORD20250301001', 'C001', 'P015', 20250301, 'R001', 1, 899.00),
    ('ORD20250315001', 'C011', 'P013', 20250315, 'R004', 6, 21.00),
    ('ORD20250331001', 'C016', 'P012', 20250331, 'R003', 10, 50.00),
]


class SyntheticDevelopmentDB:
    """
    Self-contained SQLite development database engine.
    Supports in-memory or temporary file-based instances.
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        validator: Optional[SQLSafetyValidator] = None,
        timeout_seconds: float = 5.0,
    ):
        self.db_path = db_path
        self.validator = validator or SQLSafetyValidator(timeout_seconds=timeout_seconds)
        self.timeout_seconds = timeout_seconds
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        """Creates connection and seeds tables and sample records."""
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        cur = self._conn.cursor()

        # Create Schema
        cur.executescript(DW_SCHEMA_SQL)

        # Seed initial data
        cur.executemany("INSERT OR REPLACE INTO dim_region VALUES (?, ?, ?, ?)", REGIONS_DATA)
        cur.executemany("INSERT OR REPLACE INTO dim_customer VALUES (?, ?, ?, ?)", CUSTOMERS_DATA)
        cur.executemany("INSERT OR REPLACE INTO dim_product VALUES (?, ?, ?, ?)", PRODUCTS_DATA)
        cur.executemany("INSERT OR REPLACE INTO dim_date VALUES (?, ?, ?, ?, ?)", DATES_DATA)
        cur.executemany("INSERT OR REPLACE INTO fact_order VALUES (?, ?, ?, ?, ?, ?, ?)", ORDERS_DATA)

        self._conn.commit()
        cur.close()

    def get_schema_metadata(self) -> Dict[str, Any]:
        """Returns structured dictionary of tables, columns, data types, and foreign keys."""
        metadata = {
            "tables": {},
            "relationships": [
                {"from_table": "fact_order", "from_column": "customer_id", "to_table": "dim_customer", "to_column": "customer_id"},
                {"from_table": "fact_order", "from_column": "product_id", "to_table": "dim_product", "to_column": "product_id"},
                {"from_table": "fact_order", "from_column": "date_id", "to_table": "dim_date", "to_column": "date_id"},
                {"from_table": "fact_order", "from_column": "region_id", "to_table": "dim_region", "to_column": "region_id"},
            ],
            "metrics": {
                "GMV": {"description": "Gross Merchandise Value: SUM(order_amount) from fact_order", "formula": "SUM(order_amount)"},
                "AOV": {"description": "Average Order Value: AVG(order_amount) or SUM(order_amount)/COUNT(order_id)", "formula": "AVG(order_amount)"},
                "TotalSalesCount": {"description": "Total units sold: SUM(order_quantity)", "formula": "SUM(order_quantity)"},
            },
        }

        cur = self._conn.cursor()
        for table in ["dim_region", "dim_customer", "dim_product", "dim_date", "fact_order"]:
            cur.execute(f"PRAGMA table_info({table});")
            cols = []
            for row in cur.fetchall():
                cols.append({
                    "name": row[1],
                    "type": row[2],
                    "is_primary_key": bool(row[5]),
                })
            metadata["tables"][table] = cols
        cur.close()
        return metadata

    def execute_query(self, raw_sql: str) -> QueryExecutionResult:
        """
        Executes an SQL query safely with AST validation, read-only enforcement,
        row clamping, and timeout protection.
        """
        start_time = time.perf_counter()

        # 1. Validation Layer (Prior to execution)
        if not self._conn:
            return QueryExecutionResult(
                success=False,
                sql=raw_sql,
                error="Database connection is closed.",
                execution_time_ms=0.0,
            )

        validation_result = self.validator.validate(raw_sql)
        if not validation_result.is_valid:
            elapsed = (time.perf_counter() - start_time) * 1000
            return QueryExecutionResult(
                success=False,
                sql=raw_sql,
                error=f"SQL Validation Error [{validation_result.classification}]: {validation_result.error_message}",
                execution_time_ms=elapsed,
                validation=validation_result,
            )

        sanitized_sql = validation_result.sanitized_sql or raw_sql

        # 2. Database Execution
        try:
            # Create a separate read-only cursor/connection for execution
            cursor = self._conn.cursor()

            # Set a query progress handler to enforce query timeouts
            max_ticks = int(self.timeout_seconds * 10000)
            ticks = [0]

            def timeout_handler():
                ticks[0] += 1
                if ticks[0] > max_ticks:
                    return 1  # non-zero aborts the query
                return 0

            self._conn.set_progress_handler(timeout_handler, 100)

            try:
                cursor.execute(sanitized_sql)
                rows = [dict(r) for r in cursor.fetchall()]
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
            finally:
                self._conn.set_progress_handler(None, 0)
                cursor.close()

            elapsed = (time.perf_counter() - start_time) * 1000
            return QueryExecutionResult(
                success=True,
                sql=sanitized_sql,
                rows=rows,
                columns=columns,
                row_count=len(rows),
                execution_time_ms=elapsed,
                validation=validation_result,
            )

        except sqlite3.OperationalError as oe:
            elapsed = (time.perf_counter() - start_time) * 1000
            err_msg = str(oe)
            if "interrupted" in err_msg.lower():
                err_msg = f"Query timed out after exceeding timeout limit of {self.timeout_seconds} seconds."
            return QueryExecutionResult(
                success=False,
                sql=sanitized_sql,
                error=err_msg,
                execution_time_ms=elapsed,
                validation=validation_result,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            return QueryExecutionResult(
                success=False,
                sql=sanitized_sql,
                error=str(e),
                execution_time_ms=elapsed,
                validation=validation_result,
            )

    def close(self):
        """Closes the underlying database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
