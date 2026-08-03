# Design: User Settings Page

## Overview

Implement a user settings page for profile management, champion prediction, and theme toggle. Add password reset functionality to the login page using Django's built-in auth views.

## Architecture

### Component Structure

```
User Settings Page (/settings/)
├── Profile Section
│   ├── Email field (editable)
│   └── Username field (editable, max 20 chars)
├── Champion Prediction Section
│   ├── Team dropdown (all teams)
│   └── Lock status indicator
└── Theme Section
    └── Dark/Light toggle switch

Login Page (/login/)
└── "Passwort vergessen?" link
    └── Password Reset Flow (Django built-in)
```

### Data Flow

```
User Settings View (GET)
    │
    ├─► Load current user data
    ├─► Load all teams for champion dropdown
    ├─► Check if champion can still be changed
    └─► Render settings form

User Settings View (POST)
    │
    ├─► Validate email (format, not already taken)
    ├─► Validate username (max 20 chars, unique)
    ├─► Validate champion (team exists, deadline not passed)
    └─► Save and redirect with success message

Theme Toggle (Client-side)
    │
    ├─► Toggle dark class on HTML element
    ├─► Save preference to localStorage
    └─► (Optional) Save to user profile via HTMX
```

## Implementation Details

### 1. Model Changes (users/models.py)

Add theme preference field to User model:

```python
class User(AbstractUser):
    # ... existing fields ...
    
    theme_preference: models.CharField = models.CharField(
        max_length=10,
        choices=[('light', 'Light'), ('dark', 'Dark'), ('system', 'System')],
        default='system',
        help_text="User's preferred color theme"
    )
```

### 2. URL Configuration

**users/urls.py:**

```python
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('settings/', views.UserSettingsView.as_view(), name='settings'),
]
```

**tipapp/urls.py (password reset):**

```python
from django.contrib.auth import views as auth_views

urlpatterns = [
    # ... existing ...
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset_form.html',
             email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt',
             success_url='/password-reset/done/'
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html',
             success_url='/password-reset-complete/'
         ), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]
```

### 3. View Implementation (users/views.py)

```python
from django.views.generic.edit import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils import timezone

from .forms import UserSettingsForm
from .models import User
from matches.models import Team, Match


class UserSettingsView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """View for users to manage their profile settings."""
    
    model = User
    form_class = UserSettingsForm
    template_name = 'users/settings.html'
    success_url = reverse_lazy('users:settings')
    success_message = "Einstellungen gespeichert!"
    
    def get_object(self):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['teams'] = Team.objects.all().order_by('name')
        context['can_change_champion'] = self.can_change_champion()
        return context
    
    def can_change_champion(self) -> bool:
        """Check if champion prediction can still be changed."""
        first_match = Match.objects.order_by('kickoff').first()
        if not first_match:
            return True
        return timezone.now() < first_match.kickoff
```

### 4. Form Implementation (users/forms.py)

```python
from django import forms
from django.core.validators import MaxLengthValidator
from .models import User
from matches.models import Team


class UserSettingsForm(forms.ModelForm):
    """Form for editing user profile settings."""
    
    username = forms.CharField(
        max_length=20,
        validators=[MaxLengthValidator(20)],
        help_text="Max. 20 Zeichen",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'maxlength': '20'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-input'})
    )
    
    predicted_champion = forms.ModelChoiceField(
        queryset=Team.objects.all().order_by('name'),
        required=False,
        empty_label="-- Team wählen --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    theme_preference = forms.ChoiceField(
        choices=[('light', 'Hell'), ('dark', 'Dunkel'), ('system', 'System')],
        widget=forms.RadioSelect(attrs={'class': 'form-radio'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'predicted_champion', 'theme_preference']
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if len(username) > 20:
            raise forms.ValidationError("Username darf max. 20 Zeichen haben.")
        
        # Check uniqueness (excluding current user)
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Dieser Username ist bereits vergeben.")
        
        return username
    
    def clean_email(self):
        email = self.cleaned_data['email']
        
        # Check uniqueness (excluding current user)
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Diese E-Mail ist bereits vergeben.")
        
        return email
```

### 5. Template Structure

**templates/users/settings.html:**

