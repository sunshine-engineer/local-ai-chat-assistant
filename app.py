"""Streamlit entry point for local chat and explicit job-application commands.

File: app.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import streamlit as st
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM

from assistant.config import setting
from assistant.review_ui import render_comparison_review
from assistant.runtime import build_registry

# Creating a prompt template
CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant. Please respond to the user queries"),
        ("user", "Question:{question}"),
    ]
)


@st.cache_resource
def load_llm(engine, temperature, max_tokens):
    """Create or reuse the selected local chat model.

    Args:
        engine: Installed Ollama model name selected for chat.
        temperature: Ordinary-chat sampling temperature.
        max_tokens: Ordinary-chat output-token budget.

    Returns:
        Cached local Ollama chat model.
    """
    return OllamaLLM(
        model=engine,
        reasoning=False,
        base_url=setting("ollama", "host", "OLLAMA_HOST"),
        temperature=temperature,
        num_predict=max_tokens,
    )


def generate_response(question, engine, temperature, max_tokens):
    """Route explicit commands before invoking ordinary local chat.

    Args:
        question: User text, including any explicit slash command.
        engine: Installed Ollama model name selected for chat.
        temperature: Ordinary-chat sampling temperature.
        max_tokens: Ordinary-chat output-token budget.

    Returns:
        Command result or ordinary-chat response/failure guidance.
    """
    command_result = build_registry().execute(question)
    if command_result is not None:
        return command_result
    llm = load_llm(engine, temperature, max_tokens)
    output_parser = StrOutputParser()
    chain = CHAT_PROMPT | llm | output_parser
    try:
        return chain.invoke({"question": question})
    except Exception:
        return "Local model unavailable. Check Ollama, OLLAMA_HOST and the installed model; /help lists available commands."


def main():
    """Render the Streamlit application after loading environment settings."""
    load_dotenv()
    # Import persistence after .env is loaded; importing helpers initializes its database.
    from helpers import create_chat_session, get_sessions, load_messages, save_message

    # Variables
    if "session_id" not in st.session_state:
        st.session_state.session_id = None

    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.set_page_config(page_title="QA Chatbot", page_icon="🤖", layout="wide")

    # Title of the app
    st.title("Local AI Assistant")

    render_comparison_review()

    # Select the Open Source Model
    # Adjust the response parameter
    st.sidebar.title("Chats")
    llm = st.sidebar.selectbox(
        "Select an Open Source Model", [setting("ollama", "model", "OLLAMA_MODEL")]
    )
    temperature = st.sidebar.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=setting("chat", "temperature", "CHAT_TEMPERATURE"),
    )
    max_tokens = st.sidebar.slider(
        "Max Tokens",
        min_value=50,
        max_value=300,
        value=setting("chat", "max_tokens", "CHAT_MAX_TOKENS"),
    )

    if st.sidebar.button("➕ New Chat"):
        st.session_state.session_id = create_chat_session()
        st.session_state.messages = []
        st.rerun()

    sessions = get_sessions()
    if not sessions:
        st.sidebar.info("No chats yet. Create one!")

    for chat in sessions:
        if st.sidebar.button(chat.title, key=chat.id):
            st.session_state.session_id = chat.id
            st.session_state.messages = load_messages(chat.id)
            st.rerun()

    for msg in st.session_state.messages:
        with st.chat_message(msg.role):
            st.markdown(msg.message)

    # Main interface for the user input
    st.write("Ask any question")
    user_input = st.chat_input("Ask Anything : ")

    if user_input:
        if st.session_state.session_id is None:
            st.session_state.session_id = create_chat_session()

        save_message(st.session_state.session_id, "user", user_input)

        with st.spinner("Thinking..."):
            response = generate_response(user_input, llm, temperature, max_tokens)

        save_message(st.session_state.session_id, "assistant", response)

        st.session_state.messages = load_messages(st.session_state.session_id)

        st.rerun()


if __name__ == "__main__":
    main()
