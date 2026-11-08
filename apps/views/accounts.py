from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from apps.forms import LoginForm, ProfileForm, RegisterForm
from apps.models import District, Region, User
from apps.utils import client_ip, is_rate_limited, normalize_phone, parse_positive_int

LOGIN_WINDOW = 15 * 60
LOGIN_ATTEMPTS_PER_PHONE = 8
LOGIN_ATTEMPTS_PER_IP = 40
REGISTRATIONS_PER_IP = 10


def _post_login_redirect(request, user):
    target = request.POST.get('next', '')
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect('new-orders' if user.is_operator else 'dashboard')


class LoginView(View):
    def post(self, request):
        form = LoginForm(request.POST)
        if not form.is_valid():
            return self._fail(request)

        phone = normalize_phone(form.cleaned_data['phone_number'])
        ip = client_ip(request)
        if (is_rate_limited('login-ip', ip, limit=LOGIN_ATTEMPTS_PER_IP, window=LOGIN_WINDOW)
                or is_rate_limited('login', f'{ip}:{phone}', limit=LOGIN_ATTEMPTS_PER_PHONE, window=LOGIN_WINDOW)):
            return self._fail(request, "Urinishlar juda ko'p. 15 daqiqadan keyin qayta urinib ko'ring.")

        user = authenticate(request, phone_number=phone, password=form.cleaned_data['password'])
        if user is None:
            return self._fail(request)
        login(request, user)
        return _post_login_redirect(request, user)

    def get(self, request):
        return redirect('home')

    @staticmethod
    def _fail(request, text="Telefon raqam yoki parol xato."):
        messages.error(request, text, extra_tags='login_modal')
        return redirect('home')


class RegisterView(View):
    def post(self, request):
        if is_rate_limited('register', client_ip(request), limit=REGISTRATIONS_PER_IP, window=60 * 60):
            messages.error(request, "Urinishlar juda ko'p. Birozdan keyin qayta urinib ko'ring.",
                           extra_tags='register_modal field-phone_number')
            return redirect('home')

        form = RegisterForm(request.POST)
        if not form.is_valid():
            # __all__ (parollar mos kelmasligi) takrorlash maydoni ostida chiqadi
            for field, field_errors in form.errors.items():
                target = 'conf_password' if field == '__all__' else field
                for error in field_errors:
                    messages.error(request, error, extra_tags=f'register_modal field-{target}')
            return redirect('home')

        ref_id = parse_positive_int(request.POST.get('ref_id') or request.session.get('ref_id'))
        try:
            user = User.objects.create_user(
                phone_number=form.cleaned_data['phone_number'],
                password=form.cleaned_data['password'],
                referred_by=User.objects.filter(id=ref_id).first() if ref_id else None,
            )
        except IntegrityError:
            messages.error(request, "Bu telefon raqam allaqachon ro'yxatdan o'tgan!",
                           extra_tags='register_modal field-phone_number')
            return redirect('home')
        login(request, user)
        return redirect('profile-settings')

    def get(self, request):
        # Referal havola (/register/?id=N): id sessiyada saqlanadi va ro'yxatdan o'tishda olinadi
        ref_id = parse_positive_int(request.GET.get('id'))
        if ref_id:
            request.session['ref_id'] = ref_id
        return redirect('home')


class LogoutView(View):
    # Faqat POST: boshqa sayt <img src="/logout/"> bilan foydalanuvchini chiqarib yubora olmaydi
    def post(self, request):
        logout(request)
        return redirect('home')


@method_decorator(login_required, name='dispatch')
class ProfileSettingsView(View):
    def get(self, request):
        user = request.user
        districts = District.objects.filter(region=user.region) if user.region_id else District.objects.none()
        return render(request, 'settings.html', {
            'regions': Region.objects.order_by('title'),
            'districts': districts.order_by('title'),
        })

    def post(self, request):
        if request.POST.get('_password_change'):
            return self._change_password(request)

        form = ProfileForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Ma'lumotlar juda uzun yoki noto'g'ri.")
            return redirect('profile-settings')

        user = request.user
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        user.telegram_id = form.cleaned_data['telegram_id']
        user.bio = form.cleaned_data['description']

        region_id = parse_positive_int(request.POST.get('region'))
        region = Region.objects.filter(id=region_id).first() if region_id else None
        user.region = region
        district_name = request.POST.get('city', '')
        user.district = (District.objects.filter(title=district_name, region=region).first()
                         if region and district_name else None)
        user.save()
        messages.success(request, "Profil ma'lumotlari saqlandi.")
        return redirect('profile-settings')

    @staticmethod
    def _change_password(request):
        user = request.user
        current_password = request.POST.get('current_password') or ''
        new_password = request.POST.get('new_password') or ''
        confirm_password = request.POST.get('confirm_password')

        password_errors = []
        if new_password:
            try:
                validate_password(new_password, user)
            except ValidationError as exc:
                password_errors = exc.messages

        # Joriy parol so'raladi: o'g'irlangan sessiya bilan akkauntni egallab bo'lmasin
        if not user.check_password(current_password):
            messages.error(request, "Joriy parol noto'g'ri.", extra_tags='password_form field-current_password')
        elif not new_password:
            messages.error(request, "Yangi parolni kiriting.", extra_tags='password_form field-new_password')
        elif password_errors:
            for error in password_errors:
                messages.error(request, error, extra_tags='password_form field-new_password')
        elif new_password != confirm_password:
            messages.error(request, "Parollar mos tushmadi.", extra_tags='password_form field-confirm_password')
        else:
            user.set_password(new_password)
            user.save()
            messages.success(request, "Parol muvaffaqiyatli o'zgartirildi. Qayta kiring.")
            return redirect('home')
        return redirect('profile-settings')


def get_districts(request, region_id):
    districts = District.objects.filter(region_id=region_id).order_by('title').values_list('title', flat=True)
    return JsonResponse({'districts': [{'name': title} for title in districts]})
