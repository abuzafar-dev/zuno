from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.forms import CharField, Form, ModelForm, PasswordInput

from apps.models import Order, Withdrawal
from apps.utils import normalize_phone

MAX_ORDER_QUANTITY = 99
PHONE_ERROR = "Telefon raqamni +998 XX XXX XX XX ko'rinishida kiriting."


def _clean_phone(value):
    phone = normalize_phone(value)
    if not phone:
        raise ValidationError(PHONE_ERROR)
    return phone


class LoginForm(Form):
    phone_number = CharField(max_length=20, label="Telefon")
    password = CharField(widget=PasswordInput, label="Parol")


class RegisterForm(Form):
    phone_number = CharField(max_length=20, label="Telefon")
    password = CharField(widget=PasswordInput, label="Parol")
    conf_password = CharField(widget=PasswordInput, label="Parolni takrorlash")

    def clean_phone_number(self):
        return _clean_phone(self.cleaned_data['phone_number'])

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password)  # settings.AUTH_PASSWORD_VALIDATORS
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        conf_password = cleaned_data.get('conf_password')
        if password and conf_password and password != conf_password:
            raise ValidationError("Parollar mos tushmadi!")
        return cleaned_data


class ProfileForm(Form):
    first_name = CharField(max_length=50, required=False)
    last_name = CharField(max_length=50, required=False)
    telegram_id = CharField(max_length=100, required=False)
    description = CharField(max_length=2000, required=False)


class TrackOrderForm(Form):
    order_id = CharField(max_length=12)
    phone_number = CharField(max_length=20)


class OrderForm(ModelForm):
    class Meta:
        model = Order
        fields = ['full_name', 'phone_number', 'quantity']
        error_messages = {
            'full_name': {'required': "Ismingizni kiriting."},
            'phone_number': {'required': "Telefon raqamingizni kiriting."},
            'quantity': {'required': "Sonini tanlang.", 'invalid': "Sonini to'g'ri tanlang."},
        }

    def clean_phone_number(self):
        return _clean_phone(self.cleaned_data['phone_number'])

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity < 1:
            raise ValidationError("Soni kamida 1 bo'lishi kerak.")
        if quantity > MAX_ORDER_QUANTITY:
            raise ValidationError(f"Bir buyurtmada ko'pi bilan {MAX_ORDER_QUANTITY} dona.")
        return quantity


class WithdrawalForm(ModelForm):
    class Meta:
        model = Withdrawal
        fields = ['card_number', 'amount']

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_card_number(self):
        card_number = self.cleaned_data['card_number'].replace(' ', '').replace('-', '')
        if not card_number.isdigit() or len(card_number) != 16:
            raise ValidationError("Karta raqami 16 ta raqamdan iborat bo'lishi kerak.")
        return card_number

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise ValidationError("Summani to'g'ri kiriting.")
        if self.user and amount > self.user.main_balance:
            raise ValidationError("Hisobingizdagi mavjud summadan ko'p miqdor kiritdingiz.")
        return amount
