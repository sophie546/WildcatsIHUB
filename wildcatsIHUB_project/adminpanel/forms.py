from django import forms
from django.contrib.auth.models import User
from accounts.models import UserProfile 
from projects.models import Project, Category

class ProjectForm(forms.ModelForm):
    # Dynamic Category Dropdown
    category_select = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="Select Category (or type below)",
        required=False,
        widget=forms.Select(attrs={'class': 'form-input'}),
        label="Choose Existing Category"
    )

    class Meta:
        model = Project
        # Exclude fields handled automatically to prevent validation errors
        exclude = ['author', 'created_at', 'approved_at', 'approved_by']
        
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 5}),
            # Keep text input for manual override
            'category': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Or type a new category here...'}),
            'tech_used': forms.TextInput(attrs={'class': 'form-input'}),
            'github_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://github.com/...'}),
            'live_demo': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
            'video_demo': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://youtube.com/...'}),
            'status': forms.Select(attrs={'class': 'form-input'}),
            'likes': forms.NumberInput(attrs={'class': 'form-input'}),
            'views': forms.NumberInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-select the category in dropdown if it matches a database entry
        if self.instance.pk and self.instance.category:
            try:
                cat = Category.objects.get(name=self.instance.category)
                self.fields['category_select'].initial = cat
            except Category.DoesNotExist:
                pass

    def clean(self):
        cleaned_data = super().clean()
        # If admin picked a dropdown option, override the text box
        cat_select = cleaned_data.get('category_select')
        if cat_select:
            cleaned_data['category'] = cat_select.name
        return cleaned_data

class UserProfileEditForm(forms.ModelForm):
    """Form for editing related UserProfile data."""
    class Meta:
        model = UserProfile
        fields = ['department', 'year_level', 'student_id']
        widgets = {
            'department': forms.TextInput(attrs={'class': 'form-input'}),
            
            # Change to a Dropdown (Select) with specific choices
            'year_level': forms.Select(
                choices=[
                    ('', 'Select Year Level'), 
                    ('1st Year', '1st Year'),
                    ('2nd Year', '2nd Year'),
                    ('3rd Year', '3rd Year'),
                    ('4th Year', '4th Year'),
                    ('5th Year', '5th Year'),
                ],
                attrs={'class': 'form-input'}
            ),
            
            'student_id': forms.TextInput(attrs={'class': 'form-input'}),
        }

class UserManagementForm(forms.ModelForm):
    """Form for editing basic Django User attributes via Admin Panel."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active', 'is_staff']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

class AdminUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
        }
        
class AdminProfileForm(forms.ModelForm):
    """Form to edit the related UserProfile model fields."""
    class Meta:
        model = UserProfile
        fields = ['avatar']
