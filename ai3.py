from fastapi import FastAPI, HTTPException
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import pandas as pd
import os
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MODEL_PATH = "C:/Users/YourUsername/phi-2/"

# Define global model and tokenizer variables
model = None
tokenizer = None

# Load application details from JSON
with open("applications.json", "r", encoding="utf-8") as f:
    applications_data = json.load(f)
    applications = applications_data["applications"]

# Load ServiceNow ticket data
ticket_data = pd.read_csv("servicenow_tickets.csv", encoding="utf-8", errors="replace").fillna("Unknown")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, tokenizer
    logging.info("Loading Phi-2 model into memory...")
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, torch_dtype=torch.float32)
    
    logging.info("Model loaded successfully.")
    
    yield  # Keep the model loaded while FastAPI is running

    # Cleanup (optional)
    logging.info("Shutting down FastAPI... clearing model from memory.")
    del model
    del tokenizer
    torch.cuda.empty_cache()  # If using GPU

# Initialize FastAPI with lifespan
app = FastAPI(lifespan=lifespan)

STATIC_QUESTIONS = [
    "How familiar are you with the core infrastructure of this application?",
    "Have you resolved any critical issues related to this application?",
    "How well do you understand its functionalities and dependencies?",
    "Have you worked on performance optimization for this application?",
    "Can you troubleshoot complex failures in this application?"
]

@app.get("/applications")
def get_applications():
    return {"applications": list(applications.keys())}

@app.get("/static-questions")
def get_static_questions():
    return {"questions": STATIC_QUESTIONS}

@app.post("/verify-skill")
def verify_skill(payload: dict):
    user = payload["user"]
    application = payload["application"]
    responses = payload["responses"]
    
    if application not in applications:
        raise HTTPException(status_code=400, detail="Application not found")
    
    app_tickets = ticket_data[ticket_data["application"] == application]
    logging.info(f"Found {len(app_tickets)} tickets for application {application}")
    
    app_details = applications.get(application, {})
    functionality = app_details.get("functionality", "Unknown functionality")
    criticality = app_details.get("criticality", "Unknown criticality")
    common_issues = app_details.get("common_issues", [])
    
    input_prompt = (
        f"User rated themselves {responses} in {application}. "
        f"This application handles: {functionality}. "
        f"It has a criticality level of {criticality}. "
        f"Common issues include: {', '.join(common_issues)}. "
        f"Based on past ServiceNow tickets, generate 5 advanced questions."
    )
    
    inputs = tokenizer(input_prompt, return_tensors="pt")
    with torch.no_grad():
        output = model.generate(**inputs, max_length=200)
    questions = tokenizer.decode(output[0], skip_special_tokens=True).split("\n")
    
    return {"questions": [q for q in questions if q.strip()]}
