# AI Healthcare Appointment Assistant

A Streamlit chat assistant powered by OpenAI that guides patients through creating a **draft appointment request** for a demo hospital.

**Live demo:** _add your Streamlit URL here_

## What it does
- MediBook-style patient dashboard with Home, Find Doctors, My Appointments, Notifications, My Profile, Ask Assistant and Test Results pages
- Searchable sample doctor directory with department filtering
- Demo appointment request form; it records the request in browser-session memory and explicitly does not book or contact a hospital
- OpenAI assistant asks follow-up questions and is instructed not to diagnose, prescribe, or invent real doctor availability or confirmations
- Eight assistant test cases with manual Pass/Fail marking and CSV export

## Project structure
```
app.py            Streamlit UI, LLM call, test runner
prompts.py        System prompt and test cases (versioned)
hospital_backend.py  Standalone, in-memory hospital API mock (not connected to app.py)
requirements.txt  Dependencies
.env.example      Template for the API key (never commit .env)
```

## Run locally (Windows)
```
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env     # then add your OpenAI API key to .env
streamlit run app.py
```

Create an API key at the OpenAI platform API keys page and set `OPENAI_API_KEY` in `.env`. Use an OpenAI API key, not a ChatGPT password or Google/Gemini key. ChatGPT subscriptions and API billing are separate; API usage may incur charges and requires an OpenAI project with API access and billing enabled. The default model is `gpt-4o-mini`; set `OPENAI_MODEL` in your local environment to use a different model.

## Deploy
Push to GitHub, then on Streamlit Community Cloud pick the repo, branch `main`, file `app.py`. Under Advanced settings > Secrets add:
```
OPENAI_API_KEY = "your-openai-api-key"
OPENAI_MODEL = "gpt-4o-mini"
```
Before sharing the link, the app owner must configure `OPENAI_API_KEY` in **Manage app > Settings > Secrets**. Set `OPENAI_MODEL` there optionally; the default is `gpt-4o-mini`. Visitors can then use the chatbot without providing their own API key. The key is read only on the server and is not shown in the app UI. Do not put API keys in app code or share them in chat. API errors, including invalid keys, unavailable models, rate limits, and usage limits, are shown in the app.

## Testing results
Use the **Assistant test cases** section in the app to check replies against the prompt, then export the marked results as CSV. Prompt rules are versioned in `prompts.py`.

## Limitations
Prototype only. The assistant uses the live OpenAI API, but doctors, fees, ratings and time slots are sample data, not verified schedules. Requests and chat state are not persisted. The app does not authenticate patients, connect to a real hospital API, or book appointments. Messages are sent to OpenAI to generate responses; do not enter real patient or health information. AI replies can vary between runs.

`hospital_backend.py` is a separate demo API and is not called by the Streamlit chat. It uses in-memory sample data and demo credentials; its schedules are not verified and it is not production-secure. It must not be used with real patient data or represented as a real booking service.
