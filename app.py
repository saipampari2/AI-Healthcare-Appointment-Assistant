"""AI Healthcare Appointment Assistant - Streamlit app.

Prototype only: it creates a DRAFT appointment request.
No real booking, doctor schedule, or patient data storage.
"""
import datetime
import os

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from streamlit.errors import StreamlitSecretNotFoundError

from prompts import PROMPT_VERSION, SYSTEM_PROMPT, TEST_CASES

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

st.set_page_config(page_title="AI Healthcare Appointment Assistant", page_icon="🏥")


# ---------- LLM layer (only this part depends on the provider) ----------
def get_api_key():
    try:
        key = str(st.secrets["OPENAI_API_KEY"]).strip()
        if key:
            return key
    except (StreamlitSecretNotFoundError, KeyError):
        pass
    return os.getenv("OPENAI_API_KEY", "").strip()


def generate_reply(messages):
    """Return (reply_text, error_text). Exactly one of them is None."""
    key = get_api_key()
    if not key:
        return None, (
            "No OpenAI API key found. Add OPENAI_API_KEY to your .env file "
            "(local) or to Streamlit Secrets (deployed)."
        )
    if key.lower() in {"your-openai-api-key", "your-key-here", "replace-me"}:
        return None, (
            "The OpenAI API key is still a placeholder. Add a valid key to the server configuration, "
            ".env file, or Streamlit Secrets."
        )
    if key.startswith("AIza"):
        return None, (
            "This looks like a Google AI Studio/Gemini key, which OpenAI cannot use. "
            "Enter an API key created on the OpenAI platform instead."
        )
    today = datetime.date.today().strftime("%A, %d %B %Y")
    chat_messages = [
        {
            "role": "system",
            "content": f"{SYSTEM_PROMPT}\n\nToday's date is {today}.",
        }
    ]
    chat_messages.extend(
        {"role": message["role"], "content": message["content"]}
        for message in messages
        if message.get("role") in {"user", "assistant"}
    )
    model = MODEL
    try:
        response = requests.post(
            OPENAI_API_URL,
            json={
                "model": model,
                "messages": chat_messages,
                "max_completion_tokens": 500,
                "temperature": 0.3,
            },
            headers={"Authorization": f"Bearer {key}"},
            timeout=45,
        )
    except requests.RequestException as exc:
        return None, (
            f"Could not reach OpenAI ({type(exc).__name__}). "
            "Check your internet connection and try again."
        )

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if not response.ok:
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        message = (
            str(error.get("message", "")).replace(key, "[redacted]").strip()
            if isinstance(error, dict)
            else ""
        )
        if response.status_code == 401:
            return None, (
                "OpenAI rejected this API key (401). Use an API key created on "
                "platform.openai.com—not a ChatGPT password or Google/Gemini key. "
                "Create or check the key in your OpenAI account, then replace OPENAI_API_KEY "
                "in your local .env or Streamlit Cloud Secrets. ChatGPT subscriptions and API billing "
                "are separate. Never share your key in chat."
            )
        if response.status_code == 403:
            return None, "OpenAI denied access. Check the API key's project permissions and API access."
        if response.status_code == 404:
            return None, f"OpenAI could not find model '{model}'. Check the OPENAI_MODEL setting."
        if response.status_code == 429:
            detail = f" Details: {message}" if message else ""
            return None, (
                "OpenAI rate or usage limit reached. Check your API usage and billing limits, "
                f"then try again.{detail}"
            )
        if response.status_code == 400:
            detail = f" Details: {message}" if message else ""
            return None, f"OpenAI rejected the request (HTTP 400). Check the model and request settings.{detail}"
        if response.status_code >= 500:
            return None, f"OpenAI is temporarily unavailable (HTTP {response.status_code}). Try again shortly."
        detail = f": {message}" if message else "."
        return None, f"OpenAI returned an error (HTTP {response.status_code}){detail}"

    try:
        text = payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError, TypeError):
        text = ""
    if not text:
        return None, "The model returned an empty reply. Try rephrasing your message."
    return text, None


# ---------- state ----------
ss = st.session_state
ss.setdefault("messages", [])
ss.setdefault("queued", None)
ss.setdefault("active_test", None)
ss.setdefault("results", {})  # id -> {"actual","version","result","note"}
ss.setdefault("demo_appointments", [])
ss.setdefault("booking_doctor", None)
ss.setdefault("active_page", "Find Doctors")

