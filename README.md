# Prodapt AI Operations Center 🛰️

![Prodapt Operations Center](https://img.shields.io/badge/Agentic-AI-blue.svg)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-green.svg)

Welcome to the **Prodapt AI Operations Center**! This project acts as an intelligent, multi-agent automated front door for Prodapt Telecom customer support and NOC teams. By integrating specialized frameworks into a single LangGraph-orchestrated workflow, the system can instantly resolve complex queries spanning policy documents, live operational databases, and billing systems.

## ✨ Capabilities & Architecture

Our system employs a modular, microservice-based architecture that uses the best tool for every specific domain:

1. **Policy & FAQ Knowledge** 
   * **Framework:** `LlamaIndex` Document RAG
   * **Purpose:** Embeds and searches company policy TXT files (e.g. Roaming, SLAs).
2. **Network Analytics**
   * **Framework:** `LlamaIndex` Semantic SQL
   * **Purpose:** Queries historical outage and performance metrics in natural language.
3. **Network Diagnostics**
   * **Framework:** `Google ADK` (Agent Development Kit) A2A Microservice
   * **Purpose:** Connects via SQL to tower metrics to actively diagnose connection drops.
4. **Billing Resolution**
   * **Framework:** `Google ADK` A2A Microservice
   * **Purpose:** Checks duplicate charges and applies credits directly to the SQL database.
5. **Customer Communications**
   * **Framework:** `CrewAI`
   * **Purpose:** Employs a multi-agent crew to draft and review the final response for empathy and compliance.
6. **Orchestration & UI**
   * **Framework:** `LangGraph` & `Streamlit`
   * **Purpose:** The LangGraph Supervisor dynamically routes the user query to the correct specialists, while Streamlit visualizes the Agent Execution Trace.

## 🚀 Quick Start Guide

Follow these steps to initialize the environment, seed the database, and run the microservices.

### 1. Prerequisites
- **Python 3.11+**
- A valid **OpenAI API Key** (for LlamaIndex, LangGraph, and CrewAI)
- A valid **Google Gemini API Key** (for Google ADK agents)

### 2. Environment Setup
Create a virtual environment and install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set up your environment variables:
```bash
cp .env.example .env
# Open .env and add your OPENAI_API_KEY and GOOGLE_API_KEY
```

### 3. Initialize the Database
This will create `data/telecom_ops.db` and insert seed data representing customers, towers, outages, and billing charges:
```bash
python init_db.py
```

### 4. Start the Microservices
You must run the Google ADK Agents as standalone A2A microservices alongside the Streamlit app. Open three separate terminal windows and run:

**Terminal 1:** Network Diagnostics Agent (Port 8001)
```bash
PYTHONPATH=. python adk_services/network_diagnostics/agent.py
```

**Terminal 2:** Billing Resolution Agent (Port 8002)
```bash
PYTHONPATH=. python adk_services/billing_resolution/agent.py
```

**Terminal 3:** Streamlit User Interface
```bash
PYTHONPATH=. python -m streamlit run ui/app.py
```

## 🎯 Demo Scenarios

Once the Streamlit UI is running at `http://localhost:8501`, try pasting these real-world scenarios into the chat:

1. **Policy Query:** `"What is Prodapt's roaming policy for Western Europe?"`
2. **Network Analytics:** `"Which region had the most CRITICAL network outages recently?"`
3. **Diagnostics:** `"My 5G keeps dropping in Austin near tower TX-512. Please diagnose."`
4. **Billing Action:** `"Customer CUST-10002 was charged twice for Unlimited Plus. Investigate and apply credit."`
5. **Complex Multi-Agent Flow:** `"We had a 6-hour outage in the Midwest. Am I eligible for SLA credit and what does policy say?"`

## 🧪 Automated Testing (Promptfoo)

This project integrates **promptfoo** to automate the testing of the agentic system.

To evaluate all of the demo scenarios against expected logic assertions automatically:
1. Ensure Node.js is installed (`npx` must be available).
2. Open a new terminal.
3. Run the evaluation:
```bash
source ../.venv/bin/activate
PYTHONPATH=. npx promptfoo@latest eval
```

## 🛠️ Troubleshooting

| Issue | Resolution |
|---|---|
| **ADK unavailable** | Ensure both ADK agent services are running on ports 8001 and 8002. |
| **Empty SQL answers** | Verify `init_db.py` ran successfully and `data/telecom_ops.db` exists. |
| **Hugging Face Errors** | The app handles local cache automatically, but ensure write permissions to `.hf_cache`. |
| **Model Errors** | We strictly use `gpt-4.1-mini` as configured. |
