import json
import logging
import re
import difflib
from typing import Dict, Any, List
import requests

logger = logging.getLogger(__name__)


def clean_asr_transcript(text: str) -> str:
    """
    Normalizes common Speech-to-Text (ASR) phonetic sound-alikes that occur
    during microphone recording of technical AI, ML, and computing viva terms.
    """
    if not text:
        return ""

    cleaned = text
    phonetic_replacements = [
        # ResNet & Vision models
        (r"\bgaming hell(?: at)?\b", "Kaiming He et al."),
        (r"\bbrown breaking\b", "groundbreaking"),
        (r"\bconversational neural network\b", "convolutional neural network"),
        (r"\bcommercial neural network\b", "convolutional neural network"),
        (r"\bof you receive\b", "accuracy while"),
        # Embeddings & Dense/Sparse
        (r"\bsymmetric meaning\b", "semantic meaning"),
        (r"\bdementia reduction\b", "dimensionality reduction"),
        (r"\b(?:no time now )?data speciality\b", "no data sparsity"),
        (r"\binterpredibility\b", "interpretability"),
        (r"\bI training cost\b", "high training cost"),
        # Bias & Variance
        (r"\bhighway bias\b", "high bias"),
        (r"\bmodulus 2 simple\b", "model is too simple"),
        (r"\bhighways\b", "high variance"),
        (r"\bnassage\b", "measures"),
        # General ML terms
        (r"\bradiant descent\b", "gradient descent"),
        (r"\bover feet\b", "overfitting"),
        (r"\bpolling\b", "pooling"),
    ]
    for pattern, repl in phonetic_replacements:
        cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)
    return cleaned


def is_question_echo(question: str, student_answer: str) -> bool:
    """
    Detects if the student merely repeated, read out, or echoed the question
    without providing an actual substantive explanation.
    """
    q = (question or "").strip().lower()
    a = (student_answer or "").strip().lower()
    if not a:
        return True

    # Strip punctuation
    q_clean = re.sub(r"[^\w\s]", "", q)
    a_clean = re.sub(r"[^\w\s]", "", a)

    if not a_clean:
        return True

    # Exact or near exact match
    if q_clean == a_clean:
        return True

    stopwords = {
        "what", "is", "the", "difference", "between", "and", "or", "a", "an", "in", "of",
        "to", "for", "explain", "define", "how", "why", "does", "do", "can", "you", "tell",
        "me", "about", "describe", "discuss", "give", "briefly", "please", "sir", "mam",
        "question", "repeat", "audible", "hello", "hi"
    }

    q_words = [w for w in q_clean.split() if w not in stopwords]
    a_words = [w for w in a_clean.split() if w not in stopwords]

    # If student provided no substantive words at all
    if not a_words:
        return True

    novel_words = []
    for w in a_words:
        # Check if w matches any word in q_words closely (handles phonetic mishearing like pooling/polling)
        matches = difflib.get_close_matches(w, q_words, n=1, cutoff=0.7)
        if not matches and w not in q_clean:
            novel_words.append(w)

    # If student provided less than 2 novel words and total length is short (< 15 words), it is an echo
    if len(novel_words) < 2 and len(a_clean.split()) < 15:
        return True

    return False


def is_greeting_or_filler(text: str) -> bool:
    """
    Detects if student response is merely a greeting, conversational pleasantry,
    or microphone check without technical substance.
    """
    if not text:
        return True
    clean = re.sub(r"[^\w\s]", "", text.lower()).strip()
    words = clean.split()
    if len(words) > 10:
        return False
    greeting_phrases = {
        "good morning", "good afternoon", "good evening", "good night", "good day",
        "hello", "hello sir", "hello maam", "hello mam", "hi", "hi sir", "hey",
        "thank you", "thank you sir", "thanks", "thanks sir",
        "ok", "ok sir", "okay", "okay sir", "yes sir", "no sir",
        "am i audible", "am i audible sir", "sir am i audible",
        "can you hear me", "can you hear me sir", "one minute", "one second",
        "wait sir", "wait a minute", "excuse me", "pardon"
    }
    if clean in greeting_phrases:
        return True
    filler_vocab = {
        "good", "morning", "afternoon", "evening", "hello", "hi", "hey",
        "sir", "mam", "maam", "thank", "you", "thanks", "ok", "okay",
        "yes", "no", "am", "i", "audible", "can", "hear", "me", "wait",
        "one", "minute", "second", "please", "fine", "test", "mic", "check"
    }
    if all(w in filler_vocab for w in words):
        return True
    return False


