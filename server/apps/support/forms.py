from django import forms


class SupportMessageForm(forms.Form):
    message = forms.CharField(
        max_length=1000,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": (
                    "Ask about order status, pickup timing, guest lookup, refunds, "
                    "account help, or what FloatStack is."
                ),
            }
        ),
    )


class SupportEscalationForm(forms.Form):
    summary = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={"rows": 4}))
    contact_email = forms.EmailField(required=False)
