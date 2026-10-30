from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .models import AttendanceRecord, Booking, ContactInquiry, Equipment, FitnessClass, MembershipPlan, NewsletterSignup, Payment, SitePage, Subscription, Trainer, User


class RegistrationForm(UserCreationForm):
    full_name = forms.CharField(max_length=150, label="Full Name", widget=forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Enter your full name"}))
    username = forms.CharField(required=False, widget=forms.HiddenInput)
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "Enter your email"}))
    phone = forms.CharField(required=False, label="Phone Number", widget=forms.TextInput(attrs={"autocomplete": "tel", "placeholder": "Enter your phone number"}))
    terms_accepted = forms.BooleanField(required=True, label="I agree to the Terms of Service and Privacy Policy")

    class Meta:
        model = User
        fields = ("username", "email", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"autocomplete": "new-password", "placeholder": "Create a password"})
        self.fields["password2"].widget.attrs.update({"autocomplete": "new-password", "placeholder": "Confirm your password"})

    def clean(self):
        cleaned = super().clean()
        full_name = " ".join(cleaned.get("full_name", "").split())
        if full_name:
            names = full_name.split(" ", 1)
            self.instance.first_name = names[0]
            self.instance.last_name = names[1] if len(names) > 1 else ""

        email = cleaned.get("email", "")
        if email:
            base_username = slugify(email.partition("@")[0])[:120] or "member"
            username = base_username
            suffix = 1
            while User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
                suffix += 1
                username = f"{base_username[:120 - len(str(suffix))]}{suffix}"
            cleaned["username"] = username
        return cleaned

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account already uses this email address. Try logging in instead.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Roles.MEMBER
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email", "placeholder": "you@example.com"}),
    )

    def clean(self):
        email = self.cleaned_data.get("username")
        if email:
            matching_users = User.objects.filter(email__iexact=email)
            if matching_users.count() == 1:
                self.cleaned_data["username"] = matching_users.get().get_username()
        return super().clean()


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"placeholder": "Your name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "you@example.com"}))
    phone = forms.CharField(max_length=24, required=False, widget=forms.TextInput(attrs={"placeholder": "Phone (optional)"}))
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Tell us what you are looking for..."}))


class NewsletterForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "Enter your email", "autocomplete": "email", "aria-label": "Email address"}))


class MemberForm(forms.ModelForm):
    initial_password = forms.CharField(required=False, label="Initial password", widget=forms.PasswordInput, help_text="Required for a new member. Leave blank when editing.")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "is_active")

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk is None and not cleaned.get("initial_password"):
            self.add_error("initial_password", "Set an initial password for this member.")
        if cleaned.get("initial_password"):
            try:
                validate_password(cleaned["initial_password"], self.instance)
            except ValidationError as error:
                self.add_error("initial_password", error)
        email = cleaned.get("email", "").strip()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            self.add_error("email", "An account already uses this email address.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Roles.MEMBER
        if self.cleaned_data.get("initial_password"):
            user.set_password(self.cleaned_data["initial_password"])
        elif not user.pk:
            user.set_unusable_password()
        if commit:
            user.save()
        return user


class AccountForm(forms.ModelForm):
    initial_password = forms.CharField(required=False, label="Initial password", widget=forms.PasswordInput, help_text="Required for a new account. Leave blank to keep the current password.")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "role", "is_active")

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk is None and not cleaned.get("initial_password"):
            self.add_error("initial_password", "Set an initial password for this account.")
        if cleaned.get("initial_password"):
            try:
                validate_password(cleaned["initial_password"], self.instance)
            except ValidationError as error:
                self.add_error("initial_password", error)
        email = cleaned.get("email", "").strip()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            self.add_error("email", "An account already uses this email address.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("initial_password")
        if password:
            user.set_password(password)
        elif not user.pk:
            user.set_unusable_password()
        if commit:
            user.save()
        return user


class TrainerForm(forms.ModelForm):
    class Meta:
        model = Trainer
        fields = ("name", "email", "specialties", "bio", "years_experience", "photo_url", "user", "active")
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(role=User.Roles.TRAINER)
        self.fields["user"].required = False


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ("name", "brand", "quantity", "category", "image_url", "description", "active", "sort_order")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class FitnessClassForm(forms.ModelForm):
    class Meta:
        model = FitnessClass
        fields = ("title", "category", "trainer", "description", "starts_at", "duration_minutes", "capacity", "level", "active")
        widgets = {"starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"), "description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["starts_at"].input_formats = ["%Y-%m-%dT%H:%M"]


class MembershipPlanForm(forms.ModelForm):
    features_text = forms.CharField(required=False, label="Plan features", help_text="One feature per line", widget=forms.Textarea(attrs={"rows": 4}))

    class Meta:
        model = MembershipPlan
        fields = ("name", "slug", "price", "duration_days", "description", "popular", "active", "sort_order")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["features_text"].initial = "\n".join(self.instance.features or [])

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.features = [line.strip() for line in self.cleaned_data.get("features_text", "").splitlines() if line.strip()]
        if commit:
            instance.save()
        return instance


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ("member", "fitness_class", "status")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["member"].queryset = User.objects.filter(role=User.Roles.MEMBER).order_by("first_name", "last_name")
        self.fields["fitness_class"].queryset = FitnessClass.objects.order_by("starts_at")


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ("member", "checked_in_at", "checked_out_at", "note")
        widgets = {
            "checked_in_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "checked_out_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["member"].queryset = User.objects.filter(role=User.Roles.MEMBER).order_by("first_name", "last_name")
        self.fields["checked_in_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["checked_out_at"].input_formats = ["%Y-%m-%dT%H:%M"]


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ("member", "plan", "amount", "status", "method", "reference", "paid_at")
        widgets = {"paid_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["member"].queryset = User.objects.filter(role=User.Roles.MEMBER).order_by("first_name", "last_name")
        self.fields["plan"].required = False
        self.fields["paid_at"].input_formats = ["%Y-%m-%dT%H:%M"]


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ("member", "plan", "started_at", "ends_at", "active")
        widgets = {
            "started_at": forms.DateInput(attrs={"type": "date"}),
            "ends_at": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["member"].queryset = User.objects.filter(role=User.Roles.MEMBER).order_by("first_name", "last_name")


class ContactInquiryForm(forms.ModelForm):
    class Meta:
        model = ContactInquiry
        fields = ("name", "email", "phone", "message", "resolved")
        widgets = {"message": forms.Textarea(attrs={"rows": 5})}


class NewsletterSignupForm(forms.ModelForm):
    class Meta:
        model = NewsletterSignup
        fields = ("email", "active")


class SitePageForm(forms.ModelForm):
    class Meta:
        model = SitePage
        fields = ("slug", "name", "hero_title", "hero_subtitle", "body", "active")
        widgets = {
            "hero_subtitle": forms.Textarea(attrs={"rows": 3}),
            "body": forms.Textarea(attrs={"rows": 6}),
        }
