import streamlit as st

# Set page config first
st.set_page_config(page_title="Loan Processor Assistant", page_icon="✅")

# Custom login logic
from login import login

# App modules
from f2 import get_weather, fetch_todays_tasks, display_tasks, init_database
from upload_document import add_missing_columns, get_loan_types, get_required_documents
from missing_doc import get_pending_applicants, update_applicant_status, generate_email_message, get_document_checklist, find_missing_documents, send_missing_docs_email
from Income_verifier import analyze_document, extract_bank_deposits, load_env_variables, initialize_clients, send_email
from ai_chatbot import classify_query, generate_sql_query, clean_data
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage

import os
import mysql.connector

# Load environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Ensure login
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login()
    st.stop()

# Initialize LLM and DB
# LLM Model
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=GOOGLE_API_KEY)
db = init_database()

# Sidebar: Chatbot + Logout
with st.sidebar:
    st.markdown(f"👤 **Logged in as:** `{st.session_state.get('full_name', 'Unknown')}`")
    st.markdown("---")

    st.subheader("🤖 Loan Processor Assistant AI")

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            AIMessage(content="👋 Hello! I'm your AI Assistant. You can ask about loans, tasks, or general topics.")
        ]

    # Display conversation history
    for message in st.session_state.chat_history:
        role = "AI" if isinstance(message, AIMessage) else "You"
        st.markdown(f"**{role}:** {message.content}")

    # Temporary input buffer
    if "temp_input" not in st.session_state:
        st.session_state.temp_input = ""

    def process_input():
        if st.session_state.temp_input.strip():
            st.session_state.chat_input = st.session_state.temp_input
            st.session_state.temp_input = ""

    # Input box
    st.text_input("Type your message", key="temp_input", on_change=process_input)

    # Process new input
    if "chat_input" in st.session_state and st.session_state.chat_input:
        user_input = st.session_state.chat_input
        st.session_state.chat_input = ""

        # Prevent duplicate submission
        if len(st.session_state.chat_history) > 0 and st.session_state.chat_history[-1].content == user_input:
            pass
        else:
            st.session_state.chat_history.append(HumanMessage(content=user_input))

            try:
                # Classify the query
                query_type = classify_query(user_input)

                if query_type == "general":
                    # Use LLM for general questions
                    response = llm.invoke(user_input).content
                else:
                    # Generate and run SQL query
                    sql_query = generate_sql_query(query_type)

                    if sql_query:
                        try:
                            response_data = db.run(sql_query)
                            cleaned_data = clean_data(response_data)
                            response = "\n\n".join(cleaned_data) if cleaned_data else "❌ No relevant records found."
                        except Exception as e:
                            response = f"⚠️ Error executing SQL: {str(e)}"
                    else:
                        response = "⚠️ I couldn't generate an SQL query for that request."

            except Exception as e:
                response = f"🚨 Unexpected Error: {str(e)}"

            # Add AI response to history
            st.session_state.chat_history.append(AIMessage(content=response))
            st.markdown(f"**AI:** {response}")

    st.success("💬 Need help? Ask me anything!")
    st.markdown("---")

    # Logout button
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()


# ✅ Page parameters
query_params = st.query_params
step_from_url = query_params.get("step", None)
loan_id_from_url = query_params.get("loan_id", None)

if step_from_url:
    st.session_state["step"] = step_from_url
if loan_id_from_url:
    st.session_state["loan_id"] = loan_id_from_url

if "step" not in st.session_state:
    st.session_state["step"] = "first_screen"
if "chat_enabled" not in st.session_state:
    st.session_state["chat_enabled"] = False

DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "neeraj1503",
    "database": "loan_processor"
}

# ✅ UNIVERSAL HELP REQUEST FUNCTION

