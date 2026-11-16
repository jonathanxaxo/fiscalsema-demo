"""Visual vivo (Sprint 41): logotipo, controle de movimento, fontes locais e acessibilidade."""

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from contracts.tests import VALID_PASSWORD
from accounts.models import AccountStatus, User


def static_text(path):
    return open(finders.find(path), encoding="utf-8").read()


class VisualVivoTests(TestCase):
    def test_logo_is_magnifier_and_follows_motion_modes(self):
        logo = static_text("core/img/logo.svg")
        self.assertNotIn("prefers-reduced-motion", logo)
        self.assertIn("tick", logo)
        self.assertTrue(finders.find("core/fonts/space-grotesk-latin.woff2"))
        self.assertTrue(finders.find("core/fonts/inter-latin.woff2"))

    def test_css_has_motion_modes_and_reduced_motion(self):
        css = static_text("core/css/app.css")
        for piece in ('html[data-motion="sem"]', 'html[data-motion="calmo"]', "prefers-reduced-motion: reduce",
                      ".progress .fs-tip", ".live-badge", "@font-face", "fs-panel"):
            self.assertIn(piece, css)
        self.assertNotIn("fonts.googleapis.com", css)

    def test_motion_control_and_live_badge_on_screens(self):
        user = User.objects.create_user(email="vivo@example.local", full_name="Fiscal Vivo",
                                        password=VALID_PASSWORD, status=AccountStatus.ACTIVE)
        self.client.force_login(user)
        page = self.client.get(reverse("home"))
        self.assertContains(page, 'data-motion-choice="vivo"')
        self.assertContains(page, 'data-motion-choice="sem"')
        self.assertContains(page, "fiscalsema-movimento")
        script = static_text("core/js/app.js")
        for piece in ("fs-ripple", "fs-ring", "--fs-i", "still()"):
            self.assertIn(piece, script)
