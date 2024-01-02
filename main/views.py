from datetime import datetime
from smtplib import SMTPRecipientsRefused
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import User
from books.models import Book
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
import qrcode
import qrcode.image.svg
import logging
import user_agents
from django.core.serializers import serialize
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import *
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string

user_logger = logging.getLogger("users")
book_logger = logging.getLogger("books")


RED = '\033[91m'
RESET = '\033[0m'



def staff_required(function):
    def wrapper(request, *args, **kwargs):
        if request.user.is_active and request.user.is_staff:
            return function(request, *args, **kwargs)
        else:
            return render(request, "403.html", status=403)

    return wrapper


def index(request):
    books = Book.objects.all().order_by('id')[::-1]
    last_books = books[:5]
    context = {'latest_books': last_books, 'logs': []}
    # with open(book_logger.handlers[0].baseFilename, 'r') as logs:
    #     log_lines = logs.readlines()
    # for line in log_lines[::-1]:
    #     context['logs'].append(
    #         {'message': line[4:].split(" /$/ ")[0],
    #          'color': 'text-success' if line[:3] == 'ADD' else ('text-info' if line[:3] == 'EDT' else 'text-danger'),
    #          'time': datetime.strptime(line.split(" /$/ ")[1].strip('\n'), '%Y-%m-%d %H:%M:%S,%f')}
    #     ) if line[:3] == 'ADD' or line[:3] == 'EDT' or line[:3] == 'DLT' else None
    #     if len(context['logs']) >= 7:
    #         break

    return render(request, "main/dashboard.html", context)


def generate_qr_code(request, string_to_encode):
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=4,
    )
    qr.add_data(f"{request.scheme}://{request.get_host()}/{string_to_encode}")
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    response = HttpResponse(content_type="image/png")
    img.save(response, "PNG")
    return response


def download_qr_code(request, string_to_encode):
    qr_code_response = generate_qr_code(request, string_to_encode)
    qr_code_data = qr_code_response.content
    response = HttpResponse(content_type="image/png")
    response["Content-Disposition"] = f"attachment; filename=qr_code.png"
    response.write(qr_code_data)
    return response


def faq(request):
    return render(request, "main/faq.html")


def contact(request):
    return render(request, "main/contact.html")


@csrf_protect
def login_view(request):
    if request.user.is_authenticated:
        return redirect("main:index")
    elif request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        remember_me = request.POST.get("rememberMe")
        user = authenticate(request, username=username, password=password)

        if username == '' or password == '':
            messages.warning(request, "Please fill in all fields.")
            return redirect('main:login')
        # username doesn't exist or password incorrect.
        if user is None:
            messages.error(request, "Credentials given incorrect, please try again.")
            return redirect('main:login')
        else:
            if not remember_me:
                request.session.set_expiry(0)
            user_logger.info(f"User {username} (User ID: {user.id}) logged on {datetime.now()}"
                             f" with user-agent {user_agents.parse(request.META.get('HTTP_USER_AGENT', ''))}")
            login(request, user)
            return redirect('main:profile', username=user.username)
    return render(request, "main/login.html")


@staff_required
@login_required(login_url='login')
def all_users(request):
    users = User.objects.all()
    return render(request, 'main/all-users.html', {'users': users})


@staff_required
@login_required(login_url="login")
def new_user(request):
    if request.method == "POST":
        password = request.POST.get("password")
        pass_conf = request.POST.get("pwd_conf")

        if password != pass_conf:
            messages.error(request, "Password don't match. Please try again.")
            return redirect("main:register")
        try:
            user = User.objects.create_user(
                username=request.POST.get("username"),
                email=request.POST.get("email"),
                password=password,
                first_name=request.POST.get("first_name"),
                last_name=request.POST.get("last_name"),
                is_active=False,
            )
            token = default_token_generator.make_token(user)
            user_pk = user.pk
            uid = urlsafe_base64_encode(str(user_pk).encode("utf-8"))

            current_site = get_current_site(request)
            confirmation_link = f'{current_site.domain}/confirm/{uid}/{token}/'

            subject = 'Confirm your email'
            message = render_to_string('main/email_confirmation_email.html', {
                'user': user,
                'confirmation_link': confirmation_link,
            })
            send_mail(subject, message, "email.the.artax.network@gmail.com", [user.email], html_message=message)
            user.save()
            role = request.POST.get("role")
            if role == '1':
                user.is_superuser = True
                user.groups.add(Group.objects.get(name="System Administrator"))
            elif role == '2':
                user.is_staff = True
                user.groups.add(Group.objects.get(name="Office Administrator"))
            elif role == '3':
                user.groups.add(Group.objects.get(name="Lawyer"))
            elif role == '4':
                user.groups.add(Group.objects.get(name="Visitor"))
            user.save()
            return render(request, "main/email-verify-email.html")
        except IntegrityError:
            messages.error(
                request, "Username or email already in use, please try again with a new one or log in instead!")
        except SMTPRecipientsRefused:
            messages.error(
                request, "Email address given is unreachable. Please try again."
            )
            return redirect('main:register')
    return render(request, "main/register.html")


def confirm_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode("utf-8")
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, ObjectDoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'main/email_confirmed.html')
    else:
        return render(request, 'main/email_confirmation_invalid.html')


@login_required(login_url="login")
def profile(request, username):
    user = get_object_or_404(User, username=username)
    if request.method == "POST" and request.user == user:
        current_user = request.user
        current_user.first_name = request.POST.get("firstName")
        current_user.last_name = request.POST.get("lastName")
        current_user.job = request.POST.get("job")
        current_user.address = request.POST.get("address")
        current_user.phone = request.POST.get("phone")
        current_user.email = request.POST.get("email")
        current_user.about = request.POST.get("about")
        current_user.save()
        user_logger.info(
            f"User @{request.user.username} (User ID: {request.user.pk}) edited his profile on {datetime.now()}.")
        user_logger.info(f"Old User: {serialize('json', [request.user])}")
        user_logger.info(f"New User: {serialize('json', [current_user])}")

    context = {'target_user': user}
    for user_group in user.groups.values_list('name', flat=True):
        context['clearance'] = user_group
    return render(request, "main/users-profile.html", context=context)


@login_required(login_url="login")
def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("password")
        new_password = request.POST.get("new_password")
        renew_password = request.POST.get("renew_password")
        user = User.objects.filter(username=request.user.username).first()
        if new_password != renew_password:
            messages.error(request, "Password entered don't match. Please try again.")
            return redirect('main:profile', username=user.username)
        elif current_password == new_password:
            messages.error(request, "Password entered is the same as original. Please choose a new one and try again.")
            return redirect('main:profile', username=user.username)
        elif authenticate(request, username=user.username, password=current_password) is None:
            messages.error(request, 'Current password incorrect, please try again.')
            return redirect('main:profile', username=user.username)
        else:
            user.set_password(new_password)
            user.save()
            user_logger.info(
                f"User @{request.user.username} (User ID: {request.user.pk}) changed his password on {datetime.now()}")
            update_session_auth_hash(request, request.user)
            return redirect("main:profile")
    return redirect("main:profile")


@login_required(login_url="login")
def logout_view(request):
    user = request.user
    logout(request)
    user_logger.info(f"User {user.username} (User ID: {user.pk}) logged out on {datetime.now()}")
    return redirect("main:login")
