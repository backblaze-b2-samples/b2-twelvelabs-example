from django import forms


class ResultForm(forms.Form):
    id = forms.IntegerField()
