from django import forms

from .models import Pet


class PetForm(forms.ModelForm):
    feeder_code = forms.CharField(
        label="Codigo del plato",
        max_length=12,
        help_text="Va impreso en la etiqueta debajo del plato. Cada mascota tiene el suyo.",
    )

    class Meta:
        model = Pet
        fields = ["name", "species", "breed", "birth_date", "weight_kg", "kcal_per_gram", "profile", "meals_per_day"]
        widgets = {"birth_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "field-input")
        if self.instance.pk and self.instance.feeder:
            self.fields["feeder_code"].initial = self.instance.feeder.code


class PetPhotoForm(forms.Form):
    front = forms.ImageField(label="Frente al plato", required=False)
    eating = forms.ImageField(label="Comiendo", required=False)
    top = forms.ImageField(label="Desde arriba", required=False)
