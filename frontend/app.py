import streamlit as st
import requests
import uuid
# CONFIG
BACKEND_URL = "http://127.0.0.1:8001"
# PAGE CONFIG
st.set_page_config(
    page_title="Groq RAG Chatbot",
    page_icon="🤖",
    layout="wide"
)
# SESSION STATE
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_document" not in st.session_state:
    st.session_state.uploaded_document = None
# FUNCTIONS
def create_new_chat():
    # Create a new chat session
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.uploaded_document = None
def load_conversations():
    # Get previous conversations from backend
    try:
        response = requests.get(
            f"{BACKEND_URL}/conversations",
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Could not load conversations: {e}")
        return []
def load_conversation(conversation):
    # Open an existing conversation
    st.session_state.session_id = conversation.get("session_id")
    st.session_state.messages = conversation.get("messages", [])
    # Restore uploaded document name
    filenames = conversation.get("filenames", [])
    if filenames:
        st.session_state.uploaded_document = filenames[0]
    else:
        st.session_state.uploaded_document = None
def delete_conversation(session_id):
    # Delete a conversation from backend
    try:
        response = requests.delete(
            f"{BACKEND_URL}/conversations/{session_id}",
            timeout=30
        )
        return response.status_code == 200
    except Exception as e:
        st.error(f"Delete error: {e}")
        return False
def upload_document(uploaded_file):
    # Upload PDF/DOCX to backend
    if not st.session_state.session_id:
        st.session_state.session_id = str(uuid.uuid4())
    # Get correct MIME type
    mime_type = uploaded_file.type or "application/octet-stream"
    # Prepare file
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            mime_type
        )
    }
    data = {
        "session_id": st.session_state.session_id
    }
    # Send upload request
    try:
        response = requests.post(
            f"{BACKEND_URL}/upload",
            files=files,
            data=data,
            timeout=120
        )
        if response.status_code != 200:
            st.error(f"Upload failed: {response.status_code}")
            return False
        result = response.json()
        # Check backend response
        if result.get("message") != "Document uploaded successfully":
            st.error(
                result.get(
                    "message",
                    "Document upload failed."
                )
            )
            return False
        # Store filename
        st.session_state.uploaded_document = result.get(
            "filename",
            uploaded_file.name
        )
        # Store returned session ID
        returned_session_id = result.get("session_id")
        if returned_session_id:
            st.session_state.session_id = returned_session_id
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Could not connect to backend: {e}")
        return False
# SIDEBAR
with st.sidebar:
    st.title("💬 Groq RAG Chatbot")
    # NEW CHAT BUTTON
    if st.button(
        "➕ New Chat",
        use_container_width=True
    ):
        create_new_chat()
        st.rerun()
    st.divider()
    st.subheader("Previous Chats")
    # PREVIOUS CHATS
    conversations = load_conversations()
    if not conversations:
        st.caption("No previous chats")
    else:
        for conversation in conversations:
            session_id = conversation.get("session_id")
            title = conversation.get("title", "New Chat")
            # Get filenames stored for this session
            filenames = conversation.get("filenames", [])
            # Two columns: Chat and Delete
            col1, col2 = st.columns([5, 1])
            # CHAT BUTTON
            with col1:
                if st.button(
                    f"💬 {title}",
                    key=f"chat_{session_id}",
                    use_container_width=True
                ):
                    load_conversation(conversation)
                    st.rerun()
                # Show uploaded document name
                for filename in filenames:
                    st.caption(f"📄 {filename}")
            # DELETE BUTTON
            with col2:
                if st.button(
                    "🗑️",
                    key=f"delete_{session_id}",
                    help="Delete this chat"
                ):
                    deleted = delete_conversation(session_id)
                    if deleted:
                        # If currently opened chat is being deleted
                        if st.session_state.session_id == session_id:
                            st.session_state.session_id = None
                            st.session_state.messages = []
                            st.session_state.uploaded_document = None
                        st.rerun()
# MAIN PAGE
st.title("🤖 Groq RAG Chatbot")
st.caption("Upload a PDF/DOCX and ask questions about your document.")
# CURRENT SESSION ID
if st.session_state.session_id:
    st.caption(f"Session ID: {st.session_state.session_id}")
# CURRENT DOCUMENT
if st.session_state.uploaded_document:
    st.success(
        f"📄 **Document:** {st.session_state.uploaded_document}"
    )
# DISPLAY CHAT HISTORY
for message in st.session_state.messages:
    role = message.get("role", "assistant")
    content = message.get("content", "")
    with st.chat_message(role):
        st.markdown(content)
# CHAT INPUT
prompt = st.chat_input(
    "Ask something about your document...",
    accept_file=True,
    file_type=["pdf", "docx"]
)
# PROCESS INPUT
if prompt:
    # Get uploaded files
    uploaded_files = prompt.get("files", [])
    # Get text
    prompt_text = prompt.get("text", "").strip()
    # DOCUMENT UPLOAD
    if uploaded_files:
        uploaded_file = uploaded_files[0]
        success = upload_document(uploaded_file)
        if success:
            # Show upload confirmation
            with st.chat_message("assistant"):
                st.success(
                    f"📄 Document uploaded: "
                    f"**{st.session_state.uploaded_document}**"
                )
        # If only file was uploaded
        if not prompt_text:
            st.rerun()
    # SAVE USER MESSAGE LOCALLY
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt_text
        }
    )
    # DISPLAY USER MESSAGE
    with st.chat_message("user"):
        st.markdown(prompt_text)
    # PREPARE BACKEND REQUEST
    payload = {
        "message": prompt_text,
        "session_id": st.session_state.session_id,
        "filename": st.session_state.uploaded_document
    }
    # SEND QUESTION TO BACKEND
    try:
        response = requests.post(
            f"{BACKEND_URL}/ask-conversation",
            json=payload,
            timeout=120
        )
        # Backend error
        if response.status_code != 200:
            st.error(f"Backend error: {response.status_code}")
        else:
            result = response.json()
            # Get answer
            answer = result.get("response", "No response received.")
            # Update session ID
            returned_session_id = result.get("session_id")
            if returned_session_id:
                st.session_state.session_id = returned_session_id
            # Save assistant message
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )
            # Display assistant answer
            with st.chat_message("assistant"):
                st.markdown(answer)
    except requests.exceptions.RequestException as e:
        st.error(f"Could not connect to backend: {e}")