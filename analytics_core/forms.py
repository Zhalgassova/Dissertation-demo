from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import AnalysisDataset


class DatasetUploadForm(forms.ModelForm):
    title = forms.CharField(
        label="������ �����",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "������: 2 ����, ���, �����������"}
        ),
    )
    teacher_name = forms.CharField(
        label="�?� �??���",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "�??����? ���-�?�"}
        ),
    )
    subject_title = forms.CharField(
        label="�?� �����",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "�?� ������ ����?��"}
        ),
    )
    cohort_label = forms.CharField(
        label="�?� ��������",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "������: 2 ����, ���� ����"}
        ),
    )
    notes = forms.CharField(
        label="?��?��� �������",
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control", "rows": 3, "placeholder": "?������ �?�������"}
        ),
    )

    class Meta:
        model = AnalysisDataset
        fields = ["source_file"]
        labels = {"source_file": "CSV ������ Excel �����"}
        widgets = {"source_file": forms.FileInput(attrs={"class": "form-control"})}

    def clean_source_file(self):
        uploaded = self.cleaned_data["source_file"]
        allowed = {".csv", ".xlsx", ".xls", ".xlsm"}
        suffix = ""
        if "." in uploaded.name:
            suffix = uploaded.name[uploaded.name.rfind(".") :].lower()
        if suffix not in allowed:
            raise forms.ValidationError(
                "CSV ������ Excel ������ �?���?�� (.csv, .xlsx, .xls, .xlsm)."
            )
        return uploaded


class TeacherStudentCommentForm(forms.Form):
    student_name = forms.CharField(widget=forms.HiddenInput())
    student_email = forms.CharField(required=False, widget=forms.HiddenInput())
    group_name = forms.CharField(required=False, widget=forms.HiddenInput())
    score_band = forms.CharField(required=False, widget=forms.HiddenInput())
    task_focus = forms.CharField(required=False, widget=forms.HiddenInput())
    comment = forms.CharField(
        required=False,
        label="�??����? ���� �����������",
        widget=forms.Textarea(
            attrs={
                "class": "form-control ai-comment-textarea",
                "rows": 4,
                "placeholder": "��������� �����?�� ?������ ��������, ��� �������� ������ �?������ ����?��",
            }
        ),
    )


class TeacherAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="�����",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "�����?��� ����?��"}
        ),
    )
    password = forms.CharField(
        label="??����?�",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "??����?�?��� ����?��"}
        ),
    )


class TeacherRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        label="���",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "�??����? ���"}),
    )
    last_name = forms.CharField(
        label="���",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "�??����? ���"}),
    )
    username = forms.CharField(
        label="�����",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "�?���� ��� �����"}),
    )
    email = forms.EmailField(
        label="����������? �����",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "teacher@example.com"}),
    )
    password1 = forms.CharField(
        label="??����?�",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "������ 8 ��?��"}),
    )
    password2 = forms.CharField(
        label="??����?�� ?�������",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "??����?�� ?���� ����?��"}
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "username", "email", "password1", "password2")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("�?� ����������? ����� �?��� ��������.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.email = self.cleaned_data["email"].strip().lower()
        if commit:
            user.save()
        return user