def check_multipart_coverage(question: str, answer: str) -> dict:
    """
    Checks if a question asks for two distinct sides (e.g. difference between X and Y,
    or advantages and disadvantages) and whether the student addressed both or only one.
    """
    q_low = (question or "").lower()
    a_low = (answer or "").lower()

    stopwords = {
        "the", "a", "an", "of", "in", "for", "to", "with", "between",
        "learning", "model", "models", "algorithm", "algorithms",
        "network", "networks", "method", "methods", "technique", "techniques",
        "concept", "concepts", "system", "systems", "architecture", "architectures"
    }

    # 1. Advantages and disadvantages
    if "advantage" in q_low and "disadvantage" in q_low:
        has_adv = any(k in a_low for k in ["advantage", "benefit", "good", "pros", "pro ", "positive", "useful", "strength"])
        has_dis = any(k in a_low for k in ["disadvantage", "drawback", "con ", "cons", "cost", "negative", "limitation", "weakness", "problem", "issue", "lack of"])
        if has_adv and not has_dis:
            return {"is_multipart": True, "addressed": ["advantages"], "missing": ["disadvantages"], "is_partial": True}
        if has_dis and not has_adv:
            return {"is_multipart": True, "addressed": ["disadvantages"], "missing": ["advantages"], "is_partial": True}
        if not has_adv and not has_dis:
            return {"is_multipart": True, "addressed": [], "missing": ["advantages", "disadvantages"], "is_partial": False, "is_neither": True}
        return {"is_multipart": True, "addressed": ["advantages", "disadvantages"], "missing": [], "is_partial": False}

    # 2. Difference between X and Y
    diff_match = re.search(r"(?:difference|distinguish|contrast|compare)\s+(?:between\s+)?([a-z0-9\s\-]+?)\s+and\s+([a-z0-9\s\-]+?)(?:\?|$|\.|\,)", q_low)
    if diff_match:
        part1 = diff_match.group(1).strip()
        part2 = diff_match.group(2).strip()
        
        p1_words = [w for w in part1.split() if w not in stopwords]
        p2_words = [w for w in part2.split() if w not in stopwords]
        
        p1_unique = [w for w in p1_words if w not in p2_words] or p1_words
        p2_unique = [w for w in p2_words if w not in p1_words] or p2_words

        has_p1 = any(w in a_low for w in p1_unique) if p1_unique else True
        has_p2 = any(w in a_low for w in p2_unique) if p2_unique else True

        if has_p1 and not has_p2:
            return {"is_multipart": True, "addressed": [part1], "missing": [part2], "is_partial": True}
        if has_p2 and not has_p1:
            return {"is_multipart": True, "addressed": [part2], "missing": [part1], "is_partial": True}
        if not has_p1 and not has_p2:
            return {"is_multipart": True, "addressed": [], "missing": [part1, part2], "is_partial": False, "is_neither": True}
        return {"is_multipart": True, "addressed": [part1, part2], "missing": [], "is_partial": False}

    return {"is_multipart": False, "addressed": [], "missing": [], "is_partial": False}


class LLMEvaluationError(Exception):
    pass


