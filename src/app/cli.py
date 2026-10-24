import argparse
import uuid

from app.common.tracing import init_tracing
from app.common.vault import PIIVault
from app.sales.graph import build_graph


def main():
    ap = argparse.ArgumentParser(description="Local pharma sales analytics agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sales", help="ask a question about the sales data")
    s.add_argument("question")
    s.add_argument("--masked", action="store_true", help="show placeholders instead of real names")
    s.add_argument("--no-trace", action="store_true")
    args = ap.parse_args()
    if not args.no_trace:
        init_tracing()
    st = build_graph().invoke({"question": args.question, "attempts": 0},
                              config={"configurable": {"thread_id": uuid.uuid4().hex}})
    if st.get("error"):
        print(f"Could not answer after {st.get('attempts')} attempts: {st['error']}\nLast SQL: {st.get('sql_raw')}")
        return
    out = f"{st['answer']}\n\n{st['table']}"
    if not args.masked:                      # re-identification happens here, outside the traced graph
        out = PIIVault().reidentify("pharma", out)
    print(out + f"\n\nSQL: {st['sql']}\n(attempts: {st['attempts']})")


if __name__ == "__main__":
    main()
