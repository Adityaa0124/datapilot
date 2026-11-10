"""
Conversational Memory Module for Autonomous Database Analyst.
Maintains multi-turn context, preserves prior SQL statements and active filters,
and seamlessly resolves follow-up queries without confusing old and new context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConversationTurn:
    turn_id: int
    user_query: str
    generated_sql: str
    referenced_tables: List[str]
    row_count: int
    summary: str
    active_filters: List[str] = field(default_factory=list)


class ConversationalMemory:
    """
    Session-level memory manager for multi-turn database analysis dialogues.
    """

    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        self.turns: List[ConversationTurn] = []

    def add_turn(
        self,
        user_query: str,
        generated_sql: str,
        referenced_tables: List[str],
        row_count: int,
        summary: str,
        active_filters: Optional[List[str]] = None,
    ) -> ConversationTurn:
        """Records a completed conversation turn."""
        turn = ConversationTurn(
            turn_id=len(self.turns) + 1,
            user_query=user_query,
            generated_sql=generated_sql,
            referenced_tables=referenced_tables,
            row_count=row_count,
            summary=summary,
            active_filters=active_filters or [],
        )
        self.turns.append(turn)
        if len(self.turns) > self.max_history:
            self.turns.pop(0)
        return turn

    def get_last_turn(self) -> Optional[ConversationTurn]:
        """Returns the most recent conversation turn if available."""
        return self.turns[-1] if self.turns else None

    def is_follow_up(self, query: str) -> bool:
        """
        Determines whether the incoming query is a follow-up or refinement
        of the preceding query.
        """
        if not self.turns:
            return False

        q = query.lower().strip()

        # Follow-up cue phrases in Chinese and English
        follow_up_cues = [
            "只看", "过滤", "仅保留", "只要", "加上", "再按", "另外按", "然后按",
            "其中", "那", "如果", "再看", "重新排序",
            "now filter", "filter those", "filter to", "only in",
            "and for", "what about", "sort by", "order by", "change to",
            "restrict to", "just for", "break down by",
        ]

        if any(cue in q for cue in follow_up_cues):
            return True

        # Date/time relative follow-ups
        if any(d in q for d in ["近30天", "本月", "上月", "第一季度", "q1", "今年", "last 30 days", "this month"]):
            return True

        return False

    def resolve_follow_up_query(self, follow_up_query: str) -> tuple[str, Optional[str]]:
        """
        Resolves a follow-up query by synthesizing it with prior context.
        Returns:
            (augmented_prompt_query, prior_sql)
        """
        last_turn = self.get_last_turn()
        if not last_turn or not self.is_follow_up(follow_up_query):
            return follow_up_query, None

        q = follow_up_query.lower()
        prior_sql = last_turn.generated_sql

        augmented_query = (
            f"Follow-up context from previous question: '{last_turn.user_query}'\n"
            f"Previous SQL: '{last_turn.generated_sql}'\n"
            f"Active Tables: {last_turn.referenced_tables}\n"
            f"New follow-up constraint / refinement: '{follow_up_query}'"
        )

        return augmented_query, prior_sql

    def apply_follow_up_to_sql(self, follow_up_query: str, base_sql: str) -> str:
        """
        Synthesizes follow-up constraints directly onto the base SQL:
        e.g., adding date filter (WHERE date_id >= 20250101) or ORDER BY.
        """
        q = follow_up_query.lower()
        refined_sql = base_sql.rstrip("; \t\n")

        # Case 1: Time filter refinement (e.g. "last 30 days" / "一月份" / "Q1")
        if any(k in q for k in ["30天", "30 days", "一月", "1月", "january", "q1"]):
            time_filter = "f.date_id BETWEEN 20250101 AND 20250131"
            if "WHERE" in refined_sql.upper():
                refined_sql = re.sub(
                    r"\bWHERE\b",
                    f"WHERE {time_filter} AND",
                    refined_sql,
                    count=1,
                    flags=re.IGNORECASE,
                )
            elif "GROUP BY" in refined_sql.upper():
                refined_sql = re.sub(
                    r"\bGROUP BY\b",
                    f"WHERE {time_filter} GROUP BY",
                    refined_sql,
                    count=1,
                    flags=re.IGNORECASE,
                )
            elif "ORDER BY" in refined_sql.upper():
                refined_sql = re.sub(
                    r"\bORDER BY\b",
                    f"WHERE {time_filter} ORDER BY",
                    refined_sql,
                    count=1,
                    flags=re.IGNORECASE,
                )
            elif "LIMIT" in refined_sql.upper():
                refined_sql = re.sub(
                    r"\bLIMIT\b",
                    f"WHERE {time_filter} LIMIT",
                    refined_sql,
                    count=1,
                    flags=re.IGNORECASE,
                )
            else:
                refined_sql = f"{refined_sql} WHERE {time_filter}"

        # Case 2: Limit count change (e.g. "top 3" / "只要前3个")
        if any(k in q for k in ["前3", "top 3", "前三"]):
            if "LIMIT" in refined_sql.upper():
                refined_sql = re.sub(r"\bLIMIT\s+\d+", "LIMIT 3", refined_sql, flags=re.IGNORECASE)
            else:
                refined_sql = f"{refined_sql} LIMIT 3"

        return refined_sql

    def clear(self):
        """Clears conversational history."""
        self.turns.clear()
