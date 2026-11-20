from django.contrib.auth.forms import AuthenticationForm

class FormLogin(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(FormLogin, self).__init__(*args,**kwargs)
        self.fields['username'].widget.attrs.update({
            'id': 'username',
            'class': 'form-control',
            'autocomplete': 'username',
            'placeholder': 'Ingrese su usuario',
        })
        self.fields['password'].widget.attrs.update({
            'id': 'password',
            'class': 'form-control',
            'autocomplete': 'current-password',
            'placeholder': 'Ingrese su contraseña',
        })
