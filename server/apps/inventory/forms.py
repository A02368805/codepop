from django import forms


class InventoryAdjustmentForm(forms.Form):
    delta = forms.DecimalField(decimal_places=2, max_digits=12)
    reason = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        delta = cleaned_data.get("delta")
        reason = (cleaned_data.get("reason") or "").strip()
        if delta in {None, 0}:
            self.add_error("delta", "Enter a non-zero adjustment.")
        if delta is not None and abs(delta) > 5000:
            self.add_error(
                "delta",
                "Adjustments over 5000 units must be handled through a supply workflow.",
            )
        if delta not in {None, 0} and not reason:
            self.add_error("reason", "Provide a reason for the inventory adjustment.")
        return cleaned_data
