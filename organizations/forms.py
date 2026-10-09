from django import forms
from django.db import models

from .models import Organization, Sector


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ("name", "is_active")


class SectorForm(forms.ModelForm):
    class Meta:
        model = Sector
        fields = ("organization", "name", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Organization.objects.filter(is_active=True)
        if self.instance and self.instance.pk:
            queryset = Organization.objects.filter(
                models.Q(is_active=True) | models.Q(pk=self.instance.organization_id)
            )
        self.fields["organization"].queryset = queryset.order_by("name")
