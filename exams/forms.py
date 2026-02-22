# forms.py
from django import forms
from .models import Testimonial

class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ['text', 'stars', 'achievement']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'rows': 4,
                'placeholder': 'Share your experience with our platform...'
            }),
            'stars': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500'
            }),
            'achievement': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
                'placeholder': 'e.g., Selected in UPSC 2023, Scored 95% in JEE'
            }),
        }
        labels = {
            'text': 'Your Testimonial',
            'stars': 'Rating',
            'achievement': 'Your Achievement (Optional)',
        }