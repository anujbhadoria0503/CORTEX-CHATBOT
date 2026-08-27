import os
import requests
import pandas as pd
from dotenv import load_dotenv
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from langchain_groq import ChatGroq
from ragas.embeddings import BaseRagasEmbeddings
from sentence_transformers import SentenceTransformer
# ============================================================
# CONFIG
# ============================================================
load_dotenv(
    "/Users/anujsarita/Documents/bgelarge/backend/.env"
)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found")
API_URL = "http://127.0.0.1:8001/ask-conversation"
GROQ_MODEL = "allam-2-7b"
EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
# ============================================================
# GROQ LLM
# ============================================================
evaluator_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=GROQ_MODEL,
    temperature=0,
    max_tokens=1024,
    timeout=120,
    max_retries=0,
)
# ============================================================
# BGE-LARGE FOR RAGAS
# ============================================================
class BGEEmbeddings(BaseRagasEmbeddings):
    def __init__(self):
        self.model = SentenceTransformer(
            EMBEDDING_MODEL
        )
    def embed_documents(self, texts):
        if not texts:
            return []
        return self.model.encode(
            texts,
            normalize_embeddings=True
        ).tolist()
    def embed_query(self, text):
        return self.model.encode(
            [text],
            normalize_embeddings=True
        )[0].tolist()
    async def aembed_documents(self, texts):
        return self.embed_documents(texts)
    async def aembed_query(self, text):
        return self.embed_query(text)
ragas_embeddings = BGEEmbeddings()
# ============================================================
# 10 QUESTIONS
# 5 LABOUR + 5 DOCX
# ============================================================
evaluation_questions = [
    # ---------------- LABOUR ----------------
    {
        "question":
            "What is the purpose of the Labour Standards Act?",
        "reference":
            "The Labour Standards Act provides fundamental protection to individual workers and establishes standard employment practices and minimum employment standards."
    },
    {
        "question":
            "Who does the Labour Standards Act apply to?",
        "reference":
            "The Labour Standards Act applies to people employed under a contract of service."
    },
    {
        "question":
            "How many weeks of annual vacation does an employee receive after 15 years of continuous employment?",
        "reference":
            "An employee with 15 years or more of continuous employment receives 3 weeks of annual vacation."
    },
    {
        "question":
            "What percentage of vacation pay is provided to an employee with 15 years or more of continuous employment?",
        "reference":
            "An employee with 15 years or more of continuous employment receives 6% vacation pay."
    },
    {
        "question":
            "How many days of sick leave are available after 30 days of employment?",
        "reference":
            "An employee employed for at least 30 days is entitled to 7 days of unpaid sick or family responsibility leave per year."
    },
    # ---------------- DOCX ----------------
    {
        "question":
            "What is the standard working schedule for employees?",
        "reference":
            "The standard working schedule is Monday through Friday."
    },
    {
        "question":
            "What responsibilities does the AI department have?",
        "reference":
            "The AI department maintains machine-learning services, evaluates model performance, and supports data-driven applications."
    },
    {
        "question":
            "What is the department and role of employee EMP-1001?",
        "reference":
            "EMP-1001 is in the AI department and the role is ML Engineer."
    },
    {
        "question":
            "What is the duration and requirement status of TR-02?",
        "reference":
            "TR-02 is Information Security training, has a duration of 3 hours, and is required."
    },
    {
        "question":
            "Who is the contact person for the IT department and what is their extension?",
        "reference":
            "Rahul Jain is the IT department contact and the extension is 310."
    },
]
# ============================================================
# GET ANSWER + CONTEXT FROM BACKEND
# ============================================================
questions = []
answers = []
contexts = []
references = []
for item in evaluation_questions:
    question = item["question"]
    try:
        response = requests.post(
            API_URL,
            json={
                "message": question
            },
            timeout=180
        )
        response.raise_for_status()
        result = response.json()
        answer = result.get(
            "response",
            ""
        )
        retrieved_chunks = result.get(
            "retrieved_chunks",
            []
        )
        context = [
            chunk.get(
                "text",
                ""
            )[:1200]
            for chunk in retrieved_chunks
            if isinstance(
                chunk,
                dict
            )
            and chunk.get(
                "text"
            )
        ][:2]
        questions.append(question)
        answers.append(answer)
        contexts.append(context)
        references.append(item["reference"])
    except Exception as e:
        questions.append(question)
        answers.append("")
        contexts.append([])
        references.append(item["reference"])
# ============================================================
# DATASET
# ============================================================
dataset = Dataset.from_dict({
    "question": questions,
    "answer": answers,
    "contexts": contexts,
    "reference": references,
})
# ============================================================
# RESULTS DATAFRAME
# ============================================================
final_results = pd.DataFrame({
    "question": questions,
    "answer": answers,
    "reference": references,
})
# ============================================================
# METRICS
# ============================================================
metrics = [
    ("faithfulness", faithfulness),
    ("answer_relevancy", answer_relevancy),
    ("context_precision", context_precision),
    ("context_recall", context_recall),
]
# ============================================================
# RUN RAGAS
# ============================================================
for metric_name, metric in metrics:
    try:
        result = evaluate(
            dataset,
            metrics=[metric],
            llm=evaluator_llm,
            embeddings=ragas_embeddings,
            raise_exceptions=False,
            show_progress=True,
            batch_size=1,
        )
        result_df = result.to_pandas()
        if metric_name in result_df.columns:
            final_results[metric_name] = result_df[
                metric_name
            ]
        else:
            final_results[metric_name] = None
    except Exception as e:
        print(
            f"{metric_name} failed:",
            e
        )
        final_results[metric_name] = None
# ============================================================
# AVERAGE SCORES
# ============================================================
print("\nFINAL RAGAS SCORES")
for metric_name, _ in metrics:
    values = pd.to_numeric(
        final_results[metric_name],
        errors="coerce"
    )
    score = values.mean()
    if pd.isna(score):
        print(
            f"{metric_name}: NaN"
        )
    else:
        print(
            f"{metric_name}: {score:.4f}"
        )
# ============================================================
# SAVE CSV
# ============================================================
output_file = (
    "/Users/anujsarita/Documents/bgelarge/"
    "ragas_evaluation/"
    "ragas_results_bge_large.csv"
)
final_results.to_csv(
    output_file,
    index=False
)
print(
    f"\nSaved: {output_file}"
)