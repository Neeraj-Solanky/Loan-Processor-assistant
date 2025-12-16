import os
import streamlit as st
import requests
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase

# Load environment variables
load_dotenv()

# MySQL Database Configuration
DB_HOST = "127.0.0.1"
DB_USER = "root"
DB_PASSWORD = "neeraj1503"
DB_NAME = "loan_processor"

# OpenWeather API Configuration
OPENWEATHER_API_KEY = "bd5e378503939ddaee76f12ad7a97608"
CITY = "Dallas,TX,US"

def init_database():
    db_uri = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    return SQLDatabase.from_uri(db_uri)

def get_weather():
    url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OPENWEATHER_API_KEY}&units=imperial"
    try:
        response = requests.get(url).json()
        if response.get("cod") == 200:
            temp = int(response["main"]["temp"])
            condition = response["weather"][0]["description"].capitalize()
            return f"🌤️ {CITY}: {temp}°F, {condition}"
        # return "Keep pushing — every loan you close helps a family move forward!"
        return "⚠️ Weather data unavailable"
    except Exception:
        return "⚠️ Error fetching weather data"

def fetch_todays_tasks(db):
    if "LOAN_OFFICER" not in st.session_state or not st.session_state["LOAN_OFFICER"]:
        st.session_state["LOAN_OFFICER"] = st.session_state.get('full_name', 'Loan Officer')

    loan_officer = st.session_state["LOAN_OFFICER"].strip()

    if not loan_officer:
        st.warning("Loan Officer is not set in session.")
        return []

    sql_query = f"""
        SELECT loan_id, task_name, Borrower_Name, LOAN_OFFICER, due_date, status
        FROM tasks
        WHERE STR_TO_DATE(TRIM(due_date), '%d-%m-%Y') = CURDATE()
          AND TRIM(LOAN_OFFICER) = '{loan_officer}';
    """

    try:
        response_data = db.run(sql_query)
        if isinstance(response_data, str):
            response_data = eval(response_data)
        return response_data if isinstance(response_data, list) else []
    except Exception as e:
        st.error(f"Database Error: {str(e)}")
        return []

# ✅ Link task names to app steps (not .py files!)
def generate_task_link(task_name, loan_id):
    if task_name.lower() == "appraisal order":
        return ("upload_documents", loan_id)
    elif task_name.lower() == "document verification":
        return ("missing_docs", loan_id)
    elif task_name.lower() == "income verification":
        return ("income_verification", loan_id)
    else:
        return (None, None)

def display_tasks(tasks):
    if not tasks:
        st.success("✅ No tasks are due today. Enjoy your day!")
        return

    # ✅ Persist "Show Tasks" toggle
    if "show_task_list" not in st.session_state:
        st.session_state.show_task_list = False

    if st.button("📌 Show Today's Tasks"):
        st.session_state.show_task_list = True

    if not st.session_state.show_task_list:
        return

    priority_map = {
        "Fell Behind": 1,
        "On Track": 2,
        "Scheduled": 3,
        "Ahead": 4
    }

    tasks_sorted = sorted(tasks, key=lambda x: priority_map.get(x[5], 99))
    st.subheader("🔴 Prioritized Task List (Top to Bottom)")

    status_colors = {
        "Fell Behind": "red",
        "On Track": "green",
        "Ahead": "orange",
        "Scheduled": "blue",
    }

    for loan_id, task_name, Borrower_Name, LOAN_OFFICER, due_date, status in tasks_sorted:
        color = status_colors.get(status, "gray")
        step, loan_id_param = generate_task_link(task_name, loan_id)

        cols = st.columns([2, 3, 2, 2, 2, 2])
        cols[0].markdown(f'<div style="color:{color}; font-weight:bold;">{loan_id}</div>', unsafe_allow_html=True)
        
        if step:
            if cols[1].button(task_name, key=f"{loan_id}_{task_name}"):
                st.session_state["step"] = step
                st.session_state["loan_id"] = loan_id_param
                st.rerun()
        else:
            cols[1].markdown(f'<div style="color:{color}; font-weight:bold;">{task_name}</div>', unsafe_allow_html=True)
        
        cols[2].markdown(f'<div style="color:{color}; font-weight:bold;">{Borrower_Name}</div>', unsafe_allow_html=True)
        cols[3].markdown(f'<div style="color:{color}; font-weight:bold;">{LOAN_OFFICER}</div>', unsafe_allow_html=True)
        cols[4].markdown(f'<div style="color:{color}; font-weight:bold;">{due_date}</div>', unsafe_allow_html=True)
        cols[5].markdown(f'<div style="color:{color}; font-weight:bold;">{status}</div>', unsafe_allow_html=True)

# === Demo Top-Level View (optional to test)
if __name__ == "__main__":
    st.title("Loan Processing Assistant")
    db = init_database()
    st.header(f"👋 Good Morning, {st.session_state.get('full_name', 'Loan Officer')}!")
    st.subheader(get_weather())
    st.markdown("---")
    st.subheader("📋 Overview of Today's Tasks")
    tasks = fetch_todays_tasks(db)
    display_tasks(tasks)
