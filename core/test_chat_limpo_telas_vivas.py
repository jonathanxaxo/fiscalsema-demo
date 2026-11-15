"""Sprint 42: chat mais limpo e vivo, avisos do chat em 10 segundos e telas restantes vivas."""

from django.contrib.staticfiles import finders
from django.test import TestCase


def static_text(path):
    return open(finders.find(path), encoding="utf-8").read()


class ChatLimpoTelasVivasTests(TestCase):
    def test_chat_notices_disappear_after_ten_seconds(self):
        script = static_text("assistant/chat.js")
        self.assertIn("const NOTICE_MS = 10000;", script)
        self.assertNotIn("35000", script)
        self.assertIn("function fadePageNotices()", script)
        self.assertIn("}, 10000);", script)

    def test_chat_has_clean_live_look_and_respects_motion_modes(self):
        css = static_text("assistant/chat.css")
        for piece in ("Sprint 42", "fs-avatar", ".assistant-form:focus-within", ".assistant-notice.is-fading",
                      'html[data-motion="sem"]', "prefers-reduced-motion: reduce"):
            self.assertIn(piece, css)

    def test_remaining_screens_have_live_layer(self):
        css = static_text("core/css/app.css")
        for piece in ("Sprint 42", ".content > .confirmation-panel", ".auth-card > *", "fs-danger-edge",
                      ".content dl > div", ".table-tabs a:hover"):
            self.assertIn(piece, css)
        script = static_text("core/js/app.js")
        self.assertIn("stagger('.auth-card');", script)
