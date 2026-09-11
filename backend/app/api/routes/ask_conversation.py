import uuid
from datetime import datetime
from fastapi import APIRouter
from app.db.models import (
    ChatRequest,
    ChatResponse,
    Conversation,
    Message,
)
from app.db.connection import session_scope
from app.services.llm_service import ask_groq
from app.services.embedding import create_embeddings
from app.services.qdrant_service import (
    search_similar,
    get_session_filenames
)
router = APIRouter()
# ASK CONVERSATION
@router.post(
    "/ask-conversation",
    response_model=ChatResponse
)
def ask_conversation(request: ChatRequest):
    question = request.message
    session_id = request.session_id
    filename = getattr(
        request,
        "filename",
        None
    )
    # Create session_id if not provided
    if not session_id:
        session_id = str(
            uuid.uuid4()
        )
    # Make sure conversation exists
    with session_scope() as session:
        conversation = (
            session.query(Conversation)
            .filter(
                Conversation.session_id
                == session_id
            )
            .first()
        )
        if not conversation:
            conversation = Conversation(
                session_id=session_id,
                title="New Chat"
            )
            session.add(
                conversation
            )
            session.commit()
    # Save user message
    with session_scope() as session:
        user_message = Message(
            session_id=session_id,
            role="user",
            content=question
        )
        session.add(
            user_message
        )
        session.commit()
    # Create embedding for question
    question_embedding = create_embeddings(
        [
            {
                "text": question
            }
        ]
    )[0]
    # Search Qdrant
    # session_id ensures that documents belonging to
    # another chat/session are not retrieved.
    relevant_chunks = search_similar(
        question_embedding,
        top_k=5,
        question=question,
        filename=filename,
        session_id=session_id
    )
    # BUILD CONTEXT
    context_parts = []
    # Use only top 2 chunks
    for chunk in relevant_chunks[:2]:
        chunk_text = chunk.get(
            "text",
            ""
        )
        if not chunk_text:
            continue
        metadata = []
        # Type
        if chunk.get("type"):
            metadata.append(
                f"Type: {chunk['type']}"
            )
        # Page information
        if chunk.get("page"):
            if chunk.get("last_page"):
                if (
                    chunk["last_page"]
                    != chunk["page"]
                ):
                    metadata.append(
                        f"Pages: "
                        f"{chunk['page']}-"
                        f"{chunk['last_page']}"
                    )
                else:
                    metadata.append(
                        f"Page: "
                        f"{chunk['page']}"
                    )
            else:
                metadata.append(
                    f"Page: "
                    f"{chunk['page']}"
                )
        # Heading
        if chunk.get("heading"):
            metadata.append(
                f"Heading: "
                f"{chunk['heading']}"
            )
        # Add metadata + text
        if metadata:
            context_parts.append(
                "\n".join(metadata)
                + "\n"
                + chunk_text
            )
        else:
            context_parts.append(
                chunk_text
            )
    # Join context
    context = "\n\n".join(
        context_parts
    )
    # HARD CONTEXT LIMIT
    MAX_CONTEXT_CHARS = 12000
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[
            :MAX_CONTEXT_CHARS
        ]
    # ASK GROQ
    answer = ask_groq(
        question,
        context
    )
    # SAVE ASSISTANT MESSAGE
    with session_scope() as session:
        assistant_message = Message(
            session_id=session_id,
            role="assistant",
            content=answer
        )
        session.add(
            assistant_message
        )
        # Update conversation
        conversation = (
            session.query(Conversation)
            .filter(
                Conversation.session_id
                == session_id
            )
            .first()
        )
        if conversation:
            conversation.updated_at = (
                datetime.utcnow()
            )
            if conversation.title == "New Chat":
                conversation.title = question[
                    :50
                ]
        session.commit()
    # RETURN RESPONSE
    return ChatResponse(
        response=answer,
        session_id=session_id,
        retrieved_chunks=relevant_chunks
    )
# GET ALL CONVERSATIONS
@router.get(
    "/conversations"
)
def get_conversations():
    with session_scope() as session:
        conversations = (
            session.query(
                Conversation
            )
            .order_by(
                Conversation.updated_at.desc()
            )
            .all()
        )
        result = []
        for conversation in conversations:
            session_id = (
                conversation.session_id
            )
            # Get chat messages
            messages = (
                session.query(
                    Message
                )
                .filter(
                    Message.session_id
                    == session_id
                )
                .order_by(
                    Message.id.asc()
                )
                .all()
            )
            # Get existing document filenames from Qdrant.
            # We are NOT uploading anything again.
            # We are NOT creating new embeddings.
            # We are only reading the filename stored in
            # existing Qdrant payload.
            filenames = get_session_filenames(
                session_id
            )
            # Add conversation
            result.append({
                "session_id":
                    session_id,
                "title":
                    conversation.title,
                "filenames":
                    filenames,
                "messages": [
                    {
                        "role":
                            message.role,
                        "content":
                            message.content
                    }
                    for message in messages
                ]
            })
        return result
# DELETE CONVERSATION
@router.delete(
    "/conversations/{session_id}"
)
def delete_conversation(
    session_id: str
):
    with session_scope() as session:
        conversation = (
            session.query(
                Conversation
            )
            .filter(
                Conversation.session_id
                == session_id
            )
            .first()
        )
        if not conversation:
            return {
                "message":
                    "Conversation not found"
            }
        # Delete messages belonging to conversation
        session.query(
            Message
        ).filter(
            Message.session_id
            == session_id
        ).delete(

            synchronize_session=False
        )
        # Delete conversation
        session.delete(
            conversation
        )
        session.commit()
        return {
            "message":
                "Conversation deleted successfully",
            "session_id":
                session_id

        }