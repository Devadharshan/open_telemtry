import streamlit as st
import requests
import logging

# Configure logging
logging.basicConfig(
    filename="ui.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# FastAPI backend URL
FASTAPI_URL = "http://localhost:8000"

st.title("Self-Assessment Tool")
st.write("Welcome to the AI-powered Self-Assessment Tool!")

logging.info("Streamlit UI started successfully.")

# Get application list from FastAPI
try:
    response = requests.get(f"{FASTAPI_URL}/applications")
    if response.status_code == 200:
        applications = response.json().get("applications", [])
        logging.info(f"Fetched applications: {applications}")
    else:
        applications = ["Error fetching applications"]
        logging.error(f"Error fetching applications: {response.text}")
except Exception as e:
    applications = ["Error fetching applications"]
    logging.exception("Exception while fetching applications")

# Dropdown for selecting an application
app_name = st.selectbox("Select an Application", applications)

# Self-assessment questions (Static)
st.subheader("Rate Yourself")
q1 = st.slider("How familiar are you with the core infrastructure?", 1, 5, 3)
q2 = st.slider("Have you resolved any critical issues?", 1, 5, 3)
q3 = st.slider("How well do you understand its functionalities?", 1, 5, 3)
q4 = st.slider("Have you worked on performance optimization?", 1, 5, 3)
q5 = st.slider("Can you troubleshoot complex failures?", 1, 5, 3)

# Submit button
if st.button("Submit"):
    user_responses = [q1, q2, q3, q4, q5]
    payload = {"user": "TestUser", "application": app_name, "responses": user_responses}

    logging.info(f"User submitted responses: {payload}")

    try:
        response = requests.post(f"{FASTAPI_URL}/verify-skill", json=payload)
        if response.status_code == 200:
            st.subheader("AI-Generated Questions")
            questions = response.json().get("questions", [])
            for question in questions:
                st.write(f"- {question}")
            logging.info(f"Received AI-generated questions: {questions}")
        else:
            st.error("Error fetching AI-generated questions.")
            logging.error(f"Error in API response: {response.text}")
    except Exception as e:
        st.error("Failed to connect to the backend.")
        logging.exception("Exception while sending request to backend")
