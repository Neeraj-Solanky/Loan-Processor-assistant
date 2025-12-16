## 📚 AI-Powered Loan Processor Assistant

This project implements an intelligent, automated system designed to streamline the loan processing workflow, integrating modern AI capabilities (LLMs, RAG, Text-to-SQL) with a full-stack Streamlit and MySQL application.

### 🌟 Features

The Loan Processor Assistant provides end-to-end automation and intelligent support for financial loan processing tasks:

  * **Structured Workflow:** A guided, step-by-step workflow for Loan Officers, covering application submission, document verification, income check, and task completion.
  * **AI Chatbot (Text-to-SQL):** A sidebar assistant powered by Groq's LLMs (Gemma2-9b-It) that can translate natural language questions (e.g., "What are my tasks for today?") into executable MySQL queries, providing instant database access.
  * **Document Intelligence (RAG):**
      * Uses **Azure Form Recognizer** to accurately extract key data from uploaded W-2s and Bank Statements.
      * Implements a **Retrieval-Augmented Generation (RAG)** pipeline using **ChromaDB** to allow the AI to answer complex, context-specific questions about the content of uploaded documents.
  * **Automated Verification:**
      * **Missing Documents Check:** Automatically identifies required but missing documents based on `Loan Type` from a checklist.
      * **Income Discrepancy Flagging:** Compares extracted W-2 income against bank deposits and flags any mismatch exceeding a $\\$100 threshold.
  * **Automated Communication:** Automatically generates and sends professional email notifications to applicants regarding missing documents or income discrepancies, accelerating follow-up.

### 💻 Technology Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Frontend/App** | `Streamlit` | Interactive user interface and workflow management. |
| **Backend/DB** | `MySQL` & `SQLAlchemy` | Persistent storage for applicant, task, and checklist data. |
| **LLMs** | `Groq (Mixtral 8x7b, Gemma2-9b-It)` | Text-to-SQL generation and general conversational AI. |
| **Document Processing** | `Azure Form Recognizer` | Data extraction from W-2s and Bank Statements. |
| **Vector Database** | `ChromaDB` | Vector store for the RAG pipeline. |
| **Email Service** | `smtplib` | Sending automated emails (missing docs, discrepancies). |

### 🛠️ Setup and Installation

#### 1\. Prerequisites

  * Python 3.8+
  * MySQL Server (running locally or accessible via `127.0.0.1`)
  * Necessary API Keys (see Step 3)

#### 2\. Environment Setup

1.  **Clone the repository:**

    ```bash
    git clone [Your Repository URL]
    cd [your-project-directory]
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # .\venv\Scripts\activate  # On Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

#### 3\. API and Environment Configuration

Create a file named **`.env`** in the project root directory and populate it with your credentials:

```ini
# Groq API Key for LLM access
GROQ_API_KEY="YOUR_GROQ_API_KEY"

# Azure Form Recognizer (Document Intelligence) Keys
AZURE_FORM_RECOGNIZER_ENDPOINT="YOUR_AZURE_ENDPOINT"
AZURE_FORM_RECOGNIZER_KEY="YOUR_AZURE_KEY"

# Email Configuration (e.g., Gmail App Password)
SENDER_EMAIL="YOUR_SENDER_EMAIL@gmail.com"
EMAIL_PASSWORD="YOUR_EMAIL_APP_PASSWORD" 

# Note: The database credentials are hardcoded in the files 
# (host: 127.0.0.1, user: root, password: neeraj1503, database: loan_processor)
```

#### 4\. Database Setup

1.  Ensure your MySQL server is running.
2.  Log in as root and create the necessary database:
    ```sql
    CREATE DATABASE loan_processor;
    ```
3.  **Run the initial setup function (or relevant setup script)**. The application automatically attempts to create the required tables (`loan_applicants`, `users`) on startup or when the application is first run.
4.  **Populate Initial Data:** Manually insert initial data into the `checklist` and `tasks` tables (if not done via a separate script) for the application to function correctly.

### 🚀 Running the Application

Execute the `main.py` file using Streamlit:

```bash
streamlit run main.py
```

The application will open in your web browser. Start by logging in or signing up via the login screen.

### 📝 File Structure

  * `app2.py`: Main application script handling navigation and component display.
  * `ai_chatbot.py`: Logic for query classification, Text-to-SQL generation, and LLM interaction.
  * `rag.py`: Implements Azure extraction, ChromaDB interaction, and the RAG query logic.
  * `upload_document.py`: Handles document upload, dynamic column creation, and data insertion into `loan_applicants`.
  * `missing_doc.py`: Contains logic for checking missing documents, email generation, and sending.
  * `Income_verifier.py`: Logic for income data extraction and discrepancy checking.
  * `f2.py`: Handles weather API fetching and task display.
  * `login.py`: User authentication and signup logic.
  * `requirements.txt`: List of all Python dependencies.
