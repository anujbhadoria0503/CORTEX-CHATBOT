import uuid
from datetime import datetime
from fastapi import APIRouter
from app.db.models import ChatRequest, ChatResponse, Conversation, Message
from app.db.connection import session_scope
from app.services.llm_service import ask_groq
from app.services.embedding import create_embeddings
from app.services.qdrant_service import search_similar
router = APIRouter()
# ============================================================
# POST /ask-conversation
# ============================================================
@router.post("/ask-conversation", response_model=ChatResponse)
def ask_conversation(request: ChatRequest):
    # ========================================================
    # 1. GET QUESTION
    # ========================================================
    question = request.message
    session_id = request.session_id
    filename = getattr(request, "filename", None)
    # ========================================================
    # 2. CREATE SESSION ID
    # ========================================================
    if not session_id:
        session_id = str(uuid.uuid4())
    # ========================================================
    # 3. FIND / CREATE CONVERSATION
    # ========================================================
    with session_scope() as session:
        conversation = (
            session.query(Conversation)
            .filter(Conversation.session_id == session_id)
            .first()
        )
        if not conversation:
            if request.session_id:
                return ChatResponse(
                    response="Session not found",
                    session_id=session_id,
                    retrieved_chunks=[]
                )
            conversation = Conversation(
                session_id=session_id,
                title="New Chat"
            )
            session.add(conversation)
            session.commit()
    # ========================================================
    # 4. SAVE USER MESSAGE
    # ========================================================
    with session_scope() as session:
        user_message = Message(
            session_id=session_id,
            role="user",
            content=question
        )
        session.add(user_message)
        session.commit()
    # ========================================================
    # 5. CREATE QUESTION EMBEDDING
    # ========================================================
    question_embedding = create_embeddings([{"text": question}])[0]
    # ========================================================
    # 6. SEARCH QDRANT
    # ========================================================
    relevant_chunks = search_similar(
        question_embedding,
        top_k=5,
        question=question,
        filename=filename
    )
    # ========================================================
    # 7. CREATE CONTEXT
    # ========================================================
    context_parts = []
    for chunk in relevant_chunks:
        chunk_text = chunk.get("text", "")
        if not chunk_text:
            continue
        metadata = []
        if chunk.get("type"):
            metadata.append(f"Type: {chunk['type']}")

        if chunk.get("page"):
            if chunk.get("last_page"):
                if chunk["last_page"] != chunk["page"]:
                    metadata.append(
                        f"Pages: {chunk['page']}-{chunk['last_page']}"
                    )
                else:
                    metadata.append(f"Page: {chunk['page']}")
            else:
                metadata.append(f"Page: {chunk['page']}")

        if chunk.get("heading"):
            metadata.append(f"Heading: {chunk['heading']}")

        if metadata:
            context_parts.append(
                "\n".join(metadata) + "\n" + chunk_text
            )
        else:
            context_parts.append(chunk_text)
    context = "\n\n".join(context_parts)
    # ========================================================
    # 8. SEND CONTEXT + QUESTION TO GROQ
    # ========================================================
    answer = ask_groq(question, context)
    # ========================================================
    # 9. SAVE ASSISTANT RESPONSE
    # ========================================================
    with session_scope() as session:
        assistant_message = Message(
            session_id=session_id,
            role="assistant",
            content=answer
        )
        session.add(assistant_message)
        conversation = (
            session.query(Conversation)
            .filter(Conversation.session_id == session_id)
            .first()
        )
        if conversation:
            conversation.updated_at = datetime.utcnow()
            if conversation.title == "New Chat":
                conversation.title = question[:50]
        session.commit()
    # ========================================================
    # 10. RETURN RESPONSE
    # ========================================================
    return ChatResponse(
        response=answer,
        session_id=session_id,
        retrieved_chunks=relevant_chunks
    )
# ============================================================
# GET /conversations
# ============================================================
@router.get("/conversations")
def get_conversations():
    with session_scope() as session:
        conversations = (
            session.query(Conversation)
            .order_by(Conversation.updated_at.desc())
            .all()
        )
        result = []
        for conversation in conversations:
            messages = (
                session.query(Message)
                .filter(Message.session_id == conversation.session_id)
                .order_by(Message.id.asc())
                .all()
            )
            result.append({
                "session_id": conversation.session_id,
                "title": conversation.title,
                "messages": [
                    {
                        "role": message.role,
                        "content": message.content
                    }
                    for message in messages
                ]
            })
        return result
# ============================================================
# DELETE /conversations/{session_id}
# ============================================================
@router.delete("/conversations/{session_id}")
def delete_conversation(session_id: str):
    with session_scope() as session:
        conversation = (
            session.query(Conversation)
            .filter(Conversation.session_id == session_id)
            .first()
        )
        if not conversation:
            return {
                "message": "Conversation not found"
            }
        session.delete(conversation)
        session.commit()
        return {
            "message": "Conversation deleted successfully",
            "session_id": session_id
        }