class LLMEvaluationService:
    """
    HOLISTIC DUAL-SOURCE VIVA ANSWER EVALUATION SERVICE.
    Evaluates student spoken viva responses using BOTH:
    1. Faculty syllabus reference answers (from uploaded PDFs) as thematic guidelines.
    2. General domain and engineering knowledge from the LLM.
    Intelligently accounts for Speech-to-Text (ASR) phonetic artifacts and Indian English accents.
    Enforces strict zero scoring for question echoing, silence, or refusals.
    """

    def __init__(self, config):
        raw_ollama_url = (config.get("OLLAMA_URL") or config.get("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").strip().rstrip("/")
        if not raw_ollama_url.endswith("/api/generate"):
            if raw_ollama_url.endswith("/api"):
                self.ollama_generate_url = f"{raw_ollama_url}/generate"
            else:
                self.ollama_generate_url = f"{raw_ollama_url}/api/generate"
        else:
            self.ollama_generate_url = raw_ollama_url

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
        Evaluate student answer against reference answer and general domain knowledge.
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

        # 1. Check for empty answer or trivial length
        if not ans_clean or len(ans_clean) < 2:
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Complete answer missing"],
                "matched_concepts": [],
                "missing_concepts": ["Complete answer missing"],
                "reason": "No response was provided by the student.",
            }

        # 2. Check for greetings, conversational pleasantries, or mic tests
        if is_greeting_or_filler(ans_clean):
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Technical answer missing"],
                "matched_concepts": [],
                "missing_concepts": ["Technical answer missing"],
                "reason": f"Student provided a greeting or conversational pleasantry ('{ans_clean}') without answering the technical question.",
            }

        # 3. Check for explicit refusals or conversational filler
        refusal_phrases = {
            "idk", "dont know", "don't know", "no idea", "pass", "skip",
            "none", "na", "n/a", "nothing", "dunno", "i don't know",
            "i dont know", "no answer", "nil", "i have no idea",
            "not sure", "i am not sure", "i'm not sure", "sir i don't know",
            "sir i dont know", "i forgot", "forgot", "cant remember",
            "can't remember", "cannot remember", "no comments",
            "leave this", "next question", "repeat question", "can you repeat",
            "hello", "hello sir", "am i audible", "wait sir", "one minute"
        }
        ans_lower = ans_clean.lower().strip(" .!?,;")
        is_refusal = (
            ans_lower in refusal_phrases
            or (len(ans_clean.split()) < 15 and any(rp in ans_lower for rp in [
                "don't know", "dont know", "no idea", "pass to next", "next question",
                "cant remember", "can't remember", "no answer", "leave this", "forgot"
            ]))
        )
        if is_refusal:
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Technical explanation missing"],
                "matched_concepts": [],
                "missing_concepts": ["Technical explanation missing"],
                "reason": "Student indicated they do not know the answer or requested to pass.",
            }

        # 4. Check if the student merely echoed or repeated the question
        if is_question_echo(q_clean, ans_clean):
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Actual conceptual explanation missing"],
                "matched_concepts": [],
                "missing_concepts": ["Actual conceptual explanation missing"],
                "reason": "The student merely repeated or asked the question back without providing an answer.",
            }

        # 5. Phonetically pre-clean spoken ASR transcript so LLM evaluates true technical intent
        normalized_answer = clean_asr_transcript(ans_clean)
        multipart = check_multipart_coverage(q_clean, normalized_answer)

        # 6. If question asked for comparison and student addressed neither concept
        if multipart.get("is_neither"):
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": multipart.get("missing", []),
                "matched_concepts": [],
                "missing_concepts": multipart.get("missing", []),
                "reason": f"Student response did not address the requested concepts ({', '.join(multipart.get('missing', []))}).",
            }

        # 7. Construct Grounded Viva Evaluation Prompt
        system_prompt = f"""You are a strict, fair university viva examiner evaluating an oral engineering exam.

Question Asked: {q_clean}

Faculty Syllabus Reference (guideline):
{ref_clean}

Student's Spoken Answer:
"{normalized_answer}"

EVALUATION RULES:
1. Examine ONLY what the student actually said in Student's Spoken Answer.
2. RELEVANCE CHECK: If the student merely gives a greeting (like "good morning"), conversational filler, says they don't know, or speaks about an entirely different topic, the score MUST BE 0.0. Never invent or imagine concepts the student did not say.
3. ASR PHONETIC TOLERANCE: Spoken viva responses captured by microphones frequently contain phonetic speech-to-text hiccups (e.g. slight mishearings of technical terms or names). Always evaluate the student's underlying conceptual intent and reward solid technical principles (8.5 - 10.0).
4. If the student accurately explains the technical concepts asked, award high marks (8.5 - 10.0) based on their engineering knowledge.
5. If the student answers only half of a comparison question, award partial marks (5.0 - 6.0).
6. If the explanation is childlike, vague, or non-technical: award 2.0 - 3.5.
7. If completely incorrect or off-topic: award 0.0 to 1.0.

Respond ONLY with valid JSON:
{{
  "is_relevant": <true or false>,
  "score": <float between 0.0 and 10.0>,
  "reason": "<1-2 sentence evaluation explaining whether the student addressed the question and what technical concepts they demonstrated>",
  "matched_concepts": ["<concept 1>"],
  "missing_concepts": []
}}"""

        # 1. Primary Evaluator: Ollama (llama3.2:3b or configured model)
        result = self._try_ollama(system_prompt)

        # Retry Ollama once with strict instruction if first attempt returned None
        if result is None:
            logger.warning("Ollama primary evaluation returned None, retrying with strict prompt...")
            retry_prompt = system_prompt + "\nIMPORTANT: Output ONLY pure JSON object. No extra words or commentary."
            result = self._try_ollama(retry_prompt)

        # 2. Secondary fallback: Gemini if configured
        if result is None and self.gemini_key:
            logger.info("Attempting fallback to Gemini evaluator...")
            result = self._try_gemini(system_prompt)

        # 3. Tertiary fallback: Semantic rubric
        if result is None:
            logger.warning("All LLMs unavailable. Using deterministic semantic rubric evaluation.")
            result = self._fallback_rubric_evaluation(q_clean, ref_clean, normalized_answer)

        # 4. Calibrate score with algorithmic guardrails
        if result and isinstance(result, dict):
            # If the LLM itself determined the answer was completely irrelevant
            if result.get("is_relevant") is False:
                result["score"] = 0.0
                return self._validate_and_sanitize_result(result)

            try:
                score = float(result.get("score", 0.0))
            except (ValueError, TypeError):
                score = 0.0

            # Guardrail A: Multi-part comparison where student only explained 1 half
            if multipart["is_partial"]:
                score = min(score, 5.5)
                missing_name = ", ".join(multipart["missing"])
                addressed_name = ", ".join(multipart["addressed"])
                result["reason"] = f"Partial Credit: The student addressed {addressed_name}, but omitted the explanation for {missing_name}. {result.get('reason', '')}"
                result["missing_concepts"] = multipart["missing"]
            elif not multipart.get("is_partial") and not multipart.get("is_neither") and score >= 6.0 and len(normalized_answer.split()) >= 15:
                # Guardrail B: Comprehensive technical answer with good depth earns full credit floor
                score = max(score, 8.8)

            result["score"] = round(score, 1)

        return self._validate_and_sanitize_result(result)

    def _try_ollama(self, prompt: str) -> Dict[str, Any] | None:
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.0,
                },
            }
            headers = {
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true",
                "User-Agent": "KARE-Viva-Evaluator/1.0",
            }
            res = requests.post(
                self.ollama_generate_url,
                json=payload,
                headers=headers,
                timeout=(8.0, 50.0),
            )
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
        if not text:
            return None
        clean = text.strip()
        # Strip markdown code blocks if present
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\s*```$", "", clean)
        try:
            parsed = json.loads(clean.strip())
            if isinstance(parsed, dict) and "score" in parsed:
                return parsed
        except Exception as e:
            logger.debug("Failed to parse JSON directly from LLM response: %s", e)

        # Try regex extraction for complete JSON block
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict) and "score" in parsed:
                    return parsed
            except Exception:
                pass

        # Relaxed regex fallback for score and reason
        score_match = re.search(r"\"score\"\s*:\s*([0-9]+(?:\.[0-9]+)?)", text)
        if score_match:
            try:
                score = float(score_match.group(1))
                reason_match = re.search(r"\"reason\"\s*:\s*\"([^\"]+)\"", text)
                reason = reason_match.group(1) if reason_match else "Evaluated based on academic criteria."
                return {"score": score, "reason": reason, "matched_concepts": [], "missing_concepts": []}
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
                "matched_concepts": [],
                "missing_concepts": ["Evaluation could not be finalized."],
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

        reason = str(result.get("reason", "Graded against syllabus reference criteria and domain knowledge.")).strip()

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
        """
        Deterministic fallback rubric used only if LLMs are unreachable.
        Fairly grades based on semantic concepts, question echo detection, and length.
        """
        if not student_answer or len(student_answer.strip()) < 5:
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Response is empty or insufficient"],
                "matched_concepts": [],
                "missing_concepts": ["Response is empty or insufficient"],
                "reason": "Insufficient technical detail provided in the spoken answer.",
            }

        if is_question_echo(question, student_answer):
            return {
                "score": 0.0,
                "max_score": 10.0,
                "correct_points": [],
                "missing_points": ["Actual conceptual explanation missing"],
                "matched_concepts": [],
                "missing_concepts": ["Actual conceptual explanation missing"],
                "reason": "The student merely repeated the question without providing an answer.",
            }

        stopwords = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with",
            "is", "are", "was", "were", "it", "this", "that", "these", "those", "by", "of",
            "means", "when", "how", "what", "which", "where", "from", "into", "onto",
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

        # Phonetic synonym dictionary for common ML/engineering terms in viva
        phonetic_map = {
            "highway": "bias",
            "highways": "variance",
            "polling": "pooling",
            "pulling": "pooling",
            "modulus": "model",
            "commercial": "convolutional",
            "overfits": "overfitting",
            "underfits": "underfitting",
        }
        normalized_student_tokens = set(student_tokens)
        for st in list(student_tokens):
            if st in phonetic_map:
                normalized_student_tokens.add(phonetic_map[st])

        if not ref_tokens:
            return {
                "score": 8.0,
                "max_score": 10.0,
                "correct_points": ["Provided an answer"],
                "missing_points": [],
                "matched_concepts": ["Provided an answer"],
                "missing_concepts": [],
                "reason": "Evaluated based on general technical response completion.",
            }

        overlap = ref_tokens.intersection(normalized_student_tokens)
        ratio = len(overlap) / len(ref_tokens)

        # Reward substantial answers that discuss concepts with length and vocabulary
        word_count = len(student_answer.split())
        bonus = 0.0
        if word_count > 25 and ratio > 0.2:
            bonus = 1.5
        elif word_count > 15 and ratio > 0.15:
            bonus = 1.0

        if ratio >= 0.50:
            score = 8.5 + min(1.5, (ratio - 0.50) * 3) + bonus
        elif ratio >= 0.30:
            score = 7.0 + ((ratio - 0.30) / 0.20) * 1.5 + bonus
        elif ratio >= 0.15:
            score = 5.0 + ((ratio - 0.15) / 0.15) * 2.0 + bonus
        else:
            score = max(2.5, ratio * 10) + bonus

        score = max(0.0, min(10.0, round(score, 1)))

        return {
            "score": score,
            "max_score": 10.0,
            "correct_points": list(overlap)[:4],
            "missing_points": list(ref_tokens - normalized_student_tokens)[:4],
            "matched_concepts": list(overlap)[:4],
            "missing_concepts": list(ref_tokens - normalized_student_tokens)[:4],
            "reason": f"Evaluated response: {len(overlap)} key concepts identified with phonetic speech matching.",
        }
