"""Sprint 44: pulso vivo em todas as telas, com os modos de movimento preservados."""

from django.contrib.staticfiles import finders
from django.test import TestCase


def static_text(path):
    return open(finders.find(path), encoding="utf-8").read()


class PulsoVivoTests(TestCase):
    def test_pulse_layer_covers_every_screen_and_floating_icon(self):
        css = static_text("core/css/app.css")
        layer = css[css.index("Sprint 44"):]
        for piece in (".page-header .eyebrow::before", 'nav a[aria-current="page"] .nav-icon', ".kpi-card strong",
                      ".content .status-pill.status-warning::before", ".method-timeline li b",
                      ".arise-fab::before", ".arise-widget .arise-fab::after", "fs-aurora", "fs-breathe"):
            self.assertIn(piece, layer)

    def test_motion_off_still_wins(self):
        css = static_text("core/css/app.css")
        layer = css[css.index("Sprint 44"):]
        self.assertNotIn("!important", layer)  # o modo "Sem" (com !important) continua desligando tudo
        self.assertIn('html[data-motion="sem"] *, html[data-motion="sem"] *::before', css)
        self.assertIn("prefers-reduced-motion: reduce", css)
        self.assertIn("--fs-w", static_text("core/js/app.js"))
