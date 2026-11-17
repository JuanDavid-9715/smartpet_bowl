from django import forms

from .models import Pet


class PetForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ["name", "species", "breed", "birth_date", "weight_kg", "kcal_per_gram", "profile", "meals_per_day", "feeder", "photo"]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "field-input")
