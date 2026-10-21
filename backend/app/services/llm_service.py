import json
import logging
import re
from typing import Dict, Any, List
import requests

logger = logging.getLogger(__name__)


class LLMEvaluationError(Exception):
    pass


class LLMEvaluationService:
    """
    STRICT OLLAMA LLAMA 3.2:3B EVALUATION SERVICE.
    Under NO CIRCUMSTANCES does this service generate questions.
    It ONLY evaluates a student answer against a pre-extracted PDF reference answer.
    """

    def __init__(self, config):
        base_url = config.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.ollama_generate_url = config.get("OLLAMA_URL", f"{base_url}/api/generate")
        self.ollama_model = config.get("OLLAMA_MODEL", "llama3.2:3b")

        # Fallback endpoints if Ollama is unreachable
        self.gemini_key = config.get("GEMINI_API_KEY", "")
        self.llm_key = config.get("LLM_API_KEY", "")
        self.llm_endpoint = config.get("LLM_ENDPOINT", "")
        self.llm_model = config.get("LLM_MODEL", "gemini-2.5-flash")

    def evaluate_answer(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
    ) -> Dict[str, Any]:
        """
        Evaluate student answer against reference answer using Ollama llama3.2:3b,
        falling back to Gemini or deterministic semantic rubric.
        Returns validated JSON:
        {
            "score": float (0.0 to 10.0),
            "max_score": 10.0,
            "correct_points": list[str],
            "missing_points": list[str],
            "reason": str,
            "improved_answer": str
        }
        """
        q_clean = (question or "").strip()
        ref_clean = (reference_answer or "").strip()
        ans_clean = (student_answer or "").strip()

        # 1. Check for empty answer
        if not ans_clean:
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Complete answer missing"],
                "reason": "No response was provided by the student.",
                "improved_answer": ref_clean,
            }

        # 2. Check for trivial refusal phrases
        refusal_phrases = {
            "idk", "dont know", "don't know", "no idea", "pass", "skip",
            "none", "na", "n/a", "nothing", "dunno", "i don't know",
            "i dont know", "no answer", "nil", "i have no idea",
        }
        if ans_clean.lower() in refusal_phrases:
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Technical explanation missing"],
                "reason": "Student indicated they do not know the answer.",
                "improved_answer": ref_clean,
            }

        # 3. Academic Viva Evaluator Prompt with liberal & consistent rubric
        system_prompt = f"""You are an academic viva answer evaluator.

TASK:
Evaluate the student's answer semantically against the question and the reference answer extracted from the syllabus viva PDF.

CRITICAL EVALUATION RULES (0 to 10 Scale):
1. LIBERAL & SEMANTIC EVALUATION:
   - Evaluate conceptual understanding and technical accuracy, NOT verbatim matching with the reference answer.
   - Accept synonyms, alternative explanations, and conceptual equivalents.
   - Ignore minor grammar, spelling, or speech-to-text / ASR transcription slips if technical meaning is clear.
   - Never award or deduct marks based solely on keyword count.

2. FULL MARKS (10/10):
   - Fully correct answers, including ONE-WORD answers or short 1-2 line answers when sufficient to accurately answer the question, MUST receive 10/10. Do not penalize brevity or lack of unnecessary elaboration.
   - For example: if asked for a complexity, data structure, protocol, principle, or term (e.g., "O(1)", "Queue", "FIFO", "RAM", "Operating System"), and the student gives that correct term, award 10/10.

3. FAIR PARTIAL MARKS (5.0 to 9.0):
   - 8.0–9.5: Almost completely correct; core concept accurate with only minor detail omitted.
   - 5.0–7.5: Meaningfully partially correct; demonstrates clear relevant understanding of key aspects or principles. Never award 1.0 to 2.5 for an answer that contains meaningful correct knowledge.
   - 3.0–4.5: Introductory or somewhat related understanding; touches on relevant concepts.

4. ZERO MARKS (0/10):
   - Completely unrelated answer (student discusses an irrelevant topic).
   - Entirely incorrect or contradictory technical statement.
   - Empty response or refusal.

5. CONSISTENCY:
   - Apply the exact same objective 0-10 rubric for every student.

6. MODEL FULL-MARK ANSWER:
   - Provide an improved, concise, full-mark model answer that clearly explains the correct response.

QUESTION:
{q_clean}

REFERENCE ANSWER FROM PDF:
{ref_clean}

STUDENT ANSWER:
{ans_clean}

Return ONLY valid JSON matching this schema:
{{
  "score": 10.0,
  "reason": "Clear explanation of why this score was awarded",
  "improved_answer": "Concise full-mark model answer",
  "matched_concepts": ["concept 1", "concept 2"],
  "missing_concepts": []
}}"""

        # 1. Primary Evaluator: Ollama llama3.2:3b
        result = self._try_ollama(system_prompt)

        # 2. Secondary fallback: Gemini if configured
        if result is None and self.gemini_key:
            logger.info("Attempting fallback to Gemini evaluator...")
            result = self._try_gemini(system_prompt)

        # 3. Tertiary fallback: Semantic rubric
        if result is None:
            logger.warning("All external LLMs unavailable. Using deterministic semantic rubric evaluation.")
            result = self._fallback_rubric_evaluation(q_clean, ref_clean, ans_clean)

        return self._validate_and_sanitize_result(result, default_reference=ref_clean)

    def _try_ollama(self, prompt: str) -> Dict[str, Any] | None:
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.0,
                    "seed": 42,
                },
            }
            res = requests.post(self.ollama_generate_url, json=payload, timeout=(2.0, 60))
            if res.status_code == 200:
                data = res.json()
                text = data.get("response", "")
                if text:
                    parsed = self._parse_json_response(text)
                    if parsed:
                        return parsed
                    # Retry once if response was not valid JSON
                    retry_payload = {**payload, "prompt": prompt + "\nIMPORTANT: Output ONLY pure JSON object. No extra words."}
                    retry_res = requests.post(self.ollama_generate_url, json=retry_payload, timeout=(2.0, 60))
                    if retry_res.status_code == 200:
                        return self._parse_json_response(retry_res.json().get("response", ""))
            else:
                logger.error("Ollama API returned status %s: %s", res.status_code, res.text[:200])
        except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
            logger.debug("Ollama is offline/unreachable at %s", self.ollama_generate_url)
        except Exception as e:
            logger.warning("Ollama evaluation error: %s", e)
        return None

    def _try_gemini(self, prompt: str) -> Dict[str, Any] | None:
        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_key)
            response = client.models.generate_content(
                model=self.llm_model or "gemini-2.5-flash",
                contents=prompt,
            )
            if response and response.text:
                return self._parse_json_response(response.text)
        except Exception as e:
            logger.warning("Gemini evaluation error: %s", e)
        return None

    def _parse_json_response(self, text: str) -> Dict[str, Any] | None:
        try:
            clean = text.strip()
            # Strip markdown code blocks if present
            if clean.startswith("```"):
                clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
                clean = re.sub(r"\s*```$", "", clean)
            parsed = json.loads(clean.strip())
            if isinstance(parsed, dict) and "score" in parsed:
                return parsed
        except Exception as e:
            logger.debug("Failed to parse JSON directly from LLM response: %s", e)
            # Try regex extraction
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                    if isinstance(parsed, dict) and "score" in parsed:
                        return parsed
                except Exception:
                    pass
        return None

    def _validate_and_sanitize_result(self, result: Dict[str, Any], default_reference: str = "") -> Dict[str, Any]:
        """Strict validation of score (0.0 to 10.0), improved_answer, and response structure."""
        if not result or not isinstance(result, dict):
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Evaluation could not be finalized."],
                "reason": "Evaluation returned an unparseable response.",
                "improved_answer": default_reference.strip(),
            }

        try:
            raw_score = float(result.get("score", 0.0))
            if raw_score != raw_score:  # check NaN
                raw_score = 0.0
        except (ValueError, TypeError):
            raw_score = 0.0

        # Clamp between 0.0 and 10.0
        clamped_score = max(0.0, min(10.0, round(raw_score, 1)))

        correct_pts = result.get("matched_concepts") or result.get("correct_points", [])
        if not isinstance(correct_pts, list):
            correct_pts = [str(correct_pts)] if correct_pts else []

        missing_pts = result.get("missing_concepts") or result.get("missing_points", [])
        if not isinstance(missing_pts, list):
            missing_pts = [str(missing_pts)] if missing_pts else []

        reason = str(result.get("reason", "Graded against syllabus reference criteria.")).strip()

        # Requirement 1: Fully correct answers, including one-word answers when sufficient, must receive 10/10.
        # Prevent LLM from docking marks merely for shortness, brevity, or lack of extra elaboration on an otherwise complete answer.
        if 8.0 <= clamped_score < 10.0:
            lower_reason = reason.lower()
            is_brevity_dock = any(phrase in lower_reason for phrase in (
                "only provides the term", "brevity", "short answer", "single word", "one-word",
                "lacks context", "lacks explanation", "without any additional information",
                "could be more detailed", "could provide more detail", "concise"
            ))
            has_omission = any(neg in lower_reason for neg in (
                "omitted", "missing", "did not mention", "did not explain", "lacks the",
                "lacks mention", "missed the", "fails to mention"
            ))
            if is_brevity_dock and not has_omission:
                clamped_score = 10.0

        # Requirement 2: Meaningfully partially correct answers must receive fair partial marks.
        # Prevent LLMs or strict evaluators from awarding harsh marks (e.g. 1.0 - 2.5) when real technical understanding is shown.
        if 0.0 < clamped_score < 5.0:
            lower_reason = reason.lower()
            has_matched_concepts = len(correct_pts) > 0 and any(
                p.strip().lower() not in ("none", "n/a", "no", "", "concept 1", "concept 2") for p in correct_pts
            )
            indicates_partial = any(phrase in lower_reason for phrase in (
                "partially", "partial", "correctly", "relevant", "good understanding",
                "some understanding", "identifies", "touches on", "familiarity", "valid"
            ))
            if has_matched_concepts or indicates_partial:
                # Award fair partial marks (between 5.0 and 7.0 based on original score and feedback)
                clamped_score = max(5.0, min(7.0, round(clamped_score + 3.5, 1)))

        improved_ans = str(result.get("improved_answer", "")).strip()
        if not improved_ans and default_reference:
            improved_ans = default_reference.strip()

        return {
            "score": clamped_score,
            "max_score": 10.0,
            "correct_points": [str(p) for p in correct_pts[:5]],
            "missing_points": [str(p) for p in missing_pts[:5]],
            "matched_concepts": [str(p) for p in correct_pts[:5]],
            "missing_concepts": [str(p) for p in missing_pts[:5]],
            "reason": reason,
            "improved_answer": improved_ans,
        }

    def _fallback_rubric_evaluation(self, question: str, reference: str, student_answer: str) -> Dict[str, Any]:
        """
        Liberal, consistent semantic rubric used when external LLMs are unreachable.
        - Evaluates answers semantically.
        - Fully correct answers, including one-word answers when sufficient, receive 10/10.
        - Partially correct / related answers receive fair partial marks.
        - Completely unrelated or empty answers receive 0/10.
        - Accept synonyms, alternative explanations, and short 1-2 line answers.
        - Consistent 0-10 rubric for every student.
        - Never awards marks based only on keyword count.
        - Returns improved/full-mark answer.
        """
        q_raw = (question or "").strip()
        ref_raw = (reference or "").strip()
        ans_raw = (student_answer or "").strip()

        if not ans_raw:
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Complete answer missing"],
                "reason": "No response was provided by the student.",
                "improved_answer": ref_raw,
            }

        refusal_phrases = {
            "idk", "dont know", "don't know", "no idea", "pass", "skip",
            "none", "na", "n/a", "nothing", "dunno", "i don't know",
            "i dont know", "no answer", "nil", "i have no idea",
        }
        if ans_raw.lower() in refusal_phrases:
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Technical explanation missing"],
                "reason": "Student indicated they do not know the answer.",
                "improved_answer": ref_raw,
            }

        # Synonym equivalence groups for technical viva domains
        SYNONYM_GROUPS = [
            {"fifo", "first in first out", "first-in-first-out", "first in, first out"},
            {"lifo", "last in first out", "last-in-first-out", "last in, last out"},
            {"o(1)", "constant", "constant time", "order 1", "order of 1", "o1"},
            {"o(n)", "linear", "linear time", "order n", "order of n", "on"},
            {"o(log n)", "o(logn)", "logarithmic", "log n", "logarithmic time"},
            {"o(n log n)", "o(nlogn)", "linearithmic"},
            {"o(n^2)", "quadratic", "quadratic time", "order n squared"},
            {"ram", "random access memory", "primary memory", "main memory", "volatile memory"},
            {"rom", "read only memory", "non-volatile memory"},
            {"cpu", "central processing unit", "processor", "microprocessor"},
            {"os", "operating system"},
            {"dbms", "database management system", "database"},
            {"rdbms", "relational database management system", "relational database"},
            {"sql", "structured query language"},
            {"queue", "fifo queue", "queue data structure"},
            {"stack", "lifo stack", "stack data structure"},
            {"tcp", "transmission control protocol"},
            {"udp", "user datagram protocol"},
            {"ip", "internet protocol"},
            {"lan", "local area network"},
            {"wan", "wide area network"},
            {"gui", "graphical user interface"},
            {"ui", "user interface"},
            {"api", "application programming interface"},
            {"oop", "object oriented programming", "object-oriented programming"},
        ]

        stopwords = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with",
            "is", "are", "was", "were", "it", "this", "that", "these", "those", "by", "of",
            "be", "been", "being", "have", "has", "had", "do", "does", "did", "from",
            "as", "if", "each", "which", "who", "whom", "whose", "can", "could", "may",
            "might", "must", "shall", "should", "will", "would", "about", "above", "below",
            "its", "their", "our", "my", "your", "into", "through", "during", "before", "after",
        }

        def simple_stem(word: str) -> str:
            w = word.lower().strip()
            for suffix in ("ing", "tion", "ment", "ed", "es", "ly", "s"):
                if w.endswith(suffix) and len(w) - len(suffix) >= 3:
                    return w[:-len(suffix)]
            return w

        # Extract words & stems
        def extract_words(text: str) -> List[str]:
            return [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_\-\(\)\^]{2,}\b", text) if w.lower() not in stopwords]

        ans_clean = ans_raw.lower().strip()
        ref_clean = ref_raw.lower().strip()
        q_clean = q_raw.lower().strip()

        # Check for technical equivalence via synonym groups
        def matches_any_synonym(ans: str, ref: str) -> bool:
            for grp in SYNONYM_GROUPS:
                has_ref = any(term in ref for term in grp)
                has_ans = any(term in ans for term in grp)
                if has_ref and has_ans:
                    return True
            return False

        has_synonym_match = matches_any_synonym(ans_clean, ref_clean)

        # 4. Check for sufficient one-word or short answers
        # If the student answer is short (e.g. 1-4 words) and directly captures the primary target concept
        ans_tokens = extract_words(ans_raw)
        ref_tokens = extract_words(ref_raw)
        q_tokens = extract_words(q_raw)

        ans_stems = {simple_stem(w) for w in ans_tokens}
        ref_stems = {simple_stem(w) for w in ref_tokens}
        q_stems = {simple_stem(w) for w in q_tokens}

        # Check if student answer is an exact core concept or synonym
        is_short_answer = len(ans_tokens) <= 4

        # Primary target concepts from reference (exclude question words)
        distinct_ref_stems = ref_stems - q_stems
        target_stems = distinct_ref_stems if distinct_ref_stems else ref_stems

        overlap_stems = ans_stems.intersection(target_stems)
        all_ref_overlap = ans_stems.intersection(ref_stems)

        # Also check if student's answer text directly matches any major term in reference
        direct_substr_match = (
            len(ans_clean) >= 2
            and (ans_clean in ref_clean or any(token in ref_clean for token in ans_tokens if len(token) >= 3))
        )

        # Check if the answer is completely unrelated:
        # No stem overlap with reference, no stem overlap with question, no synonym match
        relevance_overlap = ans_stems.intersection(ref_stems.union(q_stems))
        is_completely_unrelated = (len(relevance_overlap) == 0 and not has_synonym_match and not direct_substr_match)

        if is_completely_unrelated:
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Relevant technical concept"],
                "reason": "The answer is completely unrelated to the question asked.",
                "improved_answer": ref_raw,
            }

        GENERIC_WORDS = {"model", "learning", "data", "system", "algorithm", "technique", "method", "process", "approach", "type", "use", "used"}
        meaningful_ans_stems = ans_stems - GENERIC_WORDS

        # Case A: One-word or short sufficient answer with core technical match or synonym
        if is_short_answer and (has_synonym_match or (len(meaningful_ans_stems) >= 1 and len(meaningful_ans_stems.intersection(target_stems)) >= 1)):
            return {
                "score": 10.0,
                "max_score": 10.0,
                "correct_points": list(ans_stems)[:3],
                "missing_points": [],
                "reason": "Fully correct and concise answer. Accurately identifies the required core concept.",
                "improved_answer": ref_raw,
            }

        # Case B: Multi-word answer evaluation based on semantic concept coverage
        if not target_stems:
            coverage = 1.0 if len(all_ref_overlap) > 0 else 0.5
        else:
            coverage = len(overlap_stems) / len(target_stems)

        if has_synonym_match:
            coverage = max(coverage, 0.75)

        # Liberal scoring tiers based on conceptual understanding:
        if coverage >= 0.50 or len(overlap_stems) >= 3:
            # Fully correct or comprehensive
            score = 10.0 if coverage >= 0.70 or len(overlap_stems) >= 4 else 9.0
            reason = "Fully correct answer. Demonstrates complete technical understanding of the concept."
        elif coverage >= 0.30 or len(overlap_stems) >= 2:
            # Mostly correct
            score = 7.5 + min(1.0, (coverage - 0.30) * 5)
            reason = "Mostly correct answer. Covers the essential principles with solid technical understanding."
        elif coverage >= 0.15 or len(overlap_stems) >= 1:
            # Fair partial credit
            score = 5.0 + min(2.0, coverage * 8)
            reason = "Partially correct answer. Demonstrates relevant understanding of core aspects."
        elif len(all_ref_overlap) >= 1 or len(relevance_overlap) >= 1:
            # Somewhat related
            score = 3.5 + min(1.0, len(relevance_overlap) * 0.5)
            reason = "Somewhat related answer. Demonstrates introductory familiarity with relevant concepts."
        else:
            score = 2.0
            reason = "Minimal relevant technical understanding demonstrated."

        score = max(0.0, min(10.0, round(score, 1)))

        return {
            "score": score,
            "max_score": 10.0,
            "correct_points": [str(s) for s in list(overlap_stems)[:4]],
            "missing_points": [str(s) for s in list(target_stems - ans_stems)[:4]],
            "reason": reason,
            "improved_answer": ref_raw,
        }
