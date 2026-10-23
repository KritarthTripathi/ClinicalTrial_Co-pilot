import argparse
import json
import uuid

from .graph import build_graph
from app.common.tracing import init_tracing
from app.common.vault import PIIVault


def main() -> None:
    ap = argparse.ArgumentParser(description="Local clinical/sales multi-agent pipeline")
    ap.add_argument("input", help="protocol (.pdf/.txt/.md) or sales (.csv)")
    ap.add_argument("--question", help="sales analytics question")
    ap.add_argument("--no-trace", action="store_true")
    ap.add_argument("--reidentify", action="store_true", help="restore original values in output (local only)")
    args = ap.parse_args()

    if not args.no_trace:
        init_tracing()
    app = build_graph()
    state = app.invoke({"input_path": args.input, "question": args.question},
                       config={"configurable": {"thread_id": uuid.uuid4().hex}})

    out = {k: state.get(k) for k in ("doc_type", "compliance", "validation", "result")}
    text = json.dumps(out, indent=2, default=str)
    if args.reidentify and state.get("session_id"):
        text = PIIVault().reidentify(state["session_id"], text)
    print(text)


if __name__ == "__main__":
    main()
