from datetime import datetime
from smtplib import SMTPRecipientsRefused
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.models import Group
from django.core.files.storage import default_storage
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from .models import User, Book, Author, Type, Location, Language
from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist, ValidationError, PermissionDenied
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
from django.http import FileResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from io import BytesIO

user_logger = logging.getLogger("users")
book_logger = logging.getLogger("books")


RED = '\033[91m'
RESET = '\033[0m'


per_page = 2000


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
    with open(book_logger.handlers[0].baseFilename, 'r') as logs:
        log_lines = logs.readlines()
    for line in log_lines[::-1]:
        context['logs'].append(
            {'message': line[4:].split(" /$/ ")[0],
             'color': 'text-success' if line[:3] == 'ADD' else ('text-info' if line[:3] == 'EDT' else 'text-danger'),
             'time': datetime.strptime(line.split(" /$/ ")[1].strip('\n'), '%Y-%m-%d %H:%M:%S,%f')}
        ) if line[:3] == 'ADD' or line[:3] == 'EDT' or line[:3] == 'DLT' else None
        if len(context['logs']) >= 7:
            break

    return render(request, "artax/dashboard.html", context)


def generate_pdf_report(request):
    data = [['ID', 'Title', 'Author', 'Section', 'Publisher', 'Publishing Date']]
    book_queryset = Book.objects.all()
    for book in book_queryset:
        data.append([book.id, book.title, book.author, book.section, book.publisher, book.publishing_date])

    # Create a buffer for the PDF to be stored in
    buffer = BytesIO()

    # Create the PDF object, using the buffer as its "file."
    pdf = SimpleDocTemplate(buffer, pagesize=letter)

    # Create a table with the data and specify the style
    table = Table(data)
    style = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)])

    table.setStyle(style)

    # Build the PDF and return it as a response
    pdf.build([table])
    buffer.seek(0)
    response = FileResponse(buffer, as_attachment=True, filename='report.pdf')
    return response


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
    return render(request, "artax/faq.html")


def contact(request):
    return render(request, "artax/contact.html")


# TODO 1 Users Handling ################################################################################################

@csrf_protect
def login_view(request):
    if request.user.is_authenticated:
        return redirect("index")
    elif request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        remember_me = request.POST.get("rememberMe")
        user = authenticate(request, username=username, password=password)

        if username == '' or password == '':
            messages.warning(request, "Please fill in all fields.")
            return redirect('login')
        # username doesn't exist or password incorrect.
        if user is None:
            messages.error(request, "Credentials given incorrect, please try again.")
            return redirect('login')
        else:
            if not remember_me:
                request.session.set_expiry(0)
            user_logger.info(f"User {username} (User ID: {user.id}) logged on {datetime.now()}"
                             f" with user-agent {user_agents.parse(request.META.get('HTTP_USER_AGENT', ''))}")
            login(request, user)
            return redirect('profile')
    return render(request, "artax/login.html")


@staff_required
@login_required(login_url="login")
def new_user(request):
    if request.method == "POST":
        password = request.POST.get("password")
        pass_conf = request.POST.get("pwd_conf")

        if password != pass_conf:
            messages.error(request, "Password don't match. Please try again.")
            return redirect("register")
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
            message = render_to_string('artax/email_confirmation_email.html', {
                'user': user,
                'confirmation_link': confirmation_link,
            })
            send_mail(subject, message, "email.the.artax.network@gmail.com", [user.email], html_message=message)
            user.save()
            role = request.POST.get("role")
            if role == '1':
                user.is_superuser = True
            elif role == '2':
                user.is_staff = True
                user.groups.add(Group.objects.get(name="Office Administrator"))
            elif role == '3':
                user.groups.add(Group.objects.get(name="Lawyer"))
            elif role == '4':
                user.groups.add(Group.objects.get(name="Visitor"))
            user.save()
            return render(request, "artax/email-verify-email.html")
        except IntegrityError:
            messages.error(
                request, "Username or email already in use, please try again with a new one or log in instead!")
        except SMTPRecipientsRefused:
            messages.error(
                request, "Email address given is unreachable. Please try again."
            )
            return redirect('register')
    return render(request, "artax/register.html")


def confirm_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode("utf-8")
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, ObjectDoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'artax/email_confirmed.html')
    else:
        return render(request, 'artax/email_confirmation_invalid.html')


@login_required(login_url="login")
def profile(request):
    if request.method == "POST":
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

    context = {}
    for user_group in request.user.groups.values_list('name', flat=True):
        context['clearance'] = user_group
    if request.user.is_superuser:
        context['clearance'] = 'System Administrator'
    return render(request, "artax/users-profile.html", context=context)


