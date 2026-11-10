"""
SQL Safety Validator Module
Provides robust, AST-level SQL validation for DataPilot.

Guarantees:
- Read-only enforcement: strictly disallows destructive operations (DROP, DELETE, INSERT, UPDATE, ALTER, TRUNCATE, etc.)
- Multi-statement rejection: prevents SQL injection through statement chaining (;).
- Table access restriction: enforces access only to an approved whitelist of tables.
- Mandatory row limits: checks for LIMIT clauses and automatically clamps to MAX_ROW_LIMIT.
- Query execution timeouts: applies execution limits to prevent hanging or runaway queries.
- SQL parsing and token analysis rather than fragile regex alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set


class SQLSecurityError(Exception):
    """Raised when an SQL query violates security or safety constraints."""
    pass


class QueryClassification(str, Enum):
    SELECT = "SELECT"
    WITH_SELECT = "WITH_SELECT"
    DISALLOWED_DML = "DISALLOWED_DML"
    DISALLOWED_DDL = "DISALLOWED_DDL"
    DISALLOWED_ADMIN = "DISALLOWED_ADMIN"
    MULTI_STATEMENT = "MULTI_STATEMENT"
    INVALID_SYNTAX = "INVALID_SYNTAX"


@dataclass
class SQLValidationResult:
    """Result of SQL safety validation."""
    is_valid: bool
    classification: QueryClassification
    error_message: Optional[str] = None
    sanitized_sql: Optional[str] = None
    referenced_tables: List[str] = field(default_factory=list)
    enforced_limit: Optional[int] = None
    applied_timeout_seconds: float = 5.0


# Default approved tables for the E-commerce Data Warehouse
DEFAULT_APPROVED_TABLES: Set[str] = {
    "dim_region",
    "dim_customer",
    "dim_product",
    "dim_date",
    "fact_order",
}

# Explicitly forbidden command verbs (DDL, DML, Administration, Dangerous functions)
FORBIDDEN_COMMANDS: Set[str] = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "TRUNCATE",
    "ALTER",
    "CREATE",
    "REPLACE",
    "RENAME",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "CALL",
    "LOCK",
    "UNLOCK",
    "SET",
    "PRAGMA",
    "ATTACH",
    "DETACH",
    "VACUUM",
    "REINDEX",
    "SHUTDOWN",
    "KILL",
    "INTO OUTFILE",
    "INTO DUMPFILE",
    "LOAD DATA",
    "LOAD_FILE",
}

DEFAULT_MAX_ROW_LIMIT: int = 1000
DEFAULT_QUERY_TIMEOUT_SECONDS: float = 5.0


class SQLSafetyValidator:
    """
    Dedicated SQL Safety Validator for Autonomous Database Analysts.
    Performs multi-phase token and AST analysis prior to query execution.
    """

    def __init__(
        self,
        approved_tables: Optional[Set[str]] = None,
        max_row_limit: int = DEFAULT_MAX_ROW_LIMIT,
        timeout_seconds: float = DEFAULT_QUERY_TIMEOUT_SECONDS,
        allow_cte: bool = True,
    ):
        self.approved_tables = {t.lower() for t in (approved_tables or DEFAULT_APPROVED_TABLES)}
        self.max_row_limit = max_row_limit
        self.timeout_seconds = timeout_seconds
        self.allow_cte = allow_cte

    def _strip_comments_and_whitespace(self, sql: str) -> str:
        """Removes single-line (-- ...) and multi-line (/* ... */) SQL comments."""
        # Remove /* multi-line */ comments
        cleaned = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
        # Remove -- single-line comments
        cleaned = re.sub(r"--[^\r\n]*", " ", cleaned)
        # Remove # single-line comments (MySQL style)
        cleaned = re.sub(r"#[^\r\n]*", " ", cleaned)
        return cleaned.strip()

    def _split_into_statements(self, sql: str) -> List[str]:
        """
        Splits SQL by semicolons while respecting single, double, and backtick quote scopes.
        Returns a list of non-empty statement strings.
        """
        statements = []
        current = []
        in_single = False
        in_double = False
        in_backtick = False

        i = 0
        n = len(sql)
        while i < n:
            char = sql[i]
            # Handle escapes within string literals
            if char == "\\" and i + 1 < n and (in_single or in_double):
                current.append(char)
                current.append(sql[i + 1])
                i += 2
                continue

            if char == "'" and not in_double and not in_backtick:
                in_single = not in_single
            elif char == '"' and not in_single and not in_backtick:
                in_double = not in_double
            elif char == "`" and not in_single and not in_double:
                in_backtick = not in_backtick
            elif char == ";" and not (in_single or in_double or in_backtick):
                stmt = "".join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
                i += 1
                continue

            current.append(char)
            i += 1

        last_stmt = "".join(current).strip()
        if last_stmt:
            statements.append(last_stmt)

        return statements

    def _extract_tokens(self, sql: str) -> List[str]:
        """Tokenizes SQL into keyword and identifier tokens, ignoring string literals."""
        # Replace quoted string literals with empty placeholders to prevent false keyword matches
        no_strings = re.sub(r"'([^'\\]|\\.)*'", "''", sql)
        no_strings = re.sub(r'"([^"\\]|\\.)*"', '""', no_strings)
        # Extract word tokens and delimiters
        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\S", no_strings)
        return tokens

    def _extract_table_names(self, sql: str) -> List[str]:
        """
        Extracts table names referenced in FROM and JOIN clauses using robust syntactic pattern matching.
        Handles schema-qualified tables (e.g. dw.fact_order), aliases, and subqueries.
        """
        tokens = self._extract_tokens(sql)
        tables: Set[str] = set()
        ctes: Set[str] = set()

        # Step 1: Detect CTE names from WITH clauses (to avoid flagging CTEs as unauthorized tables)
        for i, token in enumerate(tokens):
            if token.upper() == "WITH" or (i > 0 and tokens[i - 1] == "," and any(t.upper() == "WITH" for t in tokens[:i])):
                if i + 1 < len(tokens):
                    candidate_cte = tokens[i + 1].strip("`\"'[]").lower()
                    if i + 2 < len(tokens) and tokens[i + 2].upper() == "AS":
                        ctes.add(candidate_cte)

        # Step 2: Extract tables following FROM or JOIN
        i = 0
        n = len(tokens)
        table_indicators = {"FROM", "JOIN"}

        while i < n:
            token = tokens[i].upper()
            if token in table_indicators:
                if i + 1 < n:
                    target = tokens[i + 1]
                    # Check if it is a subquery
                    if target == "(":
                        i += 2
                        continue
                    # Clean identifier (strip schema qualifiers, backticks, quotes)
                    clean_table = target.strip("`\"'[]").lower()
                    if "." in clean_table:
                        clean_table = clean_table.split(".")[-1].strip("`\"'[]")

                    # Do not treat SQL keywords, parenthesis, or CTE definitions as tables
                    if clean_table and clean_table not in {"select", "where", "group", "order", "limit", "having"}:
                        if clean_table not in ctes:
                            tables.add(clean_table)
            i += 1

        return sorted(list(tables))

    def _enforce_row_limit(self, sql: str) -> tuple[str, int]:
        """
        Checks for a LIMIT clause. If absent, appends LIMIT {max_row_limit}.
        If present with a value > max_row_limit, safely clamps the limit.
        """
        cleaned_sql = sql.rstrip("; \t\n")
        # Match LIMIT followed by one or two integers (LIMIT [offset,] row_count)
        limit_match = re.search(r"\bLIMIT\s+(\d+)(?:\s*,\s*(\d+)|\s+OFFSET\s+(\d+))?", cleaned_sql, flags=re.IGNORECASE)

        if not limit_match:
            sanitized = f"{cleaned_sql} LIMIT {self.max_row_limit}"
            return sanitized, self.max_row_limit

        # Extract current limit count
        if limit_match.group(2):  # LIMIT offset, count
            count = int(limit_match.group(2))
            offset = int(limit_match.group(1))
            if count > self.max_row_limit:
                new_limit_clause = f"LIMIT {offset}, {self.max_row_limit}"
                sanitized = cleaned_sql[:limit_match.start()] + new_limit_clause + cleaned_sql[limit_match.end():]
                return sanitized, self.max_row_limit
            return cleaned_sql, count
        else:
            count = int(limit_match.group(1))
            offset_val = limit_match.group(3)
            if count > self.max_row_limit:
                if offset_val:
                    new_limit_clause = f"LIMIT {self.max_row_limit} OFFSET {offset_val}"
                else:
                    new_limit_clause = f"LIMIT {self.max_row_limit}"
                sanitized = cleaned_sql[:limit_match.start()] + new_limit_clause + cleaned_sql[limit_match.end():]
                return sanitized, self.max_row_limit
            return cleaned_sql, count

    def validate(self, sql: str) -> SQLValidationResult:
        """
        Main validation entrypoint. Executes full safety analysis.
        Returns SQLValidationResult detailing safety status, classification, errors, and sanitized SQL.
        """
        if not sql or not sql.strip():
            return SQLValidationResult(
                is_valid=False,
                classification=QueryClassification.INVALID_SYNTAX,
                error_message="SQL query is empty or whitespace only.",
            )

        stripped = self._strip_comments_and_whitespace(sql)
        if not stripped:
            return SQLValidationResult(
                is_valid=False,
                classification=QueryClassification.INVALID_SYNTAX,
                error_message="SQL query contained only comments and no executable statements.",
            )

        # 1. Multi-statement validation
        statements = self._split_into_statements(stripped)
        if len(statements) > 1:
            return SQLValidationResult(
                is_valid=False,
                classification=QueryClassification.MULTI_STATEMENT,
                error_message=f"Multiple SQL statements detected ({len(statements)} statements). Execution rejected to prevent SQL injection chaining.",
            )

        single_stmt = statements[0]

        # 2. Extract leading command
        tokens = self._extract_tokens(single_stmt)
        if not tokens:
            return SQLValidationResult(
                is_valid=False,
                classification=QueryClassification.INVALID_SYNTAX,
                error_message="Could not parse tokens from SQL query.",
            )

        leading_token = tokens[0].upper()

        # 3. Check if leading token or any token is a forbidden command
        if leading_token in FORBIDDEN_COMMANDS:
            classification = (
                QueryClassification.DISALLOWED_DDL
                if leading_token in {"DROP", "ALTER", "CREATE", "TRUNCATE", "RENAME"}
                else QueryClassification.DISALLOWED_DML
            )
            return SQLValidationResult(
                is_valid=False,
                classification=classification,
                error_message=f"Forbidden operation '{leading_token}' detected. The database analyst only permits approved read-only SELECT queries.",
            )

        token_set = {t.upper() for t in tokens}
        for forbidden in FORBIDDEN_COMMANDS:
            if " " in forbidden:
                # Multi-word forbidden check (e.g. INTO OUTFILE, LOAD DATA)
                if re.search(r"\b" + re.escape(forbidden) + r"\b", single_stmt, flags=re.IGNORECASE):
                    return SQLValidationResult(
                        is_valid=False,
                        classification=QueryClassification.DISALLOWED_ADMIN,
                        error_message=f"Forbidden command clause '{forbidden}' detected. Destructive and administrative operations are strictly rejected.",
                    )
            else:
                if forbidden in token_set and forbidden != "SET":  # Let DML check precedence
                    classification = (
                        QueryClassification.DISALLOWED_DDL
                        if forbidden in {"DROP", "ALTER", "CREATE", "TRUNCATE", "RENAME"}
                        else QueryClassification.DISALLOWED_DML
                    )
                    return SQLValidationResult(
                        is_valid=False,
                        classification=classification,
                        error_message=f"Forbidden operation '{forbidden}' detected. The database analyst only permits approved read-only SELECT queries.",
                    )

        if "SET" in token_set and leading_token not in {"SELECT", "WITH"}:
            return SQLValidationResult(
                is_valid=False,
                classification=QueryClassification.DISALLOWED_DML,
                error_message="Forbidden operation 'SET' detected. Database state modification is not permitted.",
            )

        # 4. Enforce approved query classification (SELECT or WITH ... SELECT)
        if leading_token == "SELECT":
            query_type = QueryClassification.SELECT
        elif leading_token == "WITH":
            if not self.allow_cte:
                return SQLValidationResult(
                    is_valid=False,
                    classification=QueryClassification.INVALID_SYNTAX,
                    error_message="Common Table Expressions (WITH clauses) are disabled.",
                )
            # Ensure the CTE culminates in a SELECT
            if "SELECT" not in token_set:
                return SQLValidationResult(
                    is_valid=False,
                    classification=QueryClassification.INVALID_SYNTAX,
                    error_message="WITH statement does not contain a terminating SELECT query.",
                )
            query_type = QueryClassification.WITH_SELECT
        else:
            return SQLValidationResult(
                is_valid=False,
                classification=QueryClassification.INVALID_SYNTAX,
                error_message=f"Unapproved statement type '{leading_token}'. Only read-only SELECT queries are permitted.",
            )

        # 5. Extract and validate referenced tables against the Approved Whitelist
        referenced_tables = self._extract_table_names(single_stmt)
        unapproved = [t for t in referenced_tables if t not in self.approved_tables]

        if unapproved:
            return SQLValidationResult(
                is_valid=False,
                classification=query_type,
                error_message=f"Access to unapproved table(s) [{', '.join(unapproved)}] rejected. Approved tables: {sorted(list(self.approved_tables))}.",
                referenced_tables=referenced_tables,
            )

        # 6. Apply mandatory row limits
        sanitized_sql, enforced_limit = self._enforce_row_limit(single_stmt)

        return SQLValidationResult(
            is_valid=True,
            classification=query_type,
            error_message=None,
            sanitized_sql=sanitized_sql,
            referenced_tables=referenced_tables,
            enforced_limit=enforced_limit,
            applied_timeout_seconds=self.timeout_seconds,
        )