DEMO_DOCTORS = [
    {
        "name": "Dr. Alex Morgan",
        "specialty": "General Practice",
        "experience": "8 years",
        "rating": "4.8",
        "reviews": "120",
        "fee": "$50",
        "initials": "AM",
        "color": "#e8f1ff",
    },
    {
        "name": "Dr. Sarah Johnson",
        "specialty": "Cardiology",
        "experience": "10 years",
        "rating": "4.9",
        "reviews": "312",
        "fee": "$200",
        "initials": "SJ",
        "color": "#f4eaff",
    },
    {
        "name": "Dr. Aisha Rahman",
        "specialty": "Dermatology",
        "experience": "7 years",
        "rating": "4.7",
        "reviews": "56",
        "fee": "$150",
        "initials": "AR",
        "color": "#fff3e8",
    },
    {
        "name": "Dr. Daniel Lee",
        "specialty": "Dermatology",
        "experience": "9 years",
        "rating": "4.8",
        "reviews": "84",
        "fee": "$160",
        "initials": "DL",
        "color": "#e8f6ff",
    },
]
DEMO_SLOTS = ["09:00", "10:30", "13:00", "14:30", "16:00"]
NAV_ITEMS = [
    "Home",
    "Find Doctors",
    "My Appointments",
    "Notifications",
    "My Profile",
    "Ask Assistant",
    "Test Results",
]


def navigate_to(page):
    ss.active_page = page
    ss.navigation = page


def queue_test_case(test_id, prompt):
    new_chat()
    ss.active_test = test_id
    ss.queued = prompt
    navigate_to("Ask Assistant")


def start_new_assistant_chat():
    new_chat()
    navigate_to("Ask Assistant")


def render_assistant_panel():
    st.markdown("### MediBook AI Assistant")
    st.caption("Powered by OpenAI · Demo assistant")
    st.info("Not for emergencies, diagnosis, or treatment.")
    st.caption(
        "Messages are sent to OpenAI to generate replies. "
        "Do not enter real patient or health information."
    )
    for message in ss.messages[-6:]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    with st.form("assistant_message_form", clear_on_submit=True):
        message_text = st.text_input("Ask a question", placeholder="How can I start an appointment request?")
        send_message = st.form_submit_button("Send", use_container_width=True)

    user_input = ss.queued
    if user_input:
        ss.queued = None
    elif send_message:
        user_input = message_text.strip()

    if user_input:
        ss.messages.append({"role": "user", "content": user_input})
        with st.spinner("Assistant is responding..."):
            reply, error = generate_reply(ss.messages)
        if error:
            ss.messages.pop()
            st.error(error)
        else:
            ss.messages.append({"role": "assistant", "content": reply})
            if ss.active_test:
                old_result = ss.results.get(ss.active_test, {})
                ss.results[ss.active_test] = {
                    "actual": reply,
                    "version": PROMPT_VERSION,
                    "result": "",
                    "note": old_result.get("note", ""),
                }
                ss.active_test = None
            st.rerun()

    st.caption("Demo only. Messages are not sent to a hospital and cannot book an appointment.")


