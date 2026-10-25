#!/usr/bin/env python3
"""
Touchstone Fact Checker CLI
Verify any factual claim against the corpus using hybrid retrieval, 
local LLM reasoning, and DeBERTa cross-encoder guardrail arbitration.
"""

import sys
import argparse
from loader import load_passages
from retriever import Retriever
from verdict import judge
from guardrails import GuardrailEngine


def format_report(claim: str, result: dict) -> str:
    verdict = result.get("verdict", "UNKNOWN")
    status = result.get("guardrail_status", "N/A")
    rationale = result.get("rationale", "")
    cited_ids = result.get("evidence_ids", [])
    
    nli = result.get("nli_details", {}) or {}
    be = nli.get("best_entailment", {}) or {}
    bc = nli.get("best_contradiction", {}) or {}
    e_score = be.get("score") if isinstance(be, dict) else be
    c_score = bc.get("score") if isinstance(bc, dict) else bc
    
    lines = [
        "",
        "=" * 68,
        f" CLAIM: {claim}",
        "=" * 68,
        f" VERDICT          : {verdict}",
        f" ARBITRATION      : {status}",
    ]
    
    if e_score is not None and c_score is not None:
        lines.append(f" NLI CONFIDENCE   : Entailment = {e_score:.3f} | Contradiction = {c_score:.3f}")
        
    if cited_ids:
        lines.append(f" CITED PASSAGES   : {', '.join(cited_ids)}")
    else:
        lines.append(" CITED PASSAGES   : None (insufficient evidence in context)")
        
    lines.extend([
        "-" * 68,
        " RATIONALE:",
        f" {rationale}",
        "=" * 68,
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Touchstone Fact-Checking Engine")
    parser.add_argument("claim", nargs="?", default=None, help="The factual claim to verify")
    parser.add_argument("--corpus", default="corpus/fever.txt", help="Path to evidence corpus (default: corpus/fever.txt)")
    parser.add_argument("--trial", action="store_true", help="Use small test corpus")
    parser.add_argument("-k", type=int, default=5, help="Number of evidence passages to retrieve (default: 5)")
    parser.add_argument("--no-guard", action="store_true", help="Disable NLI guardrail engine")
    parser.add_argument("--interactive", "-i", action="store_true", help="Start interactive verification REPL")

    args = parser.parse_args()

    corpus_path = "corpus/test.txt" if args.trial else args.corpus
    print(f"Loading corpus from {corpus_path}...")
    passages = load_passages(corpus_path)
    retriever = Retriever(passages, mode="hybrid")

    guardrail_engine = None
    if not args.no_guard:
        print("Initializing DeBERTa-v3 Guardrail Engine...")
        guardrail_engine = GuardrailEngine()

    def verify_one(text: str):
        evidence = retriever.search(text, k=args.k)
        result = judge(text, evidence, guardrail_engine=guardrail_engine)
        print(format_report(text, result))

    if args.interactive:
        print("\nTouchstone Interactive Fact Checker (type 'exit' or Ctrl-C to quit)\n")
        while True:
            try:
                query = input("Claim > ").strip()
                if not query:
                    continue
                if query.lower() in ("exit", "quit", "q"):
                    break
                verify_one(query)
            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")
                break
    elif args.claim:
        verify_one(args.claim)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
