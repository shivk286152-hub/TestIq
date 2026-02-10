from django import forms
from .models import Profile

STATE_CHOICES = [
    ("", "Select State"),
    ("Andhra Pradesh", "Andhra Pradesh"),
    ("Bihar", "Bihar"),
    ("Delhi", "Delhi"),
    ("Gujarat", "Gujarat"),
    ("Karnataka", "Karnataka"),
    ("Maharashtra", "Maharashtra"),
    ("Tamil Nadu", "Tamil Nadu"),
    ("Uttar Pradesh", "Uttar Pradesh"),
    ("West Bengal", "West Bengal"),
]

INPUT_CLASSES = (
    "w-full px-3 py-2 border border-gray-300 rounded-lg "
    "focus:outline-none focus:ring-2 focus:ring-blue-500 "
    "focus:border-blue-500 hover:border-gray-400 transition"
)

class ProfileForm(forms.ModelForm):
    state = forms.ChoiceField(choices=STATE_CHOICES, required=False)
    class Meta:
        model = Profile
        fields = [
            'name',
            'phone',
            'email',
            'profile_pic',
            'city',
            'state',
            'pincode',
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Enter your full name",
            }),
            "email": forms.EmailInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Enter your email address",
            }),
            "phone": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Optional",
            }),
            "pincode": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "e.g. 110001",
            }),
            "city": forms.TextInput(attrs={
                "class": INPUT_CLASSES,
                "placeholder": "City",
            }),
        }