def render_doctor_directory():
    st.markdown("<p class='eyebrow'>YOUR CARE, MADE SIMPLE</p>", unsafe_allow_html=True)
    st.title("Find the right doctor")
    st.caption("Explore specialists and prepare a demo appointment request.")

    summary_cols = st.columns(3)
    for column, label, value in zip(
        summary_cols,
        ("Specialties", "Sample doctors", "Booking status"),
        ("3 departments", str(len(DEMO_DOCTORS)), "Demo only"),
    ):
        with column:
            with st.container(border=True):
                st.caption(label)
                st.markdown(f"<div class='summary-value'>{value}</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-heading'>Browse specialists</div>", unsafe_allow_html=True)
    search_col, department_col = st.columns([1.7, 1])
    with search_col:
        search_text = st.text_input(
            "Search",
            placeholder="Doctor name or specialty",
            label_visibility="collapsed",
        )
    with department_col:
        departments = ["All specialties"] + sorted({doctor["specialty"] for doctor in DEMO_DOCTORS})
        selected_department = st.selectbox(
            "Specialty",
            departments,
            label_visibility="collapsed",
        )

    filtered_doctors = [
        doctor for doctor in DEMO_DOCTORS
        if (selected_department == "All specialties" or doctor["specialty"] == selected_department)
        and search_text.lower() in f"{doctor['name']} {doctor['specialty']}".lower()
    ]
    if not filtered_doctors:
        st.warning("No sample doctors match that search.")

    for start in range(0, len(filtered_doctors), 2):
        columns = st.columns(2, gap="medium")
        for column, doctor in zip(columns, filtered_doctors[start:start + 2]):
            with column:
                with st.container(border=True):
                    avatar, details = st.columns([1, 4])
                    avatar.markdown(
                        f"<div class='doctor-avatar' style='background:{doctor['color']}'>{doctor['initials']}</div>",
                        unsafe_allow_html=True,
                    )
                    details.markdown(f"**{doctor['name']}**")
                    details.caption(f"{doctor['specialty']} · {doctor['experience']} experience")
                    st.markdown(
                        f"<span class='rating'>★ {doctor['rating']}</span> "
                        f"<span class='review-count'>({doctor['reviews']} sample reviews)</span> "
                        f"<span class='doctor-fee'>{doctor['fee']} <small>/ visit</small></span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown("<span class='demo-tag'>SAMPLE PROFILE · NOT LIVE</span>", unsafe_allow_html=True)
                    if st.button(
                        "Demo appointment options",
                        key=f"book_{doctor['initials']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        ss.booking_doctor = doctor["name"]

    if ss.booking_doctor:
        st.divider()
        st.subheader(f"Demo appointment request · {ss.booking_doctor}")
        st.warning(
            "Use sample information only. This demo does not contact the doctor, verify slots, "
            "or create a real appointment."
        )
        with st.form("demo_booking_form"):
            date_col, time_col = st.columns(2)
            with date_col:
                appointment_date = st.date_input(
                    "Preferred date",
                    min_value=datetime.date.today(),
                    value=datetime.date.today() + datetime.timedelta(days=1),
                )
            with time_col:
                appointment_time = st.selectbox("Sample time (not live)", DEMO_SLOTS)
            submitted = st.form_submit_button("Save demo request", type="primary")
        if submitted:
            ss.demo_appointments.append({
                "doctor": ss.booking_doctor,
                "date": appointment_date.isoformat(),
                "time": appointment_time,
                "status": "Demo request only — not submitted",
            })
            ss.booking_doctor = None
            st.success("Demo request saved in this browser session only. No appointment was booked.")
            st.rerun()


def render_appointments():
    st.title("My Appointments")
    st.caption("Only demo requests created in this browser session appear here.")
    if not ss.demo_appointments:
        st.info("No demo requests yet. Use Find Doctors to create a sample request.")
        return
    for appointment in reversed(ss.demo_appointments):
        with st.container(border=True):
            st.markdown(f"**{appointment['doctor']}**")
            st.write(f"{appointment['date']} at {appointment['time']}")
            st.warning(appointment["status"])


def render_test_results():
    st.title("Assistant test results")
    st.write(
        "Review each OpenAI response, then mark Pass or Fail. Check that it does not invent "
        "availability or confirmations, diagnose, or prescribe."
    )
    rows = []
    for test_id, text, expected in TEST_CASES:
        result = ss.results.get(test_id, {})
        rows.append({
            "Test ID": test_id,
            "Input": text,
            "Expected": expected,
            "Actual response": result.get("actual", ""),
            "Version": result.get("version", ""),
            "Pass/Fail": result.get("result", ""),
            "Issue / improvement": result.get("note", ""),
        })
    dataframe = pd.DataFrame(rows)
    edited = st.data_editor(
        dataframe,
        hide_index=True,
        width="stretch",
        disabled=["Test ID", "Input", "Expected", "Actual response", "Version"],
        column_config={"Pass/Fail": st.column_config.SelectboxColumn(options=["", "Pass", "Fail"])},
        key="results_editor",
    )
    for _, row in edited.iterrows():
        test_id = row["Test ID"]
        if test_id in ss.results:
            ss.results[test_id]["result"] = row["Pass/Fail"] or ""
            ss.results[test_id]["note"] = row["Issue / improvement"] or ""

    marked = edited[edited["Pass/Fail"].isin(["Pass", "Fail"])]
    if len(marked):
        passed = int((marked["Pass/Fail"] == "Pass").sum())
        st.metric("Pass rate (marked tests)", f"{passed} / {len(marked)}", f"{round(100 * passed / len(marked))}%")
    else:
        st.caption("Pass rate appears after you mark tests.")
    st.download_button(
        "Download test results CSV",
        edited.to_csv(index=False),
        file_name="test_results.csv",
        mime="text/csv",
    )
    st.caption("Results are session-only until downloaded.")


def new_chat():
    ss.messages = []
    ss.active_test = None
    ss.queued = None


# ---------- styling and sidebar ----------
st.markdown(
    """
    <style>
    :root {
        --ink: #202b3c;
        --muted: #68778b;
        --brand: #1769df;
        --line: #e6ebf2;
        --canvas: #f5f8fc;
    }
    html, body, [class*="css"] { font-family: Inter, "Segoe UI", sans-serif; }
    [data-testid="stAppViewContainer"], .stApp {
        background: radial-gradient(ellipse at 85% 0%, #e9f2ff 0, transparent 32%), var(--canvas);
        color: var(--ink) !important;
    }
    [data-testid="stMain"] { padding-top: 1.4rem; background: transparent !important; }
    [data-testid="stMainBlockContainer"] { max-width: 1500px; padding: 1.8rem 2.2rem 2.4rem; }
    [data-testid="stSidebar"] {
        min-width: 265px !important; max-width: 265px !important;
        background: #182131 !important; border-right: 1px solid #243146;
    }
    [data-testid="stSidebar"] > div { background: #182131 !important; }
    [data-testid="stSidebar"] * { color: #e8eef8; }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #9eabc0; }
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        background: #202c3e; border: 1px solid #2e3d53; border-radius: 12px;
    }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color: #e8eef8; }
    [data-testid="stSidebar"] input {
        color: #f3f6fb; background: #263449; border-color: #394b64;
    }
    [data-testid="stSidebar"] button {
        color: #e8eef8; border-color: #34435a; background: #202c3e;
        border-radius: 10px; transition: background .15s ease, border-color .15s ease;
    }
    [data-testid="stSidebar"] button:hover { background: #2c3b52; border-color: #55719a; }
    h1, h2, h3 { color: var(--ink); letter-spacing: -0.035em; }
    h1 { font-size: clamp(1.9rem, 2.6vw, 2.4rem) !important; font-weight: 750 !important; margin-bottom: .2rem !important; }
    [data-testid="stCaptionContainer"] { color: var(--muted); }
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255,255,255,.93); border: 1px solid var(--line); border-radius: 17px;
        box-shadow: 0 8px 26px rgba(25, 45, 75, .045);
    }
    [data-testid="stTextInput"] input, [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        min-height: 46px; border-radius: 11px; border-color: #dce4ee; background: #fff;
    }
    [data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button {
        min-height: 43px; border-radius: 11px; font-weight: 650; transition: all .15s ease;
    }
    [data-testid="stButton"] button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
        background: linear-gradient(100deg, #1769df, #315ff2); border: 0;
        box-shadow: 0 5px 14px rgba(23, 105, 223, .18);
    }
    [data-testid="stButton"] button[kind="primary"]:hover,
    [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
        background: #0d55c5; box-shadow: 0 7px 18px rgba(23, 105, 223, .25);
        transform: translateY(-1px);
    }
    [data-testid="stAlert"] { border-radius: 12px; }
    [data-testid="stMetric"] { padding: .2rem 0; }
    .doctor-avatar {
        width: 58px; height: 58px; border-radius: 17px; display: flex;
        align-items: center; justify-content: center; font-weight: 700;
        color: #1769df; font-size: 18px; margin-top: 4px;
    }
    .doctor-fee { float: right; color: #1769df; font-weight: 750; font-size: 1.12rem; }
    .doctor-fee small { color: #8793a3; font-weight: 500; font-size: .72rem; }
    .rating { color: #d28a00; font-weight: 700; }
    .review-count { color: #8793a3; font-size: .82rem; }
    .demo-tag {
        display: inline-block; padding: 4px 8px; border-radius: 7px; margin: 4px 0 12px;
        color: #60718a; background: #f0f4f8; font-size: 10px; font-weight: 700; letter-spacing: .045em;
    }
    .eyebrow { color: #1769df; font-size: 11px; font-weight: 750; letter-spacing: .11em; margin: 0 0 .35rem; }
    .summary-value { color: var(--ink); font-size: 1.15rem; font-weight: 700; margin-top: 2px; }
    .section-heading { color: var(--ink); font-size: 1.18rem; font-weight: 700; margin: 1.5rem 0 .75rem; }
    @media (max-width: 900px) {
        [data-testid="stMainBlockContainer"] { padding: 1.2rem 1rem 2rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## 🏥 MediBook")
    st.caption("PATIENT PORTAL · DEMO")
    st.divider()
    selected_page = st.radio(
        "Navigation",
        NAV_ITEMS,
        index=NAV_ITEMS.index(ss.active_page) if ss.active_page in NAV_ITEMS else 1,
        label_visibility="collapsed",
        format_func=lambda item: {
            "Home": "⌂  Home",
            "Find Doctors": "⚕  Find Doctors",
            "My Appointments": "▣  My Appointments",
            "Notifications": "♧  Notifications",
            "My Profile": "♙  My Profile",
            "Ask Assistant": "✦  Ask AI Assistant",
            "Test Results": "✓  Test Results",
        }[item],
        key="navigation",
    )
    ss.active_page = selected_page
    st.divider()
    with st.expander("Assistant test cases"):
        st.caption("Choose a case to send it to the assistant.")
        for test_id, text, _ in TEST_CASES:
            st.button(
                f"{test_id}: {text}",
                key=f"btn_{test_id}",
                use_container_width=True,
                on_click=queue_test_case,
                args=(test_id, text),
            )
    st.button(
        "＋  New assistant chat",
        use_container_width=True,
        on_click=start_new_assistant_chat,
    )
    st.divider()
    st.caption(f"Prompt {PROMPT_VERSION}")

# ---------- dashboard pages ----------
if selected_page == "Find Doctors":
    main_col, assistant_col = st.columns([1.8, 1], gap="large")
    with main_col:
        render_doctor_directory()
    with assistant_col:
        with st.container(border=True):
            render_assistant_panel()
elif selected_page == "Home":
    st.markdown("<p class='eyebrow'>PATIENT DASHBOARD</p>", unsafe_allow_html=True)
    st.title("Good day 👋")
    st.caption("Find a specialist or start a draft appointment request.")
    st.info("Prototype demo: sample doctors and slots are not verified. No real appointment is booked.")
    card_cols = st.columns(3)
    for column, number, label in zip(
        card_cols,
        [len(DEMO_DOCTORS), len(ss.demo_appointments), "24/7"],
        ["Sample doctors", "Demo requests", "Assistant access"],
    ):
        with column:
            with st.container(border=True):
                st.metric(label, number)
    st.subheader("Quick actions")
    action_cols = st.columns(3)
    for column, label, page in zip(
        action_cols,
        ["Find a doctor", "My demo requests", "Ask the assistant"],
        ["Find Doctors", "My Appointments", "Ask Assistant"],
    ):
        with column:
            st.button(label, use_container_width=True, on_click=navigate_to, args=(page,))
    st.divider()
    left, right = st.columns([1.5, 1], gap="large")
    with left:
        st.subheader("Featured specialists")
        for doctor in DEMO_DOCTORS[:3]:
            with st.container(border=True):
                st.markdown(f"**{doctor['name']}** · {doctor['specialty']} · ⭐ {doctor['rating']}")
                st.caption("Sample profile — availability is not live")
    with right:
        with st.container(border=True):
            render_assistant_panel()
elif selected_page == "My Appointments":
    render_appointments()
elif selected_page == "Notifications":
    st.title("Notifications")
    st.caption("Demo notifications — no hospital messages are connected.")
    st.info("Welcome to MediBook. Sample appointment reminders will appear here in a connected service.")
    st.info("Your assistant is available to help prepare an unsubmitted request.")
elif selected_page == "My Profile":
    st.title("My Profile")
    st.warning("Demo profile only. Please do not enter real patient or contact information.")
    with st.form("demo_profile_form"):
        st.text_input("Display name", placeholder="Demo Patient")
        st.text_input("Email", placeholder="patient@example.test")
        saved_profile = st.form_submit_button("Save demo profile", type="primary")
    if saved_profile:
        st.success("Profile form submitted for this demo. No profile data was saved.")
    st.caption("Profile fields are not sent to a hospital or persisted.")
elif selected_page == "Ask Assistant":
    st.title("MediBook AI Assistant")
    st.caption("Ask about preparing a draft appointment request.")
    st.info("This assistant does not provide diagnosis or treatment. For an emergency, contact local emergency services.")
    render_assistant_panel()
elif selected_page == "Test Results":
    render_test_results()

st.divider()
st.caption(
    f"Prototype only · No live hospital connection · Nothing is booked · "
    f"Prompt {PROMPT_VERSION}"
)