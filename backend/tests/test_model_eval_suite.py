import json
import logging
from app.services.llm_service import LLMEvaluationService

logging.basicConfig(level=logging.INFO)

config = {
    "OLLAMA_URL": "http://127.0.0.1:11434/api/generate",
    "OLLAMA_MODEL": "llama3.2:3b"
}
service = LLMEvaluationService(config)

test_scenarios = [
    {
        "id": 1,
        "category": "Google Lens / Perfect Textbook Answer",
        "question": "What is ResNet?",
        "reference": "ResNet is a CNN model introduced in 2015. It uses residual or skip connections to make training very deep networks easier.",
        "student_answer": "ResNet, short for Residual Network, is a deep learning convolutional neural network architecture introduced by Kaiming He et al. in 2015 to solve the degradation problem in very deep networks using identity shortcut connections.",
        "expected_min": 8.8,
        "expected_max": 10.0,
    },
    {
        "id": 2,
        "category": "Google Lens / Perfect Textbook Answer",
        "question": "What is EfficientNet?",
        "reference": "EfficientNet is a CNN model introduced in 2019. It uses compound scaling to efficiently scale network depth, width, and image resolution.",
        "student_answer": "EfficientNet is a convolutional neural network architecture developed by Google Research in 2019 that uses compound scaling to uniformly scale depth, width, and resolution, achieving state of the art accuracy with fewer parameters.",
        "expected_min": 8.8,
        "expected_max": 10.0,
    },
    {
        "id": 3,
        "category": "Google Lens / Full Domain Explanation",
        "question": "What are the advantages and disadvantages of Dense representation?",
        "reference": "Dense representation is easy to process and is useful for numerical features and neural networks. However, it can require more memory and computation when there are many features.",
        "student_answer": "In deep learning and NLP, advantages of dense representations are capturing rich semantic relationships, dimensionality reduction, and avoiding data sparsity. Disadvantages include lack of interpretability, high computational training cost, and out of vocabulary issues.",
        "expected_min": 8.8,
        "expected_max": 10.0,
    },
    {
        "id": 4,
        "category": "Heavy ASR Phonetic Speech Noise (Correct Concepts)",
        "question": "What is the difference between Bias and Variance?",
        "reference": "Bias is error caused when model is too simple (underfitting). Variance is error caused when model is sensitive to training data (overfitting).",
        "student_answer": "nassage how far of a models predictions are from the True values Highway bias means modulus 2 simple in Andhra Pradesh training data variance measures how much the models prediction change when trained on different data sets Highways means the models two complex and overfits the training data",
        "expected_min": 8.5,
        "expected_max": 10.0,
    },
    {
        "id": 5,
        "category": "ASR Phonetic Noise (Kaiming He misheard)",
        "question": "What is ResNet?",
        "reference": "ResNet is a CNN model introduced in 2015 using residual or skip connections.",
        "student_answer": "resnet short for residual network is brown breaking deep learning architecture introduced by gaming hell at in 2015 to resolve the degradation problem in very deep neural networks",
        "expected_min": 8.5,
        "expected_max": 10.0,
    },
    {
        "id": 6,
        "category": "Partial Credit (1 of 2 concepts answered)",
        "question": "What is the difference between Supervised and Unsupervised Learning?",
        "reference": "Supervised learning uses labeled datasets to train models for prediction. Unsupervised learning finds hidden patterns or clusters in unlabeled data without target labels.",
        "student_answer": "Supervised learning is where the model is trained on labeled data with input features and known target outputs to perform classification or regression.",
        "expected_min": 5.0,
        "expected_max": 6.5,
    },
    {
        "id": 7,
        "category": "Weak / Vague Explanation",
        "question": "What is Gradient Descent?",
        "reference": "Gradient descent is an optimization algorithm used to minimize the loss function by iteratively updating model parameters in the direction of the steepest descent.",
        "student_answer": "It is a graph with high points and low points on numbers to make things go down.",
        "expected_min": 0.0,
        "expected_max": 3.5,
    },
    {
        "id": 8,
        "category": "Completely Wrong Answer",
        "question": "What is Backpropagation?",
        "reference": "Backpropagation calculates the gradients of the loss function with respect to weights using the chain rule to update neural network weights.",
        "student_answer": "Backpropagation is a file compression tool used to compress mp3 audio files into zip folders.",
        "expected_min": 0.0,
        "expected_max": 1.0,
    },
    {
        "id": 9,
        "category": "Question Echo / Parroting",
        "question": "What is the difference between Pooling and Padding?",
        "reference": "Pooling reduces spatial size. Padding adds border pixels.",
        "student_answer": "what is the difference between polling and padding",
        "expected_min": 0.0,
        "expected_max": 0.0,
    },
    {
        "id": 10,
        "category": "Refusal / Non-Answer",
        "question": "Explain the Vanishing Gradient problem.",
        "reference": "Gradients become exponentially small as they are backpropagated through deep layers.",
        "student_answer": "I don't know sir please pass to next question",
        "expected_min": 0.0,
        "expected_max": 0.0,
    },
    {
        "id": 11,
        "category": "User Screenshot Bug: Pure Greeting",
        "question": "What is the difference between Dense and Sparse data?",
        "reference": "Dense data contains mostly non-zero values, while sparse data contains mostly zero values. Sparse representation can save memory when most of the values are zero.",
        "student_answer": "good morning",
        "expected_min": 0.0,
        "expected_max": 0.0,
    },
    {
        "id": 12,
        "category": "Conversational Audio Check / Greeting",
        "question": "What is ResNet?",
        "reference": "ResNet uses residual skip connections to train deep networks.",
        "student_answer": "hello sir am i audible",
        "expected_min": 0.0,
        "expected_max": 0.0,
    }
]

print("=" * 80)
print("STARTING COMPREHENSIVE VIVA EVALUATION TEST SUITE")
print("=" * 80)

results_summary = []

for s in test_scenarios:
    res = service.evaluate_answer(s["question"], s["reference"], s["student_answer"])
    score = res["score"]
    passed = s["expected_min"] <= score <= s["expected_max"]
    status_str = "PASS" if passed else "FAIL"
    
    print(f"\nScenario #{s['id']} [{s['category']}]:")
    print(f"  Question: {s['question']}")
    print(f"  Answer:   {s['student_answer'][:70]}...")
    print(f"  Score:    {score}/10 (Expected: {s['expected_min']} - {s['expected_max']}) -> [{status_str}]")
    print(f"  Reason:   {res['reason']}")
    
    results_summary.append({
        "id": s["id"],
        "category": s["category"],
        "score": score,
        "expected": f"{s['expected_min']}-{s['expected_max']}",
        "passed": passed,
        "reason": res["reason"]
    })

print("\n" + "=" * 80)
print("FINAL SUMMARY REPORT:")
total = len(results_summary)
passed_count = sum(1 for r in results_summary if r["passed"])
print(f"Total Scenarios Tested: {total}")
print(f"Passed: {passed_count} / {total} ({(passed_count/total)*100:.1f}%)")
print("=" * 80)
