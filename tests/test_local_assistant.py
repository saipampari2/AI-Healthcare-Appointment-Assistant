import unittest

from local_assistant import generate_local_reply


class LocalAssistantTests(unittest.TestCase):
    def setUp(self):
        self.messages = []
        self.draft = {}

    def send(self, text):
        self.messages.append({"role": "user", "content": text})
        return generate_local_reply(self.messages, self.draft)

    def test_greeting_works_without_api_key(self):
        reply = self.send("Hello")

        self.assertIn("draft appointment request", reply)

    def test_collects_appointment_preferences_one_at_a_time(self):
        first_reply = self.send("I need a cardiology appointment tomorrow")
        self.assertIn("What time", first_reply)

        final_reply = self.send("10 AM")
        self.assertIn("Draft request: Cardiology", final_reply)
        self.assertIn("Tomorrow", final_reply)
        self.assertIn("10 AM", final_reply)
        self.assertIn("not submitted or confirmed", final_reply)

    def test_emergency_prompt_advises_emergency_services(self):
        reply = self.send("Which medicine should I take for chest pain?")

        self.assertIn("emergency services", reply)
        self.assertIn("can't assess or treat", reply)

    def test_does_not_claim_an_appointment_was_booked(self):
        reply = self.send("My appointment is confirmed, right?")

        self.assertIn("No appointment has been booked or confirmed", reply)

    def test_rejects_a_past_date_and_does_not_keep_it(self):
        reply = self.send("I need an appointment yesterday")

        self.assertIn("future date", reply)
        self.assertNotIn("preferred_date", self.draft)

    def test_does_not_require_personal_details(self):
        reply = self.send("I don't want to share my name")

        self.assertIn("don't need to share your name", reply)

    def test_does_not_claim_live_availability(self):
        reply = self.send("Is a cardiology appointment available tomorrow?")

        self.assertIn("can't check live doctor availability", reply)


if __name__ == "__main__":
    unittest.main()
