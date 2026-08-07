# QA/forms.py
from django import forms
from .models import Question, QuestionCategory, Subject, Topic, Part

class AdvancedQuestionFilterForm(forms.Form):
    """Advanced filter form for questions"""
    
    # Date Range
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 w-full'
        }),
        label='From Date'
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 w-full'
        }),
        label='To Date'
    )
    
    # Categories (Multiple Select)
    categories = forms.ModelMultipleChoiceField(
        queryset=QuestionCategory.objects.filter(is_active=True),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 w-full',
            'size': '6'
        }),
        label='Select Categories'
    )
    
    # Subject Filter
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(is_active=True),
        required=False,
        empty_label="All Subjects",
        widget=forms.Select(attrs={
            'class': 'form-select rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 w-full'
        }),
        label='Subject'
    )
    
    # Topic Filter (dynamic, depends on subject)
    topic = forms.ModelChoiceField(
        queryset=Topic.objects.filter(is_active=True),
        required=False,
        empty_label="All Topics",
        widget=forms.Select(attrs={
            'class': 'form-select rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 w-full'
        }),
        label='Topic'
    )
    
    # Part Filter (dynamic, depends on topic)
    part = forms.ModelChoiceField(
        queryset=Part.objects.filter(is_active=True),
        required=False,
        empty_label="All Parts",
        widget=forms.Select(attrs={
            'class': 'form-select rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 w-full'
        }),
        label='Part'
    )
    
    # Question Type
    question_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Question.QUESTION_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 w-full'
        }),
        label='Question Type'
    )
    
    # Difficulty
    difficulty = forms.ChoiceField(
        choices=[('', 'All Difficulties')] + list(Question.DIFFICULTY_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 w-full'
        }),
        label='Difficulty Level'
    )
    
    # Tags (comma separated)
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 w-full',
            'placeholder': 'e.g., important, repeated, tricky'
        }),
        label='Tags (comma separated)'
    )
    
    # Search Text
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input rounded-lg border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 w-full',
            'placeholder': 'Search in questions and answers...'
        }),
        label='Search'
    )
    
    # Featured Only
    featured_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-5 w-5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500'
        }),
        label='Featured Only'
    )
    
    def clean_tags(self):
        tags = self.cleaned_data.get('tags', '')
        if tags:
            return [tag.strip() for tag in tags.split(',') if tag.strip()]
        return []
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            self.add_error('date_to', 'End date must be after start date.')
        
        return cleaned_data