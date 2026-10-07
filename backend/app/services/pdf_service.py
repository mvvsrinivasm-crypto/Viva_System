import hashlib
import re
from pathlib import Path
from typing import Dict, List, Any
import pymupdf as fitz


class PDFExtractionError(Exception):
    pass


class PDFService:
    @staticmethod
    def calculate_file_hash(file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        """Extract clean text from PDF bytes using PyMuPDF."""
        if not pdf_bytes or len(pdf_bytes) == 0:
            raise PDFExtractionError("Uploaded file is empty (0 bytes).")

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            raise PDFExtractionError(f"Corrupted or invalid PDF document: {str(e)}")

        try:
            if doc.page_count == 0:
                raise PDFExtractionError("PDF contains 0 pages.")

            pages_text = []
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                # sort=True ensures correct reading order across columns/blocks
                text = page.get_text("text", sort=True)
                if text and text.strip():
                    pages_text.append(text)

            full_text = "\n".join(pages_text)
            if not full_text.strip():
                raise PDFExtractionError(
                    "No readable text found in PDF. Please ensure the PDF has searchable text, not scanned images without OCR."
                )

            return full_text
        finally:
            doc.close()

    @classmethod
    def parse_qa_pairs(cls, text: str) -> Dict[str, Any]:
        """
        Extract question and reference answer pairs strictly from the text.
        NEVER generates missing questions or answers.
        If a question lacks a reference answer, it is flagged as invalid.
        """
        # Normalize line endings and whitespace
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.strip() for line in normalized.split("\n")]
        cleaned_text = "\n".join(lines)

        # Regex to locate beginning of each question:
        # Pattern 1: Lines starting with "1. ", "1) ", "Q1. ", "Q1: ", "Q.1: ", "Question 1:", "Question 1."
        q_start_re = re.compile(
            r"(?im)^\s*(?:Q(?:uestion)?\.?\s*(\d+)[.:\-)]|\b(\d+)[\.\)][ \t]+|Question\s*(\d+)[.:\-]?\s*)",
        )

        # Find all question start line indices
        raw_lines = cleaned_text.split("\n")
        question_blocks = []
        current_num = None
        current_lines = []

        for line in raw_lines:
            m = q_start_re.match(line)
            if m:
                # If we had a prior question block, save it
                if current_num is not None and current_lines:
                    question_blocks.append((current_num, "\n".join(current_lines)))
                # Extract question number
                q_num_str = m.group(1) or m.group(2) or m.group(3)
                current_num = int(q_num_str) if q_num_str else len(question_blocks) + 1
                # Strip the marker prefix from the line
                content_after_marker = line[m.end():].strip()
                current_lines = [content_after_marker] if content_after_marker else []
            else:
                if current_num is not None:
                    current_lines.append(line)

        # Append last block
        if current_num is not None and current_lines:
            question_blocks.append((current_num, "\n".join(current_lines)))

        extracted_questions: List[Dict[str, Any]] = []
        invalid_questions: List[Dict[str, Any]] = []

        # If numbered question headers were found
        if question_blocks:
            for q_num, block_content in question_blocks:
                # 1. Look for explicit "Answer:" / "Ans:" / "Reference Answer:" / "A:"
                ans_match = re.search(r"(?im)^\s*(?:Answer|Ans|Reference\s*Answer|A)\s*[:.\-]\s*", block_content)
                if ans_match:
                    q_text = block_content[:ans_match.start()].strip()
                    ans_text = block_content[ans_match.end():].strip()
                    is_valid = bool(q_text and ans_text)
                    error = None if is_valid else "Empty question or answer content"
                else:
                    # 2. Check if answer appears inline: e.g. "What is X? Answer: Y"
                    ans_inline = re.split(r"(?i)\b(?:Answer|Ans|Reference\s*Answer)\s*[:.\-]\s*", block_content, maxsplit=1)
                    if len(ans_inline) == 2 and ans_inline[1].strip():
                        q_text = ans_inline[0].strip()
                        ans_text = ans_inline[1].strip()
                        is_valid = bool(q_text and ans_text)
                        error = None if is_valid else "Empty question or answer content"
                    else:
                        # 3. Check for natural academic Q&A format: question ends with '?' and answer follows
                        qmark_matches = list(re.finditer(r"\?(?:\s*\n+|\s+)", block_content))
                        found_split = False
                        if qmark_matches:
                            for qm in reversed(qmark_matches):
                                potential_q = block_content[:qm.start() + 1].strip()
                                potential_ans = block_content[qm.end():].strip()
                                if potential_q and potential_ans:
                                    q_text = potential_q
                                    ans_text = potential_ans
                                    is_valid = True
                                    error = None
                                    found_split = True
                                    break
                        if not found_split:
                            q_pos = block_content.find("?")
                            if q_pos != -1 and q_pos < len(block_content) - 1:
                                potential_q = block_content[:q_pos + 1].strip()
                                potential_ans = block_content[q_pos + 1:].strip()
                                if potential_q and potential_ans:
                                    q_text = potential_q
                                    ans_text = potential_ans
                                    is_valid = True
                                    error = None
                                    found_split = True
                        if not found_split:
                            # 4. Check paragraph split (double newline)
                            if "\n\n" in block_content:
                                parts = block_content.split("\n\n", 1)
                                if parts[0].strip() and parts[1].strip():
                                    q_text = parts[0].strip()
                                    ans_text = parts[1].strip()
                                    is_valid = True
                                    error = None
                                    found_split = True
                        if not found_split:
                            q_text = block_content.strip()
                            ans_text = ""
                            is_valid = False
                            error = "Missing reference answer in PDF"

                # Normalize whitespace in question text so line-wrapped questions form cohesive sentences
                if q_text:
                    q_text = " ".join(q_text.split())
                if ans_text:
                    ans_text = re.sub(r"\n{3,}", "\n\n", ans_text).strip()

                item = {
                    "question_number": q_num,
                    "question_text": q_text,
                    "reference_answer": ans_text,
                    "is_valid": is_valid,
                    "validation_error": error,
                }

                if is_valid:
                    extracted_questions.append(item)
                else:
                    invalid_questions.append(item)
        else:
            # Fallback: Check for generic "Question: ... Answer: ..." without numbers
            qa_split_re = re.compile(
                r"(?im)^\s*Question\s*[:.\-]\s*(.*?)(?=^\s*Answer\s*[:.\-]\s*)",
                re.DOTALL,
            )
            # Find Question: ... Answer: ... pairs
            parts = re.split(r"(?im)^\s*(?:Question|Answer|Ans)\s*[:.\-]\s*", cleaned_text)
            # If parts found in Q/A alternating sequence
            if len(parts) >= 3:
                # First part is header before first question
                idx = 1
                q_count = 1
                while idx < len(parts):
                    q_part = parts[idx].strip()
                    ans_part = parts[idx + 1].strip() if (idx + 1) < len(parts) else ""
                    is_valid = bool(q_part and ans_part)
                    item = {
                        "question_number": q_count,
                        "question_text": q_part,
                        "reference_answer": ans_part,
                        "is_valid": is_valid,
                        "validation_error": None if is_valid else "Missing reference answer in PDF",
                    }
                    if is_valid:
                        extracted_questions.append(item)
                    else:
                        invalid_questions.append(item)
                    idx += 2
                    q_count += 1

        total_detected = len(extracted_questions) + len(invalid_questions)
        valid_count = len(extracted_questions)
        invalid_count = len(invalid_questions)

        validation_passed = (valid_count >= 3) and (invalid_count == 0)
        validation_message = None

        if total_detected == 0:
            validation_message = "No questions found in the uploaded PDF. Please format with '1. Question ... Answer: ...' or 'Q1. ... Answer: ...'."
        elif invalid_count > 0:
            validation_message = f"Validation failed: {invalid_count} question(s) do not have reference answers. Faculty must correct the document and re-upload. The system will never generate missing answers."
        elif valid_count < 3:
            validation_message = f"Validation failed: Found only {valid_count} valid questions. A minimum of 3 questions with reference answers is required to publish a viva."
        else:
            validation_message = f"Validation successful: {valid_count} valid question-answer pairs extracted."

        return {
            "total_detected": total_detected,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "validation_passed": validation_passed,
            "validation_message": validation_message,
            "questions": extracted_questions,
            "invalid_questions": invalid_questions,
        }
