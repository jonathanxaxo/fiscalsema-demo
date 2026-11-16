"""Sprints 46 e 53: lupa escaneando nos modos Vivo/Calmo e parada somente no modo Sem."""

import re

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


def static_text(path):
    return open(finders.find(path), encoding="utf-8").read()


class LogoEscaneandoTests(TestCase):
    def test_scan_effect_lives_inside_logo_including_calm_mode(self):
        logo = static_text("core/img/logo.svg")
        for piece in ('class="beam"', 'class="glass"', "infinite alternate"):
            self.assertIn(piece, logo)
        self.assertNotIn("prefers-reduced-motion", logo)

    def test_static_version_keeps_the_same_drawing(self):
        live = static_text("core/img/logo.svg")
        still = static_text("core/img/logo-estatico.svg")
        self.assertNotIn("<style>", still)
        self.assertNotIn("animation", still)
        for shape in ('viewBox="0 0 48 48"', 'd="M15.5 21.5l4 4 7.5-8"', 'd="M30 30l9 9"', 'r="11.5"', 'rx="12"'):
            self.assertIn(shape, live)
            self.assertIn(shape, still)

    def test_header_uses_static_logo_only_for_explicit_no_motion_mode(self):
        page = self.client.get(reverse("accounts:login"))
        self.assertContains(page, 'class="brand-picture"')
        self.assertContains(page, 'data-still-src=')
        self.assertNotContains(page, 'media="(prefers-reduced-motion: reduce)"')
        self.assertTrue(re.search(r'data-still-src="[^"]*logo-estatico[^\"]*\.svg', page.content.decode()))
        css = static_text("core/css/app.css")
        self.assertIn(".brand-picture { display: contents; }", css)
        self.assertNotIn("@media (prefers-reduced-motion: reduce) { .brand-mark", css)
        self.assertIn("img.dataset.liveSrc", static_text("core/js/app.js"))
        self.assertIn("img?.dataset.stillSrc", static_text("core/js/app.js"))
