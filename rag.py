import os
import time
import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
import chromadb
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AZURE_FORM_KEY = os.getenv("AZURE_FORM_RECOGNIZER_KEY")
AZURE_FORM_ENDPOINT = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")

# Database Configuration
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "neeraj1503",
    "database": "loan_processor"
}

# Initialize MySQL Database
def init_database():
    try:
        db_uri = f"mysql+mysqlconnector://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
        return SQLDatabase.from_uri(db_uri)
    except Exception as e:
        st.error(f"❌ Database Connection Failed: {e}")
        return None

db = init_database()

# Initialize LLM
def init_llm():
    try:
        return ChatGroq(model_name="mixtral-8x7b-32768", temperature=0, api_key=GROQ_API_KEY)
    except Exception as e:
        st.error(f"❌ LLM Initialization Failed: {e}")
        return None

llm = init_llm()

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="chroma_db")
doc_collection = chroma_client.get_or_create_collection(name="loan_docs")

# Extract text from documents using Azure Form Recognizer
def extract_text_from_document(file_path):
    """
    Extracts text from a loan document using Azure Form Recognizer.
    """
    print(f"📄 Processing document: {file_path}")  # ✅ Debugging

    try:
        with open(file_path, "rb") as file:
            poller = document_client.begin_analyze_document("prebuilt-document", document=file)  
            result = poller.result()

        # ✅ Debug: Check if Azure returns any response
        if result is None:
            print("🚨 Azure Form Recognizer returned None. Check API Key and Endpoint.")
            return "⚠️ No response from Azure Form Recognizer. Please check API configuration."

        # ✅ Debug: Print Azure's raw response for deeper insights
        print(f"🔍 Raw Azure Response: {result}")

        if not hasattr(result, "pages") or not result.pages:
            print(f"🚨 Azure returned no text for {file_path}. Possibly an image-based PDF?")
            return "⚠️ No readable text found in the document. Try uploading a text-based PDF."

        extracted_text = "\n".join([line.content for page in result.pages for line in page.lines])

        if not extracted_text.strip():
            print(f"🚨 Extracted text is empty for {file_path}.")
            return "⚠️ Extracted text is empty. The document may not contain recognizable text."

        print(f"✅ Extracted Text Sample: {extracted_text[:500]}")  # ✅ Print first 500 characters for debugging
        return extracted_text

    except Exception as e:
        print(f"🚨 Azure Form Recognizer Error: {e}")
        return f"⚠️ Document processing failed: {e}"



# Store extracted text in ChromaDB
def add_document_to_chroma(file_path, doc_id):
    extracted_text = extract_text_from_document(file_path)
    if extracted_text:
        doc_collection.add(documents=[extracted_text], ids=[doc_id])

# Retrieve relevant docs from ChromaDB
def retrieve_relevant_docs(query):
    results = doc_collection.query(query_texts=[query], n_results=3)
    return "\n\n".join(results["documents"][0]) if results["documents"] else ""

# Retrieve relevant schema dynamically
def get_relevant_schema(user_query):
    try:
        full_schema = db.get_table_info()
        relevant_tables = []
        for table in full_schema.split("\n\n"):  # Splitting tables
            if any(keyword in table.lower() for keyword in user_query.lower().split()):
                relevant_tables.append(table)
        return "\n\n".join(relevant_tables) if relevant_tables else full_schema[:2000]  # Limit schema size
    except Exception as e:
        return f"⚠️ Failed to retrieve schema: {e}"

# Generate SQL query dynamically with token optimization
def generate_dynamic_sql(user_query):
    schema = get_relevant_schema(user_query)
    
    prompt = f"""
    You are an expert MySQL assistant. Based on the following database schema (truncated if necessary):
    {schema[:2000]}  
    Generate an optimized SQL query to answer this question:
    {user_query}
    Return only the SQL query, without any additional text.
    """
    
    try:
        start_time = time.time()
        response = llm.invoke(prompt).content.strip()[:1000]  # Limit response size
        if time.time() - start_time > 10:  # Timeout after 10 seconds
            return "⚠️ API took too long. Try again."
        return response
    except Exception as e:
        return f"⚠️ LLM Error: {e}"

# Execute SQL query
def execute_query(sql_query):
    try:
        st.write(f"🔍 Executing Query: `{sql_query}`")  # Debugging
        results = db.run(sql_query)
        return results[:10]  # Limit results
    except Exception as e:
        return f"⚠️ Error retrieving data: {str(e)}"

# Process user query
def process_user_query(user_query):
    sql_query = generate_dynamic_sql(user_query)
    
    if not sql_query:
        return "⚠️ Could not generate an SQL query for your question."

    response_data = execute_query(sql_query)
    
    if isinstance(response_data, str):  # If error message
        return response_data
    
    return "\n\n".join([f"✅ **{row[0]}** - {row[1]}" for row in response_data]) if response_data else "❌ No records found."

# Streamlit UI

st.title("🤖 AI Loan & Database Assistant")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "AI", "content": "👋 Hello! Ask me anything about loans, tasks, or database queries."}
    ]

# Display chat history
for message in st.session_state.chat_history:
    with st.chat_message("AI" if message["role"] == "AI" else "Human"):
        st.markdown(message["content"])

# User query input
user_query = st.chat_input("Ask me about loans, tasks, or database queries...")

if user_query:
    st.session_state.chat_history.append({"role": "Human", "content": user_query})
    with st.chat_message("Human"):
        st.markdown(user_query)

    with st.chat_message("AI"):
        response = process_user_query(user_query)
        st.markdown(response)
        st.session_state.chat_history.append({"role": "AI", "content": response})

# File upload for document analysis
uploaded_file = st.file_uploader("Upload a document for analysis", type=["pdf", "jpg", "png"])

if uploaded_file:
    file_path = f"temp_{uploaded_file.name}"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    add_document_to_chroma(file_path, uploaded_file.name)
    st.success("✅ Document uploaded and processed successfully!")
