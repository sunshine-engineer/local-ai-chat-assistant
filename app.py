from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import ollama
import streamlit as st 
import os
from dotenv import load_dotenv
load_dotenv()
# from langchain_community.llms import ollama
from langchain_ollama import OllamaLLM

from helpers import (create_chat_session,
                     save_message,
                     load_messages ,
                     get_sessions,
                     rename_chat_session,)


# Variables 
if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []


# Langsmith Tracking
os.environ["LANGCHAIN_API_KEY"]=os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_TRACKING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "QA Chatbot With Ollama"

# Creating a prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant. Please respond to the user queries"),
        ("user","Question:{question}")
    ]
)

@st.cache_resource
def load_llm(engine,temperature,max_tokens):
    return OllamaLLM(model=engine,
               base_url=os.getenv("OLLAMA_HOST"),
               temperature=temperature,
               num_predict=max_tokens,
)

def generate_response(question, engine, temperature, max_tokens):
    llm=load_llm(engine,temperature,max_tokens)
    output_parser = StrOutputParser()
    chain=prompt | llm | output_parser
    answer=chain.invoke({'question': question})
    return answer

st.set_page_config(
    page_title="QA Chatbot",
    page_icon="🤖",
    layout="wide"
)

# Title of the app
st.title("Local AI Assistant")

# Select the Open Source Model 
# Adjust the response parameter
st.sidebar.title("Chats")
llm=st.sidebar.selectbox('Select an Open Source Model', ['phi3:mini'])
temperature = st.sidebar.slider('Temperature', min_value=0.0, max_value=1.0,value=0.7)
max_tokens = st.sidebar.slider("Max Tokens", min_value=50, max_value=300, value=150)



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
user_input=st.chat_input("Ask Anything : ")


# if user_input:
#     response=generate_response(user_input,llm,temperature,max_tokens)
#     st.write(response)
# else:
#     st.write("Please provide the user input")


if user_input:

    if st.session_state.session_id is None:

        st.session_state.session_id = create_chat_session()

    save_message(
        st.session_state.session_id,
        "user",
        user_input
    )

    with st.spinner("Thinking..."):
        response = generate_response(
            user_input,
            llm,
            temperature,
            max_tokens
        )

    save_message(
        st.session_state.session_id,
        "assistant",
        response
    )

    st.session_state.messages = load_messages(
        st.session_state.session_id
    )

    st.rerun()