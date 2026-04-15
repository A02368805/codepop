from django import forms


class InventoryAdjustmentForm(forms.Form):
    delta = forms.DecimalField(decimal_places=2, max_digits=12, required=False)
    count = forms.DecimalField(
        decimal_places=2,
        max_digits=12,
        required=False,
        min_value=0,
    )
    reason = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        delta = cleaned_data.get("delta")
        count = cleaned_data.get("count")
        reason = (cleaned_data.get("reason") or "").strip()
        cleaned_data["reason"] = reason

        # A set-count target takes precedence over delta validation.
        if count is not None:
            return cleaned_data

        if delta is None:
            self.add_error("delta", "Enter a change amount or set-count target.")
            return cleaned_data

        if delta == 0:
            self.add_error("delta", "Enter a non-zero adjustment.")
        if delta is not None and abs(delta) > 5000:
            self.add_error(
                "delta",
                "Adjustments over 5000 units must be handled through a supply workflow.",
            )
        return cleaned_data
