from typing import TypedDict


class SalesState(TypedDict, total=False):
    question: str
    skip_narrate: bool
    views: list
    data_end: str
    sql_raw: str
    sql: str
    columns: list
    rows: list
    table: str
    answer: str
    error: str
    attempts: int
