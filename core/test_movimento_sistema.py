"""Sprint 45: o pedido de "reduzir movimento" do computador não deixa mais o sistema parado.

Sem escolha da pessoa, vira "Calmo" (pulsa mais devagar); "Vivo" e "Sem" escolhidos sempre valem.
"""

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


def static_text(path):
    return open(finders.find(path), encoding="utf-8").read()


class MovimentoSistemaTests(TestCase):
    def test_os_reduced_motion_falls_back_to_calm_not_frozen(self):
        css = static_text("core/css/app.css")
        self.assertNotIn("@media (prefers-reduced-motion: reduce) { *, *::before", css)
        self.assertIn("html:not([data-motion]) *, html:not([data-motion]) *::before", css)
        script = static_text("core/js/app.js")
        self.assertIn("? 'calmo' : 'vivo'", script)
        self.assertIn("const still = () => root.dataset.motion === 'sem';", script)
        self.assertIn("root.dataset.motion = mode;", script)

    def test_head_script_marks_motion_before_paint(self):
        page = self.client.get(reverse("accounts:login"))
        self.assertContains(page, "matchMedia('(prefers-reduced-motion: reduce)').matches?'calmo':'vivo'")
        self.assertContains(page, "document.documentElement.dataset.motion=m")

    def test_more_live_elements(self):
        css = static_text("core/css/app.css")
        layer = css[css.index("Sprint 45 — mais vida"):]
        for piece in ("fs-swing", "fs-logo-glow", "fs-eq", "fs-shine", "fs-bob"):
            self.assertIn(piece, layer)
        self.assertNotIn("!important", layer)
