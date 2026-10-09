from django import forms

from .models import SpreadsheetImport
from .services import ENTITY_FIELDS, MAX_UPLOAD_BYTES


class ImportUploadForm(forms.Form):
    entity_type = forms.ChoiceField(label="Dados que serão importados", choices=SpreadsheetImport.EntityType.choices)
    file = forms.FileField(label="Planilha CSV ou XLSX")

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        suffix = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""
        if suffix not in {"csv", "xlsx"}:
            raise forms.ValidationError("Envie um arquivo CSV ou XLSX.")
        if uploaded.size > MAX_UPLOAD_BYTES:
            raise forms.ValidationError("O arquivo excede o limite de 5 MB.")
        return uploaded


class ImportMappingForm(forms.Form):
    sheet = forms.ChoiceField(label="Aba ou conjunto de dados")

    def __init__(self, *args, spreadsheet_import, selected_sheet=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.spreadsheet_import = spreadsheet_import
        source = spreadsheet_import.source_data
        self.fields["sheet"].choices = [(name, name) for name in source]
        selected = self.data.get("sheet") if self.is_bound else selected_sheet or next(iter(source), "")
        self.initial["sheet"] = selected
        headers = source.get(selected, {}).get("headers", [])
        choices = [("", "— não mapear —"), *((header, header) for header in headers)]
        for definition in ENTITY_FIELDS[spreadsheet_import.entity_type]:
            field_name = f"field_{definition['name']}"
            self.fields[field_name] = forms.ChoiceField(
                label=definition["label"], choices=choices, required=definition["required"],
            )
            automatic = definition["aliases"] & {header.casefold() for header in headers}
            if automatic:
                folded = next(iter(automatic))
                self.initial[field_name] = next(header for header in headers if header.casefold() == folded)

    def mapping(self):
        return {
            definition["name"]: self.cleaned_data.get(f"field_{definition['name']}", "")
            for definition in ENTITY_FIELDS[self.spreadsheet_import.entity_type]
        }
