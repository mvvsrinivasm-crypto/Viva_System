import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from app.services.llm_service import LLMEvaluationService


def test_liberal_evaluation_rubric():
    svc = LLMEvaluationService({})

    # 1. One-word answer
    q1 = "Which data structure follows the First-In-First-Out (FIFO) principle?"
    ref1 = "A Queue operates on the First-In-First-Out (FIFO) principle where elements are enqueued at rear and dequeued from front."
    res1 = svc.evaluate_answer(q1, ref1, "Queue")
    assert res1["score"] == 10.0
    assert "improved_answer" in res1 and len(res1["improved_answer"]) > 0

    # 2. One-word complexity
    q2 = "What is the average time complexity of hash table lookup?"
    ref2 = "The average time complexity of hash table search is O(1) or constant time."
    res2 = svc.evaluate_answer(q2, ref2, "O(1)")
    assert res2["score"] == 10.0
    assert "improved_answer" in res2 and len(res2["improved_answer"]) > 0

    # 3. Full conceptual answer
    q3 = "Explain the role of the integral component in a PID controller."
    ref3 = "The integral component accumulates error over time to eliminate steady-state error completely in control loops."
    full_ans = "The integral component accumulates error over time to eliminate steady-state error completely in control loops."
    res3 = svc.evaluate_answer(q3, ref3, full_ans)
    assert res3["score"] == 10.0
    assert "improved_answer" in res3 and len(res3["improved_answer"]) > 0

    # 4. Partial answer
    res4 = svc.evaluate_answer(q3, ref3, "It eliminates steady state error in the system.")
    assert 5.0 <= res4["score"] < 10.0
    assert "improved_answer" in res4 and len(res4["improved_answer"]) > 0

    # 5. Completely unrelated answer
    res5 = svc.evaluate_answer(q3, ref3, "Photosynthesis produces glucose and oxygen from carbon dioxide.")
    assert res5["score"] == 0.0
    assert "improved_answer" in res5 and len(res5["improved_answer"]) > 0

    # 6. Refusal / Empty
    res6 = svc.evaluate_answer(q3, ref3, "I do not know")
    assert res6["score"] == 0.0

    res_empty = svc.evaluate_answer(q3, ref3, "")
    assert res_empty["score"] == 0.0

    # 7. Identical answers consistency (consistent scoring rubric)
    res7a = svc.evaluate_answer(q3, ref3, "Accumulates past error")
    res7b = svc.evaluate_answer(q3, ref3, "Accumulates past error")
    assert res7a["score"] == res7b["score"]
    assert len(res7a["reason"]) > 0 and len(res7b["reason"]) > 0