@login_required(login_url="login")
def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("password")
        new_password = request.POST.get("new_password")
        renew_password = request.POST.get("renew_password")
        user = User.objects.filter(username=request.user.username).first()
        if new_password != renew_password:
            messages.error(request, "Password entered don't match. Please try again.")
            return redirect('profile')
        elif current_password == new_password:
            messages.error(request, "Password entered is the same as original. Please choose a new one and try again.")
            return redirect('profile')
        elif authenticate(request, username=user.username, password=current_password) is None:
            messages.error(request, 'Current password incorrect, please try again.')
            return redirect('profile')
        else:
            user.set_password(new_password)
            user.save()
            user_logger.info(
                f"User @{request.user.username} (User ID: {request.user.pk}) changed his password on {datetime.now()}")
            update_session_auth_hash(request, request.user)
            return redirect("profile")
    return redirect("profile")


@login_required(login_url="login")
def logout_view(request):
    user = request.user
    logout(request)
    user_logger.info(f"User {user.username} (User ID: {user.pk}) logged out on {datetime.now()}")
    return redirect("login")


# TODO 2 Book Library ##################################################################################################

@login_required(login_url="login")
def all_books(request):
    page_obj = paginator_books(request, Book.objects.all().order_by("id"))
    return render(request, "artax/all-books.html",
                  {"page_obj": page_obj, 'per_page': per_page, 'per_page_options': [25, 35, 45]})


def paginator_books(request, books):
    page_number = request.GET.get('page')
    if request.GET.get("asc") == 'False':
        books = books[::-1]
    paginator = Paginator(books, per_page)
    page_obj = paginator.get_page(page_number)
    return page_obj


