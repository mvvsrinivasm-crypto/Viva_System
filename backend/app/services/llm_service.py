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
        Evaluate student answer against reference answer using Ollama llama3.2:3b.
        Returns validated JSON:
        {
            "score": float (0.0 to 10.0),
            "max_score": 10.0,
            "correct_points": list[str],
            "missing_points": list[str],
            "reason": str
        }
        """
        q_clean = (question or "").strip()
        ref_clean = (reference_answer or "").strip()
        ans_clean = (student_answer or "").strip()

        # Check for empty answer or trivial refusal
        if not ans_clean or len(ans_clean) < 2:
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Complete answer missing"],
                "reason": "No response was provided by the student.",
            }

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
            }

        system_prompt = f"""You are an academic viva answer evaluator.

Evaluate the student's answer against the provided question and reference answer.

The reference answer was provided by the faculty through the official viva PDF.

Evaluate semantic meaning, not exact wording.

Equivalent answers must receive full marks.

A student may express the same concept using different words.

Award partial marks when the student demonstrates only part of the required concept.

Recognize relevant key concepts, but do not award marks merely because an isolated keyword appears.

Do not penalize grammar, spelling, or minor speech-transcription errors when the technical meaning is correct.

Do not invent information.

Do not generate a new answer.

Return a score from 0 to 10.

Scoring guide:
10 = fully correct / semantically equivalent
9 = almost completely correct
8 = correct core concept with minor omission
7 = mostly correct
5-6 = partially correct
3-4 = limited understanding
1-2 = minimal relevant understanding
0 = incorrect or irrelevant

QUESTION:
{q_clean}

REFERENCE ANSWER FROM PDF:
{ref_clean}

STUDENT ANSWER:
{ans_clean}

Return ONLY valid JSON:
{{
  "score": 0,
  "reason": "Short explanation of why this score was awarded",
  "matched_concepts": [],
  "missing_concepts": []
}}"""

        # 1. Primary Evaluator: Ollama llama3.2:3b
        result = self._try_ollama(system_prompt)

        # Retry Ollama once if result was invalid
        if result is None:
            logger.warning("Ollama primary evaluation returned None, retrying with strict prompt...")
            retry_prompt = system_prompt + "\nIMPORTANT: Output ONLY pure JSON object. No extra words."
            result = self._try_ollama(retry_prompt)

        # 2. Secondary fallback: Gemini if configured
        if result is None and self.gemini_key:
            logger.info("Attempting fallback to Gemini evaluator...")
            result = self._try_gemini(system_prompt)

        # 3. Tertiary fallback: Semantic rubric
        if result is None:
            logger.warning("All LLMs unavailable. Using deterministic semantic rubric evaluation.")
            result = self._fallback_rubric_evaluation(q_clean, ref_clean, ans_clean)

        return self._validate_and_sanitize_result(result)

    def _try_ollama(self, prompt: str) -> Dict[str, Any] | None:
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                },
            }
            res = requests.post(self.ollama_generate_url, json=payload, timeout=(3.0, 45))
            if res.status_code == 200:
                data = res.json()
                text = data.get("response", "")
                if text:
                    return self._parse_json_response(text)
            else:
                logger.error("Ollama API returned status %s: %s", res.status_code, res.text[:200])
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

    def _validate_and_sanitize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Strict validation of score (0.0 to 10.0) and response structure."""
        if not result or not isinstance(result, dict):
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Evaluation could not be finalized."],
                "reason": "Evaluation returned an unparseable response.",
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

        return {
            "score": clamped_score,
            "max_score": 10.0,
            "correct_points": [str(p) for p in correct_pts[:5]],
            "missing_points": [str(p) for p in missing_pts[:5]],
            "matched_concepts": [str(p) for p in correct_pts[:5]],
            "missing_concepts": [str(p) for p in missing_pts[:5]],
            "reason": reason,
        }

    def _fallback_rubric_evaluation(self, question: str, reference: str, student_answer: str) -> Dict[str, Any]:
        """Heuristic semantic rubric used only if external LLMs are unreachable."""
        if not student_answer or len(student_answer.strip()) < 5:
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Response is empty or insufficient"],
                "reason": "Insufficient technical detail provided in the spoken answer.",
            }

        stopwords = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with",
            "is", "are", "was", "were", "it", "this", "that", "these", "those", "by", "of",
        }
        ref_tokens = {
            w.lower()
            for w in re.findall(r"\b[a-zA-Z]{3,}\b", reference)
            if w.lower() not in stopwords
        }
        student_tokens = {
            w.lower()
            for w in re.findall(r"\b[a-zA-Z]{3,}\b", student_answer)
            if w.lower() not in stopwords
        }

        if not ref_tokens:
            return {
                "score": 5.0,
                "max_score": 10.0,
                "correct_points": ["Provided an answer"],
                "missing_points": [],
                "reason": "Evaluated based on standard academic completion.",
            }

        overlap = ref_tokens.intersection(student_tokens)
        ratio = len(overlap) / len(ref_tokens)

        # Scale ratio to 0-10 score with partial marking tiers
        if ratio >= 0.70:
            score = 9.0 + min(1.0, (ratio - 0.70) * 3)
        elif ratio >= 0.50:
            score = 7.0 + ((ratio - 0.50) / 0.20) * 1.5
        elif ratio >= 0.30:
            score = 4.5 + ((ratio - 0.30) / 0.20) * 2.0
        elif ratio >= 0.15:
            score = 2.0 + ((ratio - 0.15) / 0.15) * 2.0
        else:
            score = max(0.5, ratio * 10)

        score = max(0.0, min(10.0, round(score, 1)))

        return {
            "score": score,
            "max_score": 10.0,
            "correct_points": list(overlap)[:4],
            "missing_points": list(ref_tokens - student_tokens)[:4],
            "reason": f"Evaluated response: {len(overlap)} key syllabus concepts matched.",
        }
