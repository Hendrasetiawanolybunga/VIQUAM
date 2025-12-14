from django import forms
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.hashers import make_password
from .models import Pelanggan, Pemesanan, Sopir

class SopirEditPengirimanForm(forms.ModelForm):
    class Meta:
        model = Pemesanan
        fields = ['status', 'fotoPengiriman']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control bg-white text-dark border-dark'}),
            'fotoPengiriman': forms.FileInput(attrs={'class': 'form-control-file bg-white text-dark border-dark'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit status choices to only 'Selesai' and 'Dibatalkan'
        self.fields['status'].choices = [
            ('Selesai', 'Selesai'),
            ('Dibatalkan', 'Dibatalkan')
        ]

class PelangganRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control bg-white text-dark border-dark',
        'placeholder': 'Masukkan password'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control bg-white text-dark border-dark',
        'placeholder': 'Konfirmasi password'
    }))
    
    class Meta:
        model = Pelanggan
        fields = ['nama', 'noWa', 'alamat', 'username', 'password']
        widgets = {
            'nama': forms.TextInput(attrs={'class': 'form-control bg-white text-dark border-dark', 'placeholder': 'Nama lengkap'}),
            'noWa': forms.TextInput(attrs={'class': 'form-control bg-white text-dark border-dark', 'placeholder': 'Nomor WhatsApp'}),
            'alamat': forms.Textarea(attrs={'class': 'form-control bg-white text-dark border-dark', 'placeholder': 'Alamat lengkap', 'rows': 3}),
            'username': forms.TextInput(attrs={'class': 'form-control bg-white text-dark border-dark', 'placeholder': 'Username'}),
        }
    
    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Password tidak cocok!")
        return confirm_password
    
    def save(self, commit=True):
        pelanggan = super().save(commit=False)
        # Biarkan raw password ada di pelanggan.password
        # Model akan menghashnya saat pelanggan.save() dipanggil
        if commit:
            pelanggan.save()
        return pelanggan

class PelangganLoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control bg-white text-dark border-dark',
        'placeholder': 'Username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control bg-white text-dark border-dark',
        'placeholder': 'Password'
    }))

class PemesananCheckoutForm(forms.ModelForm):
    class Meta:
        model = Pemesanan
        fields = ['alamatPengiriman', 'buktiBayar']
        widgets = {
            'alamatPengiriman': forms.Textarea(attrs={
                'class': 'form-control bg-white text-dark border-dark', 
                'placeholder': 'Alamat lengkap untuk pengiriman',
                'rows': 3
            }),
            'buktiBayar': forms.FileInput(attrs={
                'class': 'form-control-file bg-white text-dark border-dark',
                'required': True
            }),
        }

class PelangganUpdateForm(forms.ModelForm):
    class Meta:
        model = Pelanggan
        fields = ['nama', 'noWa', 'alamat']
        widgets = {
            'nama': forms.TextInput(attrs={'class': 'form-control bg-white text-dark border-dark'}),
            'noWa': forms.TextInput(attrs={'class': 'form-control bg-white text-dark border-dark'}),
            'alamat': forms.Textarea(attrs={'class': 'form-control bg-white text-dark border-dark', 'rows': 3}),
        }

class ChangePasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="Password baru",
        widget=forms.PasswordInput(attrs={'class': 'form-control bg-white text-dark border-dark'}),
        strip=False,
    )
    new_password2 = forms.CharField(
        label="Konfirmasi password baru",
        widget=forms.PasswordInput(attrs={'class': 'form-control bg-white text-dark border-dark'}),
        strip=False,
    )