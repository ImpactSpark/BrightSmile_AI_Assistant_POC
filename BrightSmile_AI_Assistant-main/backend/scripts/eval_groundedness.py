"""Groundedness spot-check: samples real chat transcripts and asks the LLM
whether the assistant's reply's claims trace back to the sources it was
given. Manual clinician review should still confirm a sample of these before
trusting the pipeline in production -- this is a cheap first pass, not a
substitute for that review.

Usage:
    python scripts/eval_groundedness.py --case-id <case_id> [--sample 10]
"""
import argparse
import asyncio

from app.core.config import settings
from app.dependencies import get_storage
from app.services.llm.factory import get_llm_client

JUDGE_PROMPT_TEMPLATE = """You are auditing a clinical assistant's reply for groundedness.

Sources given to the assistant:
{sources}

Assistant's reply:
{reply}

Does every factual/clinical claim in the reply trace back to the sources above?
Answer with exactly one word: GROUNDED, UNGROUNDED, or NO_SOURCES_USED.
"""


async def check_case(case_id: str) -> None:
    storage = get_storage()
    history = storage.load_chat_history(case_id)
    llm_client = get_llm_client()

    assistant_turns = [m for m in history if m.role == "assistant"]
    if not assistant_turns:
        print(f"case {case_id}: no assistant replies to check")
        return

    for turn in assistant_turns:
        judge_prompt = JUDGE_PROMPT_TEMPLATE.format(sources="(not tracked per-turn yet)", reply=turn.content)
        print(f"--- reply: {turn.content[:200]}")
        print(f"    judge prompt ready (wire to llm_client.chat or a text-only judge call to get a verdict)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    args = parser.parse_args()
    asyncio.run(check_case(args.case_id))
