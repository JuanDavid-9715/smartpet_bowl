from django import forms
from django.db.models import Q

from .models import Feeder, Pet


class PetForm(forms.ModelForm):
    feeder = forms.ModelChoiceField(
        queryset=Feeder.objects.none(),
        required=False,
        label="Plato ya vinculado",
        empty_label="Elegir un plato de la lista",
        help_text="Solo aparecen los platos libres de tu cuenta.",
    )
    new_feeder_code = forms.CharField(
        label="O vincula un plato nuevo",
        max_length=12,
        required=False,
        help_text="Va impreso en la etiqueta debajo del plato. Cada mascota tiene el suyo.",
    )

    class Meta:
        model = Pet
        fields = ["name", "species", "breed", "birth_date", "weight_kg", "kcal_per_gram", "profile", "meals_per_day"]
        widgets = {"birth_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "field-input")

        libres = Feeder.objects.none()
        if self.user is not None:
            base = Feeder.objects.filter(owner=self.user)
            if self.instance.pk:
                libres = base.filter(Q(pets__isnull=True) | Q(pets=self.instance))
            else:
                libres = base.filter(pets__isnull=True)
        self.fields["feeder"].queryset = libres.distinct()

        if self.instance.pk and self.instance.feeder_id:
            self.fields["feeder"].initial = self.instance.feeder_id

    def clean(self):
        data = super().clean()
        chosen = data.get("feeder")
        new_code = (data.get("new_feeder_code") or "").strip().upper()
        tiene_actual = bool(self.instance.pk and self.instance.feeder_id)
        if not chosen and not new_code and not tiene_actual:
            raise forms.ValidationError("Elige un plato de la lista o vincula uno nuevo.")
        if chosen and new_code:
            raise forms.ValidationError("Elige uno: o un plato de la lista o uno nuevo, no los dos.")
        if new_code:
            data["new_feeder_code"] = new_code
        return data


class PetPhotoForm(forms.Form):
    front = forms.ImageField(label="Frente al plato", required=False)
    eating = forms.ImageField(label="Comiendo", required=False)
    top = forms.ImageField(label="Desde arriba", required=False)