def send_help_request(applicant_name, loan_id, stage, processor_email, message_body, supervisor_email, env_vars):
    subject = f"🚩 Assistance Needed: {stage} for Loan ID {loan_id}"
    full_message = f"""
Dear Supervisor,

The loan processor has requested assistance during processing.

- Applicant Name: {applicant_name}
- Loan ID: {loan_id}
- Processing Stage: {stage}
- Processor Email: {processor_email}

Message from Processor:
-------------------------
{message_body}

Please review and provide guidance.

Regards,
Loan Processing Assistant
"""
    return send_email(env_vars["SENDER_EMAIL"], env_vars["EMAIL_PASSWORD"], supervisor_email, subject, full_message)

def show_help_request_ui(stage, applicant_name):
    with st.expander("🚩 Request Help / Escalate Issue"):
        help_message = st.text_area("Describe the issue:", "")
        if st.button("📨 Send Help Request"):
            env_vars = load_env_variables()
            supervisor_email = "neerajsolanky2@gmail.com"  # <-- Replace with supervisor email
            loan_id = st.session_state.get("loan_id", "N/A")
            processor_email = st.session_state.get("email", "processor@example.com")

            status = send_help_request(
                applicant_name, loan_id, stage,
                processor_email, help_message, supervisor_email, env_vars
            )
            if status is True:
                st.success("✅ Help request sent to supervisor!")
            else:
                st.error(f"❌ Failed to send email: {status}")

# ✅ PAGE FUNCTIONS

def show_first_screen():
    st.title("Loan Processing Assistant")
    st.header(f"👋 Good Morning, {st.session_state.get('full_name')}!")
    st.subheader(get_weather())
    st.markdown("---")
    display_tasks(fetch_todays_tasks(db))

    if st.button("Add New Application"):
        st.session_state["step"] = "upload_documents"
        st.session_state["chat_enabled"] = True
        st.rerun()

    show_help_request_ui("Main Dashboard", "N/A")

from PIL import Image
import numpy as np
import cv2

# 🧠 Image quality check functions


def is_not_blurry(image, threshold=30):  # Very relaxed blur check
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    score = cv2.Laplacian(gray, cv2.CV_64F).var()
    return score > threshold  # Accept even soft images

def is_not_noisy(image, threshold=7.0):  # Increased threshold slightly
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist /= hist.sum()
    entropy = -np.sum(hist * np.log2(hist + 1e-7))
    print("Noise Entropy:", entropy)
    return entropy < threshold

def is_properly_aligned(image, min_doc_area_ratio=0.15):  # Accept loosely cropped
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False
    largest = max(contours, key=cv2.contourArea)
    doc_area = cv2.contourArea(largest)
    image_area = image.shape[0] * image.shape[1]
    return (doc_area / image_area) > min_doc_area_ratio

def is_valid_image(uploaded_file):
    try:
        image = Image.open(uploaded_file).convert("RGB")
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        blurry = is_not_blurry(cv_image)
        aligned = is_properly_aligned(cv_image)

        # You can print for debugging if needed
        print(f"Blur OK: {blurry}, Cropping OK: {aligned}")
        return blurry and aligned
    except Exception as e:
        print("Validation Error:", e)
        return False



# ✅ Updated Upload Function

