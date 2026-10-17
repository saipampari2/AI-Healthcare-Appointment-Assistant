"""Deterministic, key-free replies for the appointment-assistant demo."""

import re


def generate_local_reply(messages, draft):
    """Reply to common questions and collect a session-only appointment draft."""
    user_messages = [
        message["content"].strip()
        for message in messages
        if message.get("role") == "user" and message.get("content", "").strip()
    ]
    if not user_messages:
        return "Hi! I can help you prepare a draft appointment request. What would you like help with?"

    latest = user_messages[-1]
    text = latest.lower()

    if any(term in text for term in (
        "chest pain", "can't breathe", "cannot breathe", "difficulty breathing",
        "shortness of breath", "stroke", "unconscious", "emergency",
    )):
        return (
            "This may need urgent medical attention. Please contact your local emergency "
            "services now or go to the nearest emergency department. I can't assess or treat "
            "medical conditions."
        )

    if any(term in text for term in (
        "diagnos", "medicine", "medication", "prescribe", "treatment", "symptom",
        "what should i take", "which drug",
    )):
        return (
            "I can't diagnose symptoms or recommend medicines. Please contact a licensed "
            "healthcare professional. If this could be an emergency, contact local emergency "
            "services now."
        )

    if any(term in text for term in ("confirmed", "confirmation", "already booked", "is it booked")):
        return (
            "No appointment has been booked or confirmed. This demo can only help prepare "
            "an unsubmitted request; it does not contact a hospital."
        )

    if any(term in text for term in ("available", "availability", "open slot", "time slot")):
        return (
            "I can't check live doctor availability or schedules. The doctors and times in "
            "this demo are samples only."
        )

    appointment_terms = ("appointment", "book", "booking", "schedule", "see a doctor", "visit a doctor")
    is_appointment_chat = any(term in text for term in appointment_terms) or draft.get("started", False)
    if not is_appointment_chat:
        if any(term in text for term in ("name", "personal information")) and any(
            phrase in text for phrase in ("don't want", "do not want", "not share", "won't share")
        ):
            return (
                "You don't need to share your name or contact details here. To prepare a demo "
                "draft, I only ask for a specialty and preferred date and time."
            )
        if any(term in text for term in ("hello", "hi", "hey", "good morning", "good afternoon")):
            return (
                "Hello! I can answer questions about this demo or help prepare a draft "
                "appointment request. Which would you like?"
            )
        if any(term in text for term in ("thank", "thanks")):
            return "You're welcome. Remember, this demo does not submit or confirm appointments."
        return (
            "I can help prepare a draft appointment request, but I can't provide medical "
            "advice or check live doctor schedules. Would you like to start an appointment request?"
        )

    draft["started"] = True
    for department in (
        "cardiology", "dermatology", "neurology", "general practice", "general",
        "pediatrics", "orthopedics", "ophthalmology", "gastroenterology",
    ):
        if department in text:
            draft["department"] = department.title()
            break

    date_match = next(
        (value for value in (
            "tomorrow", "next week", "monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday",
        ) if value in text),
        None,
    )
    if date_match:
        draft["preferred_date"] = date_match.title()
    elif "today" in text or "yesterday" in text or "last week" in text or "last month" in text:
        draft.pop("preferred_date", None)
        return "Please choose a future date for your request. What date would you prefer?"
    else:
        explicit_date = re.search(
            r"\b(?:\d{4}-\d{2}-\d{2}|"
            r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
            r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|"
            r"dec(?:ember)?)\s+\d{1,2}(?:,?\s+\d{4})?)\b",
            latest,
            flags=re.IGNORECASE,
        )
        if explicit_date:
            draft["preferred_date"] = explicit_date.group(0)

    time_match = re.search(
        r"\b(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?))\b",
        latest,
        flags=re.IGNORECASE,
    )
    if time_match:
        draft["preferred_time"] = time_match.group(1).strip()

    if not draft.get("department"):
        if "dr." in text or "doctor" in text:
            return (
                "I can't verify a specific doctor's schedule or availability. Which department "
                "or specialty would you like to include in your draft?"
            )
        return "Which department or specialty would you like to see, such as cardiology or dermatology?"
    if not draft.get("preferred_date"):
        return "What future date would you prefer? I can't check the hospital's live schedule."
    if not draft.get("preferred_time"):
        return "What time would you prefer? This is only a preference; I can't verify available slots."

    return (
        f"Draft request: {draft['department']} · {draft['preferred_date']} · "
        f"{draft['preferred_time']}. Is that correct? This request is not submitted or confirmed."
    )
