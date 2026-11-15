"""Sprint 46: lupa do logotipo escaneando, sem mudar o desenho, e parada quando pedem menos movimento."""

import re

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


def static_text(path):
    return open(finders.find(path), encoding="utf-8").read()


class LogoEscaneandoTests(TestCase):
    def test_scan_effect_lives_inside_logo_and_respects_reduced_motion(self):
        logo = static_text("core/img/logo.svg")
        for piece in ('class="beam"', 'class="glass"', "infinite alternate", "@media (prefers-reduced-motion:reduce)"):
            self.assertIn(piece, logo)

    def test_static_version_keeps_the_same_drawing(self):
        live = static_text("core/img/logo.svg")
        still = static_text("core/img/logo-estatico.svg")
        self.assertNotIn("<style>", still)
        self.assertNotIn("animation", still)
        for shape in ('viewBox="0 0 48 48"', 'd="M15.5 21.5l4 4 7.5-8"', 'd="M30 30l9 9"', 'r="11.5"', 'rx="12"'):
            self.assertIn(shape, live)
            self.assertIn(shape, still)

    def test_header_uses_picture_with_still_source(self):
        page = self.client.get(reverse("accounts:login"))
        self.assertContains(page, 'class="brand-picture"')
        self.assertContains(page, 'media="(prefers-reduced-motion: reduce)"')
        self.assertTrue(re.search(r"logo-estatico[^\"]*\.svg", page.content.decode()))
        css = static_text("core/css/app.css")
        self.assertIn(".brand-picture { display: contents; }", css)
        self.assertIn("img.dataset.liveSrc", static_text("core/js/app.js"))
