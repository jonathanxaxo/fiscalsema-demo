from django import forms


AUDIT_CATEGORIES = (
    ("", "Todas"),
    ("CONTRATO", "Contrato"),
    ("ITEM", "Item"),
    ("EMPENHO", "Empenho"),
    ("RATEIO", "Rateio"),
    ("OS", "Ordem de Serviço"),
    ("EXECUCAO", "Execução"),
    ("NF", "Nota Fiscal"),
    ("PAGAMENTO", "Pagamento"),
    ("COMPARTILHAMENTO", "Compartilhamento"),
    ("SUBSTITUICAO_FISCAL", "Substituição de Fiscal"),
    ("DOCUMENTO", "Documento"),
    ("IMPORTACAO", "Importação"),
    ("EXPORTACAO", "Exportação"),
    ("INTELIGENCIA_CONTRATUAL", "Inteligência contratual"),
    ("AUTENTICACAO", "Autenticação"),
    ("ORGANIZACAO", "Organização"),
    ("API", "API"),
    ("ASSISTENTE_IA", "Assistente IA"),
)


class AuditFilterForm(forms.Form):
    categoria = forms.ChoiceField(choices=AUDIT_CATEGORIES, required=False)
    usuario = forms.CharField(required=False, max_length=200)
    inicio = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    fim = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("inicio") and cleaned.get("fim") and cleaned["fim"] < cleaned["inicio"]:
            self.add_error("fim", "A data final não pode anteceder a data inicial.")
        return cleaned