@permission_required("artax.change_book", raise_exception=True)
def remove_book_summary(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        if book.summary:
            default_storage.delete(book.summary.path)
            book.summary = None
            book.save()
    return redirect('show_book', book_id=book_id)


@permission_required("artax.change_book", raise_exception=True)
def remove_book_cover(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        if book.cover:
            default_storage.delete(book.cover.path)
            book.cover = None
            book.save()
    return redirect('show_book', book_id=book_id)


@permission_required("artax.change_book", raise_exception=True)
def change_book_summary(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    book_summary = request.FILES.get('bookSummary')
    if request.method == 'POST' and book_summary and book.summary == '':
        if book_summary.content_type != "application/pdf":
            messages.warning(request, "File type for image summary invalid.")
            return redirect("show_book", book_id=book_id)
        book.summary = book_summary
        book.save()
    return redirect('show_book', book_id=book_id)


@permission_required("artax.change_book", raise_exception=True)
def change_book_cover(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    book_cover = request.FILES.get("bookCover")
    if request.method == 'POST' and book_cover and book.cover == "":
        if not book_cover.content_type.startswith("image/"):
            messages.warning(request, "File type for image cover invalid.")
            return redirect("show_book", book_id=book_id)
        book.cover = book_cover
        book.save()
    return redirect('show_book', book_id=book_id)


@login_required
def new_book(request):
    book_record = Book.objects.all().last()
    if book_record is None:
        book_id = 1
    else:
        book_id = book_record.id + 1
    types, authors, locations, languages = Type.objects.all(), Author.objects.all().order_by('name'), Location.objects.all().order_by(
        "code"), Language.objects.all()
    if request.method == "POST":
        if not request.user.has_perm("artax.add_book"):
            raise PermissionDenied
        else:
            if Book.objects.filter(title=request.POST.get("bookTitle")).first():
                messages.warning(request, "A book already exists with that title. Choose another one and try again.")
                return redirect('new_book')
            else:
                book_type = Type.objects.get(pk=request.POST.get("bookType"))
                special_id = f"{book_type.code}{Book.objects.filter(type=book_type).count() + 1}"

                purchase_date = request.POST.get("purchaseDate")
                if purchase_date == '':
                    purchase_date = None

                book_summary = request.FILES.get("bookSummary")
                book_cover = request.FILES.get("bookCover")

                if book_summary is not None and book_summary.content_type != "application/pdf":
                    messages.warning(request, "File type for summary invalid.")
                    return redirect("new_book")
                if book_cover is not None and not book_cover.content_type.startswith("image/"):
                    messages.warning(request, "File type for image cover invalid.")
                    return redirect("new_book")

                new_book_record = Book(
                    lib_id=special_id,
                    author=Author.objects.get(pk=request.POST.get("authorName")),
                    title=request.POST.get("bookTitle"),
                    subject=request.POST.get("subject", None),
                    type=book_type,
                    section=request.POST.get("bookSection", None),
                    location=Location.objects.get(pk=request.POST.get("bookLocation")),
                    language=Language.objects.get(pk=request.POST.get("bookLanguage")),
                    summary=book_summary,
                    cover=book_cover,
                    publisher=request.POST.get("publisher"),
                    publishing_date=request.POST.get("publishingYear"),
                    purchase_date=purchase_date,
                    isbn=request.POST.get("isbn", None),
                    number_of_copies=request.POST.get("numberOfCopies"),
                    registrator=request.user,
                    last_editor=request.user,
                    last_edit_time=datetime.now(),
                )
                try:
                    new_book_record.save()
                    book_logger.info(f"ADD: @{request.user.username} created a new record: Book (ID={special_id}), "
                                     f'title "{request.POST.get("bookTitle")}"')
                    new_book_record.purchase_date = None
                    book_logger.info(f"Record created: {serialize('json', [new_book_record])}")

                except ValueError as error:
                    messages.warning(request, f"ValueError: {error}")
                    return redirect("new_book")
                except ValidationError as error:
                    messages.warning(request, f"ValidationError: {error}")
                    return redirect("new_book")
                except AttributeError as error:
                    messages.warning(request, "Attribute error")
                    messages.warning(request, f"{error}")
            return redirect("show_book", book_id=Book.objects.all().last().id)
    return render(request, "artax/new-book.html", {"book_id": book_id, "types": types, "locations": locations,
                                                   "authors": authors, "languages": languages,
                                                   "url_arg": f"books%2F{book_id}%2F"})


@login_required
def change_per_page(request):
    global per_page
    per_page = request.POST.get("number")
    return redirect('all_books')


@login_required
def book_queries(request):
    context = {
        "types": Type.objects.all(),
        "authors": Author.objects.all().order_by('name'),
        "locations": Location.objects.all(),
        "languages": Language.objects.all(),
    }
    return render(request, "artax/queries-books.html", context)


@login_required
def query_books_by(request):
    book_query_param = request.GET.get("book_query_param")
    book_param = request.GET.get("name")
    books = Book.objects.all().order_by("id")
    if book_query_param == "id" or book_query_param == "special_id":
        book = get_object_or_404(Book,
                                 lib_id=f"{book_param}{request.GET.get('name_id')}") if book_query_param == "special_id" else get_object_or_404(
            Book, pk=book_param)
        if book is None or book == []:
            return render(request, "artax/record-404.html", {'param': "book"})
        else:
            return redirect("show_book", book_id=book.id)
    else:
        filters = {
            "type": ("type__name__icontains", "type"),
            "location": ("location__code__icontains", "location"),
            "title": ("title__icontains", "title"),
            "content": ("subject__icontains", "content"),
            "language": ("language__code__icontains", "language"),
            "author": ("author__name__icontains", "author"),
            "publisher": ("publisher__icontains", "publisher"),
        }
        filter_params = {}
        for field, (lookup, param_name) in filters.items():
            value = request.GET.get(param_name)
            if value != "0" and str(value).strip() != "":
                filter_params[lookup] = value

        if filter_params:
            books = books.filter(**filter_params)

    if books.exists() is False:
        context = {'param': "book"}
        return render(request, "artax/record-404.html", context)
    else:
        page_number = request.GET.get('page')
        paginator = Paginator(books, per_page)
        page_obj = paginator.get_page(page_number)
        return render(request, 'artax/query-results.html', {'page_obj': page_obj})


@login_required(login_url="login")
def show_book(request, book_id):
    book_record = get_object_or_404(Book, pk=book_id)
    book_title = request.POST.get("title")
    types, authors, locations, languages = Type.objects.all(), Author.objects.all().order_by('name'), Location.objects.all(), Language.objects.all()
    if request.method == "POST":
        if not request.user.has_perm("artax.change_book"):
            raise PermissionDenied
        target_book = Book.objects.filter(title=str(request.POST.get("title")).strip(" "))
        if target_book.exists():
            if target_book.first().pk != book_id:
                messages.warning(request,
                                 "Book with that title already exists. Please try again with another one or change "
                                 "book section field.")
                return redirect(show_book, book_id=book_id)
        book_author = Author.objects.get(pk=request.POST.get("author"))
        book_location = Location.objects.get(pk=request.POST.get("location"))
        book_language = Language.objects.get(pk=request.POST.get("language"))
        flag = False
        if book_author != book_record.author or book_language != book_record.language or book_location != book_record.author:
            flag = True
        book_record.author = book_author
        book_record.location = book_location
        book_record.language = book_language
        book_record.title = book_title
        book_record.subject = request.POST.get("subject")
        book_record.section = request.POST.get("section")
        book_record.publisher = request.POST.get("publisher")
        book_record.publishing_date = request.POST.get("publishing_date")
        book_record.isbn = request.POST.get("isbn")
        book_record.number_of_copies = request.POST.get("numberOfCopies")
        if book_record.is_dirty() or flag:
            book_record.last_edit_time = datetime.now()
            book_record.last_editor = request.user
            book_record.save()
            book_logger.info(f"EDT: @{request.user.username} altered record: Book (ID={book_record.lib_id}), "
                             f'title "{book_record.title}"')
            book_logger.info(f"New version: {serialize('json', [book_record])}")
    return render(request, "artax/record-book.html", {"book": book_record, "types": types, "locations": locations,
                                                      "authors": authors, "languages": languages,
                                                      "url_arg": f"books%2F{book_id}%2F"
                                                      })


@permission_required("artax.delete_book", raise_exception=True)
@login_required(login_url="login")
def delete_book(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    book.delete()
    book_logger.info(f"DLT: @{request.user.username} deleted record: Book (ID={book.lib_id}), "
                     f'title "{book.title}".')
    return redirect("all_books")
