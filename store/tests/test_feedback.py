"""Tests for contact/feedback capture and staff access."""

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from store.models import Feedback


class ContactSubmissionTests(TestCase):
    """Public contact form submission."""

    def setUp(self):
        self.client = Client()

    def test_contact_page_renders(self):
        response = self.client.get(reverse("contact"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contact Us")

    def test_contact_submit_creates_feedback(self):
        response = self.client.post(reverse("contact"), {
            "name": "Jane", "email": "jane@test.com",
            "subject": "Order query", "message": "Where is my order?",
        })
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(Feedback.objects.count(), 1)
        fb = Feedback.objects.first()
        self.assertEqual(fb.name, "Jane")
        self.assertFalse(fb.is_read)


class StaffFeedbackTests(TestCase):
    """Staff access to feedback list."""

    def setUp(self):
        self.client = Client()

    def test_feedback_list_staff_only(self):
        response = self.client.get(reverse("staff_feedback_list"))
        self.assertIn(response.status_code, (302, 403))

    def test_feedback_list_renders_for_staff(self):
        User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.client.login(username="staff", password="pass")
        Feedback.objects.create(
            name="A", email="a@t.com", subject="S", message="M",
        )
        response = self.client.get(reverse("staff_feedback_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "a@t.com")
