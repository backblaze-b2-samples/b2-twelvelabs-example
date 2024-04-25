from django import forms


class ResultForm(forms.Form):
    """
    Used in the search result page to receive the clip data.
    """
    id = forms.IntegerField()
    query = forms.CharField()
    clips = forms.CharField()
