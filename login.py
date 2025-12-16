# login.py
import streamlit as st
import mysql.connector

def get_user_credentials(username):
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="neeraj1503",
        database="loan_processor"
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

# login.py

import streamlit as st
import mysql.connector

DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "neeraj1503",
    "database": "loan_processor"
}

# Connect to DB and fetch user info
def get_user_credentials(username):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

# Add new user to the database
def create_user(username, password, full_name):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, password, full_name) VALUES (%s, %s, %s)",
                   (username, password, full_name))
    conn.commit()
    cursor.close()
    conn.close()

def login():
    st.title("🔐 Loan Officer Login / Signup")

    mode = st.radio("Select Mode", ["Login", "Signup"])

    if mode == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            user = get_user_credentials(username)
            if user and user["password"] == password:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["full_name"] = user["full_name"]
                st.success(f"✅ Welcome {user['full_name']}!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")

    elif mode == "Signup":
        full_name = st.text_input("Full Name")
        new_username = st.text_input("Choose a Username")
        new_password = st.text_input("Choose a Password", type="password")

        if st.button("Create Account"):
            if not full_name or not new_username or not new_password:
                st.error("❌ All fields are required.")
                return

            if get_user_credentials(new_username):
                st.error("⚠️ Username already taken. Try a different one.")
            else:
                create_user(new_username, new_password, full_name)
                st.success("🎉 Account created successfully! You can now log in.")

