from django.test import SimpleTestCase

from .forms import (
    AdministrativeFiscalCreationForm,
    FiscalRegistrationForm,
    GoogleSignupForm,
    UserProfileChangeForm,
)
from .models import REGISTRATION_PROFILE_CHOICES, UserProfile


class FunctionalProfileFormTests(SimpleTestCase):
    def test_public_registration_exposes_only_four_requestable_profiles(self):
        expected = {
            UserProfile.FISCAL_TITULAR,
            UserProfile.AUXILIARY_ADMINISTRATIVE,
            UserProfile.ADMINISTRATIVE_MANAGER,
            UserProfile.CONTRACT_MANAGER,
        }
        self.assertEqual({value for value, _label in REGISTRATION_PROFILE_CHOICES}, expected)
        for form_class in (FiscalRegistrationForm, GoogleSignupForm):
            choices = {value for value, _label in form_class().fields["requested_profile"].choices}
            self.assertEqual(choices, expected)
            self.assertNotIn(UserProfile.ADMINISTRATOR_GENERAL, choices)
            self.assertNotIn(UserProfile.CONSULTATION, choices)

    def test_fiscal_substitute_is_not_a_profile(self):
        self.assertNotIn("FISCAL_SUBSTITUTO", UserProfile.values)

    def test_administrator_forms_do_not_offer_legacy_consultation_profile(self):
        for form_class in (AdministrativeFiscalCreationForm, UserProfileChangeForm):
            choices = {value for value, _label in form_class().fields["profile"].choices}
            self.assertIn(UserProfile.ADMINISTRATOR_GENERAL, choices)
            self.assertNotIn(UserProfile.CONSULTATION, choices)