def upload_documents():
    st.subheader("Upload Loan Documents")
    st.write(f"📄 Working on loan ID: {st.session_state.get('loan_id', 'N/A')}")

    loan_id = st.session_state.get("loan_id")
    applicant_name = ""
    email = ""
    loan_type = ""
    error_in_upload = False
    uploaded_files = {}

    if loan_id:
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT `Borrower_Name`, `Email`, `Loan_Type` FROM tasks WHERE loan_id = %s", (loan_id,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                applicant_name = result["Borrower_Name"]
                email = result["Email"]
                loan_type = result["Loan_Type"]

        except mysql.connector.Error as err:
            st.warning(f"⚠️ Could not fetch applicant data for loan ID {loan_id}: {err}")

    st.write(f"👤 Applicant Name: `{applicant_name or 'Not found'}`")
    st.write(f"📧 Email: `{email or 'Not found'}`")
    st.write(f"📌 Loan Type: `{loan_type or 'Not found'}`")

    if loan_type:
        required_docs = get_required_documents(loan_type)

        for doc in required_docs:
            uploaded_file = st.file_uploader(f"Upload {doc}", type=["pdf", "jpg", "png"], key=doc)
            file_data = None

            if uploaded_file:
                if uploaded_file.type in ["image/jpeg", "image/png"]:
                    if not is_valid_image(uploaded_file):
                        st.warning(f"❌ The uploaded {doc} is blurry, noisy, or improperly cropped. Please re-upload.")
                        error_in_upload = True
                        continue
                    file_data = uploaded_file.read()

                elif uploaded_file.type == "application/pdf":
                    file_data = uploaded_file.read()

                else:
                    st.warning(f"{doc}: Unsupported file type.")
                    error_in_upload = True

                uploaded_files[doc] = file_data
            else:
                uploaded_files[doc] = None

        if st.button("Submit Application"):
            if error_in_upload:
                st.error("❌ Some documents were not accepted due to quality issues.")
                return

            if not applicant_name or not email or not uploaded_files:
                st.error("❌ Missing applicant info or documents. Cannot submit.")
                return

            add_missing_columns(uploaded_files.keys())

            try:
                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
                columns = ', '.join([f'`{col}`' for col in uploaded_files.keys()])
                placeholders = ', '.join(['%s'] * len(uploaded_files))
                sql = f"""
                    INSERT INTO loan_applicants 
                    (`Applicant Name`, `Email`, `Loan Type`, {columns}, `Status`) 
                    VALUES (%s, %s, %s, {placeholders}, 'Pending')
                """
                cursor.execute(sql, (applicant_name, email, loan_type, *uploaded_files.values()))
                conn.commit()
                cursor.close()
                conn.close()

                # ✅ Update task status
                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
                cursor.execute("UPDATE tasks SET status = %s WHERE loan_id = %s", ("Pending", loan_id))
                conn.commit()
                cursor.close()
                conn.close()

                st.success("✅ Application submitted successfully! Status: Pending.")

            except mysql.connector.Error as err:
                st.error(f"❌ Database Error: {err}")

    if st.button("Missing Documents Check"):
        st.session_state["step"] = "missing_docs"
        st.rerun()

    if st.button("✅ Sent to underWriter"):
        st.session_state["step"] = "task_completed"
        st.rerun()

    show_help_request_ui("Upload Documents", applicant_name)


def check_missing_documents():
    st.subheader("Check Missing Documents")
    st.write(f"📄 Working on loan ID: {st.session_state.get('loan_id', 'N/A')}")
    loan_id = st.session_state.get("loan_id")
    applicant_name = ""
    email = ""
    loan_type = ""

    # 🔍 Fetch applicant info from tasks table using loan_id
    if loan_id:
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT `Borrower_Name`, `Email`, `Loan_Type` FROM tasks WHERE loan_id = %s", (loan_id,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                applicant_name = result["Borrower_Name"]
                email = result["Email"]
                loan_type = result["Loan_Type"]
        except mysql.connector.Error as err:
            st.warning(f"⚠️ Could not fetch applicant data for loan ID {loan_id}: {err}")

    st.write(f"👤 Applicant Name: `{applicant_name or 'Not found'}`")
    st.write(f"📧 Email: `{email or 'Not found'}`")
    st.write(f"📌 Loan Type: `{loan_type or 'Not found'}`")

    # 📋 Get document checklist and pending applicants
    document_checklist = get_document_checklist()
    applicants = get_pending_applicants()

    # ✅ Handle no pending applicants
    if not applicants:
        st.success("🎉 No more pending applicants! Click below to proceed.")
        if st.button("Proceed to Income Verification"):
            st.session_state["step"] = "income_verification"
            st.rerun()
        return

    # ✅ Work on the first pending applicant
    applicant = applicants[0]

    missing_docs = find_missing_documents(applicant, document_checklist)

    if missing_docs:
        st.write("### Missing Documents:")
        for doc in missing_docs:
            st.write(f"- {doc}")

        email_body = generate_email_message(applicant["Applicant Name"], missing_docs)
        edited_email = st.text_area("✏️ Edit Email Before Sending:", email_body, height=250)

        if st.button("📧 Send Email"):
            send_missing_docs_email(applicant["Email"], edited_email)
            update_applicant_status(applicant["id"], "Waiting for Applicant Response")
            st.success("📨 Email Sent!")

    else:
        st.success("✅ All required documents are available.")

    if st.button("Upload Missing Documents"):
        st.session_state["step"] = "upload_documents"
        st.session_state["chat_enabled"] = True
        st.rerun()

    if st.button("✅ Sent to underWriter"):
        st.session_state["step"] = "task_completed"
        st.rerun()

    show_help_request_ui("Missing Documents Check", applicant["Applicant Name"])