```html
{% extends "base.html" %}
{% block title %}Einstellungen - WM 2026 Tippspiel{% endblock %}

{% block content %}
<main class="max-w-2xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">Einstellungen</h1>
    
    {% if messages %}
    <div class="mb-6">
        {% for message in messages %}
        <div class="p-4 rounded-lg {% if message.tags == 'success' %}bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200{% else %}bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200{% endif %}">
            {{ message }}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    <form method="post" class="space-y-8">
        {% csrf_token %}
        
        <!-- Profile Section -->
        <section class="bg-white dark:bg-zinc-800 rounded-xl p-6 shadow-sm border border-zinc-200 dark:border-zinc-700">
            <h2 class="text-lg font-semibold mb-4">Profil</h2>
            
            <div class="space-y-4">
                <div>
                    <label for="id_username" class="block text-sm font-medium mb-1">Username</label>
                    {{ form.username }}
                    {% if form.username.errors %}
                        <p class="text-red-600 text-sm mt-1">{{ form.username.errors.0 }}</p>
                    {% endif %}
                    <p class="text-zinc-500 text-sm mt-1">{{ form.username.help_text }}</p>
                </div>
                
                <div>
                    <label for="id_email" class="block text-sm font-medium mb-1">E-Mail</label>
                    {{ form.email }}
                    {% if form.email.errors %}
                        <p class="text-red-600 text-sm mt-1">{{ form.email.errors.0 }}</p>
                    {% endif %}
                </div>
            </div>
        </section>
        
        <!-- Champion Prediction Section -->
        <section class="bg-white dark:bg-zinc-800 rounded-xl p-6 shadow-sm border border-zinc-200 dark:border-zinc-700">
            <h2 class="text-lg font-semibold mb-4">Weltmeister-Tipp</h2>
            
            {% if can_change_champion %}
                <div>
                    <label for="id_predicted_champion" class="block text-sm font-medium mb-1">Dein Tipp</label>
                    {{ form.predicted_champion }}
                    <p class="text-zinc-500 text-sm mt-1">Kann nur vor dem ersten Spiel geändert werden.</p>
                </div>
            {% else %}
                <div class="flex items-center gap-2 text-zinc-500">
                    <span>🔒</span>
                    <span>
                        {% if user.predicted_champion %}
                            Dein Tipp: <strong>{{ user.predicted_champion.name }}</strong>
                        {% else %}
                            Kein Tipp abgegeben (nicht mehr änderbar)
                        {% endif %}
                    </span>
                </div>
            {% endif %}
        </section>
        
        <!-- Theme Section -->
        <section class="bg-white dark:bg-zinc-800 rounded-xl p-6 shadow-sm border border-zinc-200 dark:border-zinc-700">
            <h2 class="text-lg font-semibold mb-4">Darstellung</h2>
            
            <fieldset>
                <legend class="sr-only">Theme wählen</legend>
                <div class="flex gap-6">
                    {% for radio in form.theme_preference %}
                    <label class="flex items-center gap-2 cursor-pointer">
                        {{ radio.tag }}
                        <span>{{ radio.choice_label }}</span>
                    </label>
                    {% endfor %}
                </div>
            </fieldset>
        </section>
        
        <!-- Submit -->
        <div class="flex justify-end">
            <button type="submit" class="px-6 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg transition-colors">
                Speichern
            </button>
        </div>
    </form>
</main>
{% endblock %}
```

### 6. Password Reset Templates

Create templates in `templates/registration/`:

- `password_reset_form.html` - Enter email
- `password_reset_done.html` - Email sent confirmation
- `password_reset_email.html` - Email content
- `password_reset_subject.txt` - Email subject
- `password_reset_confirm.html` - Enter new password
- `password_reset_complete.html` - Success confirmation

### 7. Login Template Update

Add link to `templates/login.html`:

```html
<p class="text-center mt-4">
    <a href="{% url 'password_reset' %}" class="text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 text-sm">
        Passwort vergessen?
    </a>
</p>
```

### 8. Navigation Update

Add settings link to `templates/base.html` header:

```html
<a href="{% url 'users:settings' %}" class="text-zinc-600 dark:text-zinc-300 hover:text-emerald-600">
    ⚙️
</a>
```

## Theme Sync Logic

When theme is changed via settings form:
1. Server saves `theme_preference` to database
2. After form submit, JavaScript reads the saved value and applies it
3. Also updates localStorage for consistency

```javascript
// On settings page load, sync server preference to client
document.addEventListener('DOMContentLoaded', function() {
    const serverTheme = document.body.dataset.userTheme;
    if (serverTheme && serverTheme !== 'system') {
        localStorage.setItem('darkMode', serverTheme === 'dark' ? 'true' : 'false');
        document.documentElement.classList.toggle('dark', serverTheme === 'dark');
    }
});
```

## Edge Cases

1. **Email already taken**: Show form error, don't save
2. **Username too long**: Client-side maxlength + server validation
3. **Username already taken**: Show form error
4. **Champion deadline passed**: Disable dropdown, show lock icon
5. **No teams in database**: Show "Keine Teams verfügbar" message
6. **Invalid password reset token**: Show error with link to try again

## Dependencies

- Django's built-in auth views for password reset
- Django messages framework for success/error feedback
- Existing Tailwind CSS classes
- No new Python packages required

## Email Configuration

For password reset to work, email settings must be configured:

```python
# settings.py (development)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# settings.py (production)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')
```
