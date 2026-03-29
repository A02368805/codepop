from django import forms


class SupplyUsageImportForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if not uploaded_file.name.lower().endswith(".csv"):
            raise forms.ValidationError("Upload a CSV file.")
        return uploaded_file


class RepairStatusImportForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if not uploaded_file.name.lower().endswith(".csv"):
            raise forms.ValidationError("Upload a CSV file.")
        return uploaded_file
