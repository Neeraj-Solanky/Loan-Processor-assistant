import os
import smtplib
import streamlit as st
from dotenv import load_dotenv
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import chromadb
import uuid
import re

def load_env_variables():
    load_dotenv()
    return {
        "AZURE_ENDPOINT": os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT"),
        "AZURE_KEY": os.getenv("AZURE_FORM_RECOGNIZER_KEY"),
        "EMAIL_PASSWORD": os.getenv("EMAIL_PASSWORD"),
        "SENDER_EMAIL": os.getenv("SENDER_EMAIL")
    }

def initialize_clients(env_vars):
    document_client = DocumentAnalysisClient(
        endpoint=env_vars["AZURE_ENDPOINT"],
        credential=AzureKeyCredential(env_vars["AZURE_KEY"])
    )
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    try:
        document_collection = chroma_client.get_collection(name="income_verification")
    except:
        document_collection = chroma_client.create_collection(name="income_verification")
    return document_client, document_collection

def analyze_document(file, document_client):
    file_bytes = file.read()
    poller = document_client.begin_analyze_document("prebuilt-document", document=file_bytes)
    result = poller.result()
    return {kv.key.content.strip(): kv.value.content.strip() for kv in result.key_value_pairs if kv.key and kv.value} or None

def extract_bank_deposits(bank_data):
    deposit_amounts = re.findall(r"\$(\d+[,\d]*)", str(bank_data))
    return sum(float(amount.replace(",", "")) for amount in deposit_amounts)

def store_in_chromadb(document_collection, applicant_name, wages, bank_deposits):
    unique_id = str(uuid.uuid4())
    document_collection.add(
        documents=[f"W-2 Income: {wages}, Bank Deposits: {bank_deposits}"],
        metadatas=[{
            "applicant_name": applicant_name,
            "w2_income": wages,
            "bank_deposits": bank_deposits,
            "status": "Pending"
        }],
        ids=[unique_id]
    )

def send_email(sender_email, email_password, recipient_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, email_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        return str(e)

def display_results(applicant_name, wages, bank_deposits):
    st.write(f"👤 **Applicant Name:** {applicant_name}")
    st.write(f"💰 **W-2 Income:** ${wages:.2f}")
    st.write(f"🏦 **Bank Deposits:** ${bank_deposits:.2f}")
    if abs(wages - bank_deposits) > 100:
        st.warning("⚠️ **Income Mismatch Detected!**")

def main():
    env_vars = load_env_variables()
    document_client, document_collection = initialize_clients(env_vars)
    
    st.title("📂 Loan Document Assistant")
    st.write("Upload W-2 Form and Bank Statement for income verification.")
    
    w2_file = st.file_uploader("📂 Upload W-2 Form (PDF/Image)", type=["pdf", "jpg", "jpeg", "png"])
    bank_statement = st.file_uploader("📂 Upload Bank Statement (PDF/Image)", type=["pdf", "jpg", "jpeg", "png"])
    
    if st.button("Verify Income"):
        if not w2_file or not bank_statement:
            st.error("🚨 Please upload both documents.")
            return
        
        st.write("🔍 **Processing... Please wait.**")
        w2_data = analyze_document(w2_file, document_client)
        bank_data = analyze_document(bank_statement, document_client)
        
        if not w2_data or not bank_data:
            st.error("🚨 Failed to extract data. Please check files.")
            return
        
        applicant_name = w2_data.get("Employee's first name") or "Unknown"
        wages = float(w2_data.get("1 Wages, tips, other compensation", "0").replace("$", "").replace(",", ""))
        bank_deposits = extract_bank_deposits(bank_data)
        
        store_in_chromadb(document_collection, applicant_name, wages, bank_deposits)
        st.session_state.update({
            "applicant_name": applicant_name,
            "wages": wages,
            "bank_deposits": bank_deposits,
            "income_verified": True
        })
        
        st.success("✅ Income Verification Completed!")
    
    if "income_verified" in st.session_state:
        display_results(
            st.session_state["applicant_name"], 
            st.session_state["wages"], 
            st.session_state["bank_deposits"]
        )
        
        if abs(st.session_state["wages"] - st.session_state["bank_deposits"]) > 100:
            recipient_email = st.text_input("📧 Enter applicant email")
            email_body = f"""
            Subject: Income Discrepancy Alert
            
            Dear {st.session_state["applicant_name"]},
            
            We have identified an income discrepancy.
            - **W-2 Income:** ${st.session_state["wages"]:.2f}
            - **Bank Deposits:** ${st.session_state["bank_deposits"]:.2f}
            
            Please confirm before proceeding.
            Regards, Loan Verification Team
            """
            edited_email_body = st.text_area("✏️ Edit Email Before Sending:", value=email_body, height=250)
            if recipient_email and st.button("Send Email"):
                status = send_email(env_vars["SENDER_EMAIL"], env_vars["EMAIL_PASSWORD"], recipient_email, "Income Discrepancy Alert", edited_email_body)
                if status is True:
                    st.success(f"✅ Email sent to {recipient_email}")
                else:
                    st.error(f"🚨 Failed to send email: {status}")
    
if __name__ == "__main__":
    main()
