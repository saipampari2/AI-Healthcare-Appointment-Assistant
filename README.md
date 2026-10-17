# AI Healthcare Appointment Assistant

A Streamlit chat assistant that guides visitors through creating a **draft appointment request** for a demo hospital. It works without an API key using a built-in, deterministic assistant; optionally, the app owner can configure OpenAI for generated responses.

**Live demo:** https://saipampari2-ai-healthcare-appointment-assistant-app-avdugt.streamlit.app/

## What it does
- MediBook-style patient dashboard with Home, Find Doctors, My Appointments, Notifications, My Profile, Ask Assistant and Test Results pages
- Searchable sample doctor directory with department filtering
- Demo appointment request form; it records the request in browser-session memory and explicitly does not book or contact a hospital
- Built-in assistant works without an API key and guides visitors through common appointment questions
- Optional OpenAI assistant asks follow-up questions and is instructed not to diagnose, prescribe, or invent real doctor availability or confirmations
- Eight assistant test cases with manual Pass/Fail marking and CSV export

## Project structure
```
app.py            Streamlit UI, optional LLM call, test runner
local_assistant.py Key-free appointment and safety responses
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
copy .env.example .env     # optional: add your OpenAI API key to .env
streamlit run app.py
```

No key is needed to run the built-in assistant. To enable optional OpenAI-generated responses, create an API key on the OpenAI platform and set `OPENAI_API_KEY` in `.env`. Use an OpenAI API key, not a ChatGPT password or Google/Gemini key. ChatGPT subscriptions and API billing are separate; API usage may incur charges and requires an OpenAI project with API access and billing enabled. The default model is `gpt-4o-mini`; set `OPENAI_MODEL` in your local environment to use a different model.

## Deploy
Push to GitHub, then on Streamlit Community Cloud pick the repo, branch `main`, file `app.py`. The app works for visitors without secrets. To optionally enable OpenAI-generated replies, under Advanced settings > Secrets add:
```
OPENAI_API_KEY = "your-openai-api-key"
OPENAI_MODEL = "gpt-4o-mini"
```
When no server-side key is configured, visitors use the built-in assistant. It is deterministic (not an AI model), covers common appointment-draft and safety questions, and does not send messages to an external service. With an OpenAI secret configured, messages are sent to OpenAI; do not enter real patient or health information. Visitors never need to provide their own key. Do not put API keys in app code or share them in chat. API errors, including invalid keys, unavailable models, rate limits, and usage limits, are shown in the app.

## Testing results
Use the **Assistant test cases** section in the app to check replies against the prompt, then export the marked results as CSV. Prompt rules are versioned in `prompts.py`.

## Limitations
Prototype only. Doctors, fees, ratings and time slots are sample data, not verified schedules. Requests and chat state are not persisted. The app does not authenticate patients, connect to a real hospital API, or book appointments. The built-in assistant is limited and deterministic; optional OpenAI replies can vary between runs and are sent to OpenAI. Do not enter real patient or health information.

`hospital_backend.py` is a separate demo API and is not called by the Streamlit chat. It uses in-memory sample data and demo credentials; its schedules are not verified and it is not production-secure. It must not be used with real patient data or represented as a real booking service.
