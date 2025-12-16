import streamlit as st
import mysql.connector
import cv2
import numpy as np
from PIL import Image
import io

# MySQL Database Configuration
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "neeraj1503",
    "database": "loan_processor"
}

# ========== Quality Checks ==========

def is_not_blurry(image, threshold=100):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    score = cv2.Laplacian(gray, cv2.CV_64F).var()
    return score > threshold

def is_not_noisy(image, threshold=7.5):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist_norm = hist.ravel() / hist.sum()
    entropy = -np.sum(hist_norm * np.log2(hist_norm + 1e-7))
    return entropy < threshold

def is_properly_aligned(image, min_doc_area_ratio=0.5):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False
    largest = max(contours, key=cv2.contourArea)
    doc_area = cv2.contourArea(largest)
    image_area = image.shape[0] * image.shape[1]
    return (doc_area / image_area) > min_doc_area_ratio

def is_valid_image(file):
    try:
        image = Image.open(file).convert("RGB")
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        return (
            is_not_blurry(cv_image)
            and is_not_noisy(cv_image)
            and is_properly_aligned(cv_image)
        )
    except:
        return False

# ========== Database Operations ==========

def create_loan_applicants_table():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loan_applicants (
            id INT AUTO_INCREMENT PRIMARY KEY,
            `Applicant Name` VARCHAR(255) NOT NULL,
            `Email` VARCHAR(255) NOT NULL,
            `Loan Type` VARCHAR(100) NOT NULL,
            `Status` VARCHAR(50) DEFAULT 'Pending'
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def get_existing_columns():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SHOW COLUMNS FROM loan_applicants")
    existing_columns = {row[0] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    return existing_columns

def add_missing_columns(columns):
    existing_columns = get_existing_columns()
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    for column in columns:
        if column not in existing_columns:
            cursor.execute(f"ALTER TABLE loan_applicants ADD COLUMN `{column}` LONGBLOB NULL")
    conn.commit()
    cursor.close()
    conn.close()

def get_loan_types():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT `Loan Type` FROM checklist")
    loan_types = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return loan_types

def get_required_documents(loan_type):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT `Documents Required` FROM checklist WHERE `Loan Type` = %s", (loan_type,))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    required_docs = []
    for row in results:
        required_docs.extend(row[0].split(', '))
    return list(set(required_docs))

# ========== Streamlit UI ==========

create_loan_applicants_table()

st.title("📄 Loan Application Document Upload")
applicant_name = st.text_input("Applicant Name")
email = st.text_input("Email")

loan_types = get_loan_types()
loan_type = st.selectbox("Select Loan Type", loan_types)

if loan_type:
    required_docs = get_required_documents(loan_type)
    uploaded_files = {}

    for doc in required_docs:
        uploaded_file = st.file_uploader(f"Upload {doc}", type=["pdf", "jpg", "png"], key=doc)

        if uploaded_file:
            if uploaded_file.type in ["image/jpeg", "image/png"]:
                if is_valid_image(uploaded_file):
                    uploaded_files[doc] = uploaded_file.read()
                else:
                    st.error(f"❌ {doc} image is blurry, noisy, or improperly cropped. Please re-upload.")
            else:
                uploaded_files[doc] = uploaded_file.read()

    if st.button("Submit Application"):
        if len(uploaded_files) != len(required_docs):
            st.warning("⚠️ Please upload all required valid documents before submitting.")
        else:
            add_missing_columns(uploaded_files.keys())
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
            st.success("✅ Application submitted successfully! Status: Pending")