def income_verification():
    st.subheader("📂 Income Verification")
    st.write(f"📄 Working on loan ID: {st.session_state.get('loan_id', 'N/A')}")
    w2_file = st.file_uploader("📑 Upload W-2 Form", type=["pdf"])
    bank_statement = st.file_uploader("🏦 Upload Bank Statement", type=["pdf"])

    if w2_file and bank_statement:
        env_vars = load_env_variables()
        document_client, _ = initialize_clients(env_vars)

        w2_data = analyze_document(w2_file, document_client)
        bank_data = analyze_document(bank_statement, document_client)

        if w2_data and bank_data:
            wages = float(w2_data.get("1 Wages, tips, other compensation", "0").replace("$", "").replace(",", ""))
            bank_deposits = extract_bank_deposits(bank_data)

            st.write(f"💰 **W-2 Income:** ${wages:.2f}")
            st.write(f"🏦 **Bank Deposits:** ${bank_deposits:.2f}")

            discrepancy_threshold = 100
            if abs(wages - bank_deposits) > discrepancy_threshold:
                st.warning("⚠️ **Income Mismatch Detected!**")
                recipient_email = st.text_input("📧 Enter applicant email")
                email_body = f"""
Subject: Income Discrepancy Alert

Dear Applicant,

We have identified an income discrepancy in your loan application.

- **W-2 Income:** ${wages:.2f}
- **Bank Deposits:** ${bank_deposits:.2f}

Please verify your documents and provide clarification.

Regards,  
Loan Processing Team
"""
                edited_email_body = st.text_area("✏️ Edit Email Before Sending:", value=email_body, height=250)

                if recipient_email and st.button("📨 Send Email"):
                    status = send_email(env_vars["SENDER_EMAIL"], env_vars["EMAIL_PASSWORD"], recipient_email, "Income Discrepancy Alert", edited_email_body)
                    if status is True:
                        st.success(f"✅ Email sent to {recipient_email}")
                    else:
                        st.error(f"🚨 Failed to send email: {status}")

            if st.button("✅ Sent to underWriter"):
                st.session_state["step"] = "task_completed"
                st.rerun()

    show_help_request_ui("Income Verification", "N/A")

def show_task_completed():
    st.title("🎉 Congratulations!")
    st.subheader("You've successfully completed all your tasks for today! 🚀")
    st.markdown("""
**Great work!** Your efforts have paid off — all documents and data have been successfully sent to the underwriter for review. 📤
Take a well-deserved break and come back refreshed tomorrow — you're one step closer to success! 🌟
""")
    if st.button("🏠 Home"):
        st.session_state["step"] = "first_screen"
        st.rerun()

# ✅ FINAL PAGE NAVIGATION CONTROLLER
if st.session_state["step"] == "first_screen":
    show_first_screen()
elif st.session_state["step"] == "upload_documents":
    upload_documents()
elif st.session_state["step"] == "missing_docs":
    check_missing_documents()
elif st.session_state["step"] == "income_verification":
    income_verification()
elif st.session_state["step"] == "task_completed":
    show_task_completed()
