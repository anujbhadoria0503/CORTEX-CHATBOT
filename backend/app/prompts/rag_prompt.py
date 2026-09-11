# RAG SYSTEM PROMPT
SYSTEM_PROMPT = """
You are a helpful document question-answering assistant.
Answer the user's question using only the information
provided in the document context.
If the answer is not present in the document context,
say:
"I could not find the answer in the uploaded document."
"""
# BUILD USER PROMPT
def build_rag_prompt(
    context: str,
    question: str
) -> str:
    prompt = f"""
Document Context:
{context}
User Question:
{question}
"""
    return prompt