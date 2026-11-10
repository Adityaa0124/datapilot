"""
Schema Retriever Module for Schema-Aware SQL Generation.
Identifies and retrieves only the relevant tables, columns, foreign key relationships,
data types, and metric definitions for a given natural-language question.
Prevents sending the entire database catalog to the LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class RetrievedTableContext:
    table_name: str
    role: str
    description: str
    columns: List[Dict[str, Any]]
    foreign_keys: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class SchemaContext:
    tables: List[RetrievedTableContext]
    relevant_metrics: List[Dict[str, Any]]
    join_paths: List[str]
    date_context: Optional[Dict[str, str]] = None


# Comprehensive Schema Dictionary with descriptions, types, and sample values
SCHEMA_CATALOG: Dict[str, Dict[str, Any]] = {
    "dim_region": {
        "role": "dim",
        "description": "地区维度表，记录订单发生的地理区域信息 (大区、省份、国家)",
        "keywords": ["地区", "区域", "大区", "省份", "省", "国家", "广东", "华东", "华南", "region", "province"],
        "columns": [
            {"name": "region_id", "type": "VARCHAR(20)", "role": "primary_key", "description": "地区唯一编号 (如 R001)", "examples": ["R001", "R002"]},
            {"name": "province", "type": "VARCHAR(50)", "role": "dimension", "description": "省份名称 (如 广东省, 浙江省, 北京市)", "examples": ["广东省", "浙江省", "北京市"]},
            {"name": "region_name", "type": "VARCHAR(50)", "role": "dimension", "description": "大区名称 (如 华东, 华南, 西南, 华北)", "examples": ["华东", "华南", "华北"]},
            {"name": "country", "type": "VARCHAR(50)", "role": "dimension", "description": "国家名称 (如 中国)", "examples": ["中国"]},
        ],
    },
    "dim_customer": {
        "role": "dim",
        "description": "客户维度表，描述下单客户的基本属性 (客户姓名、性别、会员等级)",
        "keywords": ["客户", "用户", "会员", "姓名", "性别", "等级", "铂金", "黄金", "白银", "青铜", "customer", "member"],
        "columns": [
            {"name": "customer_id", "type": "VARCHAR(20)", "role": "primary_key", "description": "客户唯一标识 (如 C001)", "examples": ["C001", "C002"]},
            {"name": "customer_name", "type": "VARCHAR(50)", "role": "dimension", "description": "客户姓名 (如 李伟, 王芳)", "examples": ["李伟", "王芳"]},
            {"name": "gender", "type": "VARCHAR(10)", "role": "dimension", "description": "性别 (男/女)", "examples": ["男", "女"]},
            {"name": "member_level", "type": "VARCHAR(20)", "role": "dimension", "description": "会员等级 (青铜, 白银, 黄金, 铂金)", "examples": ["黄金", "白银", "铂金", "青铜"]},
        ],
    },
    "dim_product": {
        "role": "dim",
        "description": "商品维度表，描述商品的基本属性 (商品名、类别、品牌)",
        "keywords": ["商品", "产品", "品类", "类别", "品牌", "苹果", "华为", "耐克", "手机", "电器", "product", "category", "brand"],
        "columns": [
            {"name": "product_id", "type": "VARCHAR(20)", "role": "primary_key", "description": "商品唯一标识 (如 P001)", "examples": ["P001", "P002"]},
            {"name": "product_name", "type": "VARCHAR(200)", "role": "dimension", "description": "商品名称 (如 iPhone 15 Pro, Mate 60 Pro)", "examples": ["iPhone 15 Pro", "Mate 60 Pro"]},
            {"name": "category", "type": "VARCHAR(50)", "role": "dimension", "description": "商品类别 (手机数码, 家用电器, 鞋靴, 服饰, 食品饮料, 休闲零食)", "examples": ["手机数码", "家用电器", "鞋靴"]},
            {"name": "brand", "type": "VARCHAR(50)", "role": "dimension", "description": "品牌名称 (苹果, 三星, 华为, 戴森, 美的, 耐克)", "examples": ["苹果", "华为", "耐克"]},
        ],
    },
    "dim_date": {
        "role": "dim",
        "description": "时间维度表，用于多粒度时间周期统计 (年、季度、月、日)",
        "keywords": ["时间", "日期", "年份", "年", "月", "月份", "季度", "天", "日", "date", "year", "month", "quarter", "day", "今年", "本月", "2025"],
        "columns": [
            {"name": "date_id", "type": "INT", "role": "primary_key", "description": "日期编码 yyyyMMdd (如 20250101)", "examples": [20250101, 20250201]},
            {"name": "year", "type": "INT", "role": "dimension", "description": "年份 (如 2025)", "examples": [2025]},
            {"name": "quarter", "type": "VARCHAR(2)", "role": "dimension", "description": "季度 (Q1, Q2, Q3, Q4)", "examples": ["Q1", "Q2"]},
            {"name": "month", "type": "INT", "role": "dimension", "description": "月份 1-12", "examples": [1, 2, 3]},
            {"name": "day", "type": "INT", "role": "dimension", "description": "日期天数 1-31", "examples": [1, 15, 30]},
        ],
    },
    "fact_order": {
        "role": "fact",
        "description": "订单事实表，记录订单的核心度量 (订单量、订单金额、关联外键)",
        "keywords": ["订单", "销量", "数量", "销售额", "金额", "收入", "GMV", "AOV", "客单价", "购买", "order", "sales", "revenue", "amount", "quantity"],
        "columns": [
            {"name": "order_id", "type": "VARCHAR(30)", "role": "primary_key", "description": "订单编号", "examples": ["ORD20250101001"]},
            {"name": "customer_id", "type": "VARCHAR(20)", "role": "foreign_key", "description": "客户外键 -> dim_customer.customer_id", "examples": ["C001", "C002"]},
            {"name": "product_id", "type": "VARCHAR(20)", "role": "foreign_key", "description": "商品外键 -> dim_product.product_id", "examples": ["P001", "P002"]},
            {"name": "date_id", "type": "INT", "role": "foreign_key", "description": "日期外键 -> dim_date.date_id", "examples": [20250101]},
            {"name": "region_id", "type": "VARCHAR(20)", "role": "foreign_key", "description": "地区外键 -> dim_region.region_id", "examples": ["R001"]},
            {"name": "order_quantity", "type": "INT", "role": "measure", "description": "订单商品购买件数", "examples": [1, 5, 10]},
            {"name": "order_amount", "type": "REAL", "role": "measure", "description": "订单实付成交金额", "examples": [8999.0, 125.0]},
        ],
    },
}

FOREIGN_KEYS: List[Dict[str, str]] = [
    {"from_table": "fact_order", "from_column": "customer_id", "to_table": "dim_customer", "to_column": "customer_id"},
    {"from_table": "fact_order", "from_column": "product_id", "to_table": "dim_product", "to_column": "product_id"},
    {"from_table": "fact_order", "from_column": "date_id", "to_table": "dim_date", "to_column": "date_id"},
    {"from_table": "fact_order", "from_column": "region_id", "to_table": "dim_region", "to_column": "region_id"},
]

METRIC_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "GMV": {
        "name": "GMV",
        "description": "Gross Merchandise Value: 成交总额，计算公式为 SUM(fact_order.order_amount)",
        "formula": "SUM(order_amount)",
        "required_tables": ["fact_order"],
    },
    "AOV": {
        "name": "AOV",
        "description": "Average Order Value: 平均客单价，计算公式为 AVG(fact_order.order_amount) 或 SUM(order_amount)/COUNT(DISTINCT order_id)",
        "formula": "AVG(order_amount)",
        "required_tables": ["fact_order"],
    },
    "TotalOrders": {
        "name": "TotalOrders",
        "description": "订单总量，计算公式为 COUNT(fact_order.order_id)",
        "formula": "COUNT(order_id)",
        "required_tables": ["fact_order"],
    },
    "TotalUnits": {
        "name": "TotalUnits",
        "description": "总销售件数，计算公式为 SUM(fact_order.order_quantity)",
        "formula": "SUM(order_quantity)",
        "required_tables": ["fact_order"],
    },
}


class SchemaRetriever:
    """
    Intelligent Schema Retriever that selects only tables and columns relevant
    to the user's natural language question and conversational history.
    """

    def __init__(self, catalog: Optional[Dict[str, Dict[str, Any]]] = None):
        self.catalog = catalog or SCHEMA_CATALOG
        self.foreign_keys = FOREIGN_KEYS
        self.metrics = METRIC_DEFINITIONS

    def retrieve_schema_context(
        self,
        query: str,
        conversation_context: Optional[List[str]] = None,
    ) -> SchemaContext:
        """
        Analyzes the query keywords and returns a compact SchemaContext containing
        only relevant tables, columns, foreign keys, and metrics.
        """
        combined_text = query.lower()
        if conversation_context:
            combined_text += " " + " ".join(conversation_context).lower()

        selected_tables: Set[str] = set()

        # 1. Match tables by keywords
        for table_name, table_meta in self.catalog.items():
            for kw in table_meta["keywords"]:
                if kw.lower() in combined_text:
                    selected_tables.add(table_name)
                    break

        # 2. Check for metric mentions (GMV, AOV, sales, revenue, orders)
        selected_metrics = []
        for metric_name, metric_info in self.metrics.items():
            if metric_name.lower() in combined_text or any(k in combined_text for k in ["金额", "销售额", "客单价", "销量", "总额"]):
                selected_metrics.append(metric_info)
                for req_t in metric_info["required_tables"]:
                    selected_tables.add(req_t)

        # 3. Default fallback: if no tables matched or query is broad, always include fact_order
        if not selected_tables or any(w in combined_text for w in ["销售", "订单", "买", "卖", "前", "top", "最高", "排行"]):
            selected_tables.add("fact_order")

        # 4. Resolve join relationships: if dimensional tables are selected along with fact_order,
        # ensure foreign key connectivity is included
        join_paths = []
        for fk in self.foreign_keys:
            if fk["from_table"] in selected_tables and fk["to_table"] in selected_tables:
                join_paths.append(
                    f"{fk['from_table']}.{fk['from_column']} = {fk['to_table']}.{fk['to_column']}"
                )

        # 5. Build structured table context
        retrieved_tables: List[RetrievedTableContext] = []
        for t_name in sorted(list(selected_tables)):
            if t_name in self.catalog:
                meta = self.catalog[t_name]
                fks = [
                    fk for fk in self.foreign_keys
                    if fk["from_table"] == t_name or fk["to_table"] == t_name
                ]
                retrieved_tables.append(
                    RetrievedTableContext(
                        table_name=t_name,
                        role=meta["role"],
                        description=meta["description"],
                        columns=meta["columns"],
                        foreign_keys=fks,
                    )
                )

        return SchemaContext(
            tables=retrieved_tables,
            relevant_metrics=selected_metrics,
            join_paths=join_paths,
            date_context={"current_year": "2025", "default_quarter": "Q1"},
        )

    def format_schema_prompt(self, context: SchemaContext) -> str:
        """
        Formats the retrieved SchemaContext into a clear, structured prompt section.
        """
        lines = ["=== RELEVANT DATABASE SCHEMA ==="]
        for table in context.tables:
            lines.append(f"\nTable: {table.table_name} ({table.role.upper()})")
            lines.append(f"Description: {table.description}")
            lines.append("Columns:")
            for col in table.columns:
                examples_str = f" [Examples: {', '.join(str(e) for e in col['examples'][:3])}]" if col.get("examples") else ""
                lines.append(f"  - {col['name']} ({col['type']}): {col['description']}{examples_str}")

        if context.join_paths:
            lines.append("\n=== APPROVED JOIN RELATIONSHIPS ===")
            for path in context.join_paths:
                lines.append(f"  - {path}")

        if context.relevant_metrics:
            lines.append("\n=== RELEVANT BUSINESS METRICS ===")
            for metric in context.relevant_metrics:
                lines.append(f"  - {metric['name']}: {metric['description']} (Formula: {metric['formula']})")

        return "\n".join(lines)

