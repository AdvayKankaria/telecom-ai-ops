# Run Instructions for Telecom AI Operations Center

Follow these commands to quickly start all necessary services for the Capstone Project.

### 1. Database Initialization
Run this once to build the tables and seed the initial data:
```bash
../.venv/bin/python3 init_db.py
```

### 2. Start the Microservices
You will need to open **three separate terminals** to run the agents and the user interface simultaneously.

**Terminal 1: Network Diagnostics ADK Agent**
```bash
PYTHONPATH=. ../.venv/bin/python3 adk_services/network_diagnostics/agent.py
```

**Terminal 2: Billing Resolution ADK Agent**
```bash
PYTHONPATH=. ../.venv/bin/python3 adk_services/billing_resolution/agent.py
```

**Terminal 3: Streamlit UI**
```bash
PYTHONPATH=. ../.venv/bin/python3 -m streamlit run ui/app.py
```

### 3. Run Promptfoo Evaluations (Optional)
To test the entire multi-agent system against the standard demo scenarios using `promptfoo`, you can run the following command in a new terminal:
```bash
source ../.venv/bin/activate
PYTHONPATH=. npx promptfoo@latest eval
```

*Note: Once everything is running, you can view the Streamlit dashboard by navigating to `http://localhost:8501` in your browser.*
