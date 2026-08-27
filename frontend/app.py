import streamlit as st
import requests
# =================================================
# BACKEND CONFIG
# =================================================
BACKEND_URL = "http://127.0.0.1:8001"
# =================================================
# PAGE CONFIG
# =================================================
st.set_page_config(
    page_title="Groq RAG Chatbot",
    page_icon="🤖",
    layout="wide"
)
# =================================================
# SESSION STATE
# =================================================
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_document" not in st.session_state:
    st.session_state.uploaded_document = None
# =================================================
# UPLOAD DOCUMENT
# =================================================
def upload_document(uploaded_file):
    try:
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                "application/pdf"
            )
        }
        response = requests.post(
            f"{BACKEND_URL}/upload",
            files=files,
            timeout=120
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.uploaded_document = (
                data.get(
                    "filename",
                    uploaded_file.name
                )
            )
            st.success(
                f"Document uploaded successfully. "
                f"Chunks: {data.get('chunks', 'N/A')}"
            )
            return True
        else:
            st.error(
                f"Upload failed: "
                f"{response.status_code}"
            )
            st.code(
                response.text
            )
            return False
    except requests.exceptions.ConnectionError:
        st.error(
            "Could not connect to FastAPI backend."
        )
        st.info(
            "Make sure FastAPI is running on port 8001."
        )
        return False
    except requests.exceptions.RequestException as e:
        st.error(
            "Upload request failed."
        )
        st.code(
            str(e)
        )
        return False
# =================================================
# LOAD ALL CONVERSATIONS
# =================================================
def load_conversations():
    try:
        response = requests.get(
            f"{BACKEND_URL}/conversations",
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except requests.exceptions.RequestException:
        return []
# =================================================
# DELETE CONVERSATION
# =================================================
def delete_conversation(
    session_id
):
    try:
        response = requests.delete(
            f"{BACKEND_URL}/conversations/{session_id}",
            timeout=30
        )
        if response.status_code == 200:
            return True
        else:
            st.error(
                f"Delete failed: "
                f"{response.status_code}"
            )
            st.code(
                response.text
            )
            return False
    except requests.exceptions.RequestException as e:
        st.error(
            "Could not delete conversation."
        )
        st.code(
            str(e)
        )
        return False
# =================================================
# SIDEBAR
# =================================================
with st.sidebar:
    st.title(
        "📚 Chat History"
    )
    st.divider()
    # =================================================
    # NEW CHAT
    # =================================================
    if st.button(
        "＋ New Chat",
        use_container_width=True
    ):
        st.session_state.session_id = None
        st.session_state.messages = []
        st.session_state.uploaded_document = None
        st.rerun()
    st.divider()
    # =================================================
    # PREVIOUS CONVERSATIONS
    # =================================================
    st.caption(
        "💬 Previous Chats"
    )
    conversations = load_conversations()
    if conversations:
        for conversation in conversations:
            session_id = conversation.get(
                "session_id"
            )
            title = conversation.get(
                "title",
                "New Chat"
            )
            messages = conversation.get(
                "messages",
                []
            )
            # =================================================
            # CHAT + DELETE BUTTON
            # =================================================
            col1, col2 = st.columns(
                [5, 1]
            )
            # =================================================
            # OPEN CHAT
            # =================================================
            with col1:
                if st.button(
                    title,
                    key=f"chat_{session_id}",
                    use_container_width=True
                ):
                    st.session_state.session_id = (
                        session_id
                    )
                    st.session_state.messages = (
                        messages
                    )
                    st.rerun()
            # =================================================
            # DELETE CHAT
            # =================================================
            with col2:
                if st.button(
                    "🗑️",
                    key=f"delete_{session_id}",
                    help="Delete this conversation"
                ):
                    deleted = delete_conversation(
                        session_id
                    )
                    if deleted:
                        # ---------------------------------
                        # If current chat is deleted
                        # ---------------------------------
                        if (
                            st.session_state.session_id
                            == session_id
                        ):
                            st.session_state.session_id = None
                            st.session_state.messages = []
                        st.rerun()
    else:
        st.caption(
            "No previous chats."
        )
    # =================================================
    # CURRENT DOCUMENT
    # =================================================
    if st.session_state.uploaded_document:
        st.divider()
        st.caption(
            "📄 Current Document"
        )
        st.write(
            st.session_state.uploaded_document
        )
# =================================================
# MAIN CHAT AREA
# =================================================
st.title(
    "📚 Document Q&A Chatbot"
)
st.caption(
    "Ask questions about your uploaded document."
)
# =================================================
# DISPLAY CHAT MESSAGES
# =================================================
for message in st.session_state.messages:
    with st.chat_message(
        message["role"]
    ):
        st.markdown(
            message["content"]
        )
# =================================================
# CHAT INPUT + PDF UPLOAD
# =================================================
prompt = st.chat_input(
    "Ask something about your document...",
    accept_file=True,
    file_type=["pdf"]
)
# =================================================
# HANDLE SUBMISSION
# =================================================
if prompt:
    # =================================================
    # 1. PDF UPLOAD
    # =================================================
    uploaded_files = prompt["files"]
    if uploaded_files:
        uploaded_file = uploaded_files[0]
        upload_success = upload_document(
            uploaded_file
        )
        if upload_success:
            st.session_state.uploaded_document = (
                uploaded_file.name
            )
    # =================================================
    # 2. GET QUESTION
    # =================================================
    question = prompt["text"]
    if question:
        # =================================================
        # PREPARE PAYLOAD
        # =================================================
        payload = {
            "message":
                question,
            "session_id":
                st.session_state.session_id,
            "filename":
                st.session_state.uploaded_document
        }
        # =================================================
        # DISPLAY USER MESSAGE
        # =================================================
        with st.chat_message(
            "user"
        ):
            st.markdown(
                question
            )
        # =================================================
        # CALL FASTAPI
        # =================================================
        try:
            response = requests.post(
                f"{BACKEND_URL}/ask-conversation",
                json=payload,
                timeout=120
            )
            # =================================================
            # SUCCESS
            # =================================================
            if response.status_code == 200:
                data = response.json()
                # -----------------------------------------
                # SAVE SESSION ID
                # -----------------------------------------
                st.session_state.session_id = (
                    data["session_id"]
                )
                # -----------------------------------------
                # GET ANSWER
                # -----------------------------------------
                answer = data["response"]
                # -----------------------------------------
                # SAVE USER MESSAGE
                # -----------------------------------------
                st.session_state.messages.append(
                    {
                        "role":
                            "user",
                        "content":
                            question
                    }
                )
                # -----------------------------------------
                # SAVE ASSISTANT MESSAGE
                # -----------------------------------------
                st.session_state.messages.append(
                    {
                        "role":
                            "assistant",
                        "content":
                            answer
                    }
                )
                # -----------------------------------------
                # DISPLAY ANSWER
                # -----------------------------------------
                with st.chat_message(
                    "assistant"
                ):
                    st.markdown(
                        answer
                    )
                # =================================================
                # RETRIEVED CHUNKS
                # =================================================
                retrieved_chunks = data.get(
                    "retrieved_chunks",
                    []
                )
                if retrieved_chunks:
                    with st.expander(
                        "🔍 Retrieved Chunks"
                    ):
                        for i, chunk in enumerate(
                            retrieved_chunks,
                            start=1
                        ):
                            st.write(
                                f"### Chunk {i}"
                            )
                            st.write(
                                f"Score: "
                                f"{chunk.get('score')}"
                            )
                            st.write(
                                f"Filename: "
                                f"{chunk.get('filename')}"
                            )
                            st.write(
                                f"Type: "
                                f"{chunk.get('type')}"
                            )
                            st.write(
                                f"Page: "
                                f"{chunk.get('page')}"
                            )
                            st.write(
                                f"Last Page: "
                                f"{chunk.get('last_page')}"
                            )
                            st.write(
                                f"Heading: "
                                f"{chunk.get('heading')}"
                            )
                            st.write(
                                chunk.get(
                                    "text",
                                    ""
                                )
                            )
                            st.divider()
            # =================================================
            # BACKEND ERROR
            # =================================================
            else:
                st.error(
                    f"Backend error: "
                    f"{response.status_code}"
                )
                st.code(
                    response.text
                )
        except requests.exceptions.ConnectionError:
            st.error(
                "Could not connect to FastAPI backend."
            )
            st.info(
                "Run FastAPI on port 8001."
            )
        except requests.exceptions.Timeout:
            st.error(
                "Request timed out."
            )
        except requests.exceptions.RequestException as e:
            st.error(
                "Request failed."
            )
            st.code(
                str(e)
            )
