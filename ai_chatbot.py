import os
import streamlit as st
import time
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI # Using Groq instead of OpenAI
from langchain_community.utilities import SQLDatabase
import pandas as pd

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY=os.getenv("GROQ_API_KEY")
# MySQL Database Configuration
DB_HOST = "127.0.0.1"
DB_USER = "root"
DB_PASSWORD = "neeraj1503"
DB_NAME = "loan_processor"

# Initialize database connection
def init_database():
    db_uri = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    return SQLDatabase.from_uri(db_uri)

db = init_database()

# LLM Model
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2, google_api_key=GOOGLE_API_KEY)
# LLM Model
# from langchain_groq import ChatGroq
# llm = ChatGroq(model_name="mixtral-8x7b-32768", temperature=0.2, api_key=GROQ_API_KEY)

# Function to classify query type (loan-related, task-related, or general)
def classify_query(user_query):
    loan_keywords = ["loan", "interest rate", "repayment", "mortgage", "loan status"]
    task_keywords = ["task", "today's tasks", "completion time", "pending tasks"]

    if any(word in user_query.lower() for word in loan_keywords):
        return "loan"
    elif any(word in user_query.lower() for word in task_keywords):
        return "task"
    else:
        return "general"

# Function to generate SQL query based on query type
def generate_sql_query(query_type):
    if query_type == "task":
        return "SELECT task_name, status FROM tasks WHERE DATE(due_date) = CURDATE();"
    elif query_type == "loan":
        return "SELECT task_name, status FROM tasks WHERE status = 'Due Today' LIMIT 10;"
    else:
        return None

# Streamlit UI
st.title("🤖 Loan Processor Assistant")

# Chat History in Session State
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        AIMessage(content="👋 Welcome! I'm your Loan Processor AI Assistant. I can help you with loan applications, task updates, or general queries. How can I assist you today?")
    ]

# Display Chat History
for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.markdown(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.markdown(message.content)

# Function to Clean and Format SQL Query Results
def clean_data(response_data):
    if isinstance(response_data, str):
        response_data = eval(response_data)  # Convert string result to tuple list

    if isinstance(response_data, list):
        clean_result = []
        for item in response_data:
            if isinstance(item, tuple):
                task_name = item[0] if len(item) > 0 else "Unknown Task"
                status = item[1] if len(item) > 1 else "Unknown Status"
                clean_result.append(f"✅ **{task_name}** - {status}")
        return clean_result
    return ["⚠️ Unexpected data format"]

# User Input
user_query = st.chat_input("Ask me about loans, tasks, or general questions...")
if user_query and user_query.strip():
    user_query = ' '.join(user_query.split())  # Remove unnecessary spaces/newlines

    # Add Human Message to Chat
    st.session_state.chat_history.append(HumanMessage(content=user_query))
    with st.chat_message("Human"):
        st.markdown(user_query)

    # Simulate AI Thinking Effect
    with st.chat_message("AI"):
        message_placeholder = st.empty()
        for dot in ["", ".", "..", "..."]:
            message_placeholder.markdown(f"🤔 Thinking{dot}")
            time.sleep(0.5)

    # Classify query type
    query_type = classify_query(user_query)

    if query_type == "general":
        response = llm.invoke(user_query).content  # LLM handles general queries
    else:
        # Generate SQL query
        sql_query = generate_sql_query(query_type)

        # Execute query and fetch results
        if sql_query:
            try:
                response_data = db.run(sql_query)
                cleaned_data = clean_data(response_data)
                response = "\n\n".join(cleaned_data) if cleaned_data else "❌ No tasks found for today. Want to add a new task?"
            except Exception as e:
                response = f"⚠️ Error retrieving tasks: {str(e)}"
        else:
            response = "⚠️ I couldn't generate an SQL query for that request."

    # Display AI Response
    with st.chat_message("AI"):
        st.markdown(response)

    # Store the response in chat history
    st.session_state.chat_history.append(AIMessage(content=response))