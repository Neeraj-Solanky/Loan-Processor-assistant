import streamlit as st
import mysql.connector
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
load_dotenv()
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD")

if not SENDER_PASSWORD:
    st.error("❌ EMAIL_PASSWORD not found! Make sure it's set in the .env file.")
    st.stop()

# MySQL Database Configuration
DB_HOST = "127.0.0.1"
DB_USER = "root"
DB_PASSWORD = "neeraj1503"
DB_NAME = "loan_processor"

# Connect to MySQL
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# Fetch checklist data
def get_document_checklist():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT `Loan Type`, `Documents Required` FROM checklist")
    checklist_data = cursor.fetchall()
    cursor.close()
    conn.close()

    document_checklist = {}
    for row in checklist_data:
        loan_type = row["Loan Type"]
        document = row["Documents Required"]
        if loan_type not in document_checklist:
            document_checklist[loan_type] = []
        document_checklist[loan_type].append(document)
    
    return document_checklist

# Fetch pending loan applicants
def get_pending_applicants():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM loan_applicants WHERE Status IS NULL OR Status = 'Pending'")
    applicants = cursor.fetchall()
    cursor.close()
    conn.close()
    return applicants

# Find missing documents for an applicant
def find_missing_documents(applicant, checklist):
    loan_type = applicant["Loan Type"]
    required_docs = checklist.get(loan_type, [])

    missing_docs = []
    for doc in required_docs:
        doc_status = applicant.get(doc)
        
        # Check if the document BLOB is empty
        if doc_status is None or len(doc_status) == 0:
            missing_docs.append(doc)
    
    return missing_docs

# Generate email content
def generate_email_message(applicant_name, missing_docs):
    doc_list = "\n".join([f"- {doc}" for doc in missing_docs])
    return f"""
Dear {applicant_name},

We are processing your loan application and noticed that the following required documents are missing:

{doc_list}

Please submit these documents by next week to avoid delays in your application process.

If you have any questions, feel free to contact us at 678-901-2345.

Best regards,  
Loan Processing Team  
[Your Company Name]
    """

# Send email
def send_missing_docs_email(recipient_email, email_body):
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient_email
        msg["Subject"] = "Urgent: Missing Documents for Loan Verification"
        msg.attach(MIMEText(email_body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())

        logging.info(f"✅ Email sent to {recipient_email}")
        return True
    except Exception as e:
        logging.error(f"❌ Error sending email to {recipient_email}: {e}")
        return False

# Update applicant status or insert if not exists
def update_applicant_status(applicant_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE loan_applicants SET Status = %s WHERE id = %s", (status, applicant_id))
    conn.commit()
    cursor.close()
    conn.close()

# Streamlit UI
st.title("Loan Document Verification System")

document_checklist = get_document_checklist()
applicants = get_pending_applicants()

if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "email_sent" not in st.session_state:
    st.session_state.email_sent = False  # Track email sent status

if st.session_state.current_index < len(applicants):
    applicant = applicants[st.session_state.current_index]
    missing_docs = find_missing_documents(applicant, document_checklist)
    
    st.subheader(f"Applicant: {applicant['Applicant Name']}")
    st.write(f"Email: {applicant['Email']}")
    st.write(f"Loan Type: {applicant['Loan Type']}")

    if missing_docs:
        st.write("### Missing Documents:")
        for doc in missing_docs:
            st.write(f"- {doc}")

        email_body = generate_email_message(applicant["Applicant Name"], missing_docs)
        edited_email = st.text_area("Edit Email Before Sending:", email_body, height=250)

        if st.button("Send Email"):
            email_sent = send_missing_docs_email(applicant["Email"], edited_email)
            if email_sent:
                update_applicant_status(applicant["id"], "Waiting for Applicant Response")
                st.session_state.email_sent = True
                st.success("📧 Email sent successfully!")

    else:
        st.success("✅ All documents are submitted.")
        if st.button("Mark as Verified"):
            update_applicant_status(applicant["id"], "Verified")
            st.success("Applicant status updated to Verified!")
            st.session_state.email_sent = True

    # Navigation buttons (Previous, Next, Hold)
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.session_state.current_index > 0:
            if st.button("⬅ Previous Applicant"):
                st.session_state.current_index -= 1
                st.session_state.email_sent = False
                st.rerun()

    with col2:
        if st.session_state.current_index < len(applicants) - 1:
            if st.button("➡ Next Applicant"):
                st.session_state.current_index += 1
                st.session_state.email_sent = False
                st.rerun()

    with col3:
        if st.button("Hold"):
            update_applicant_status(applicant["id"], "Hold")
            st.success("Applicant status changed to Hold!")
            st.session_state.email_sent = True

else:
    st.write("🎉 No more pending applicants!")
