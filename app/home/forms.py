from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(max_length=32)
    reason = forms.CharField(max_length=32)
    message = forms.CharField()
