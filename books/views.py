from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from datetime import datetime
from django.http import FileResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from .models import Book, Author, Type, Location, Language
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib import messages
from django.core.serializers import serialize
from docx2pdf import convert
from django.conf import settings
import logging
import comtypes.client
from docxtpl import DocxTemplate
import os


per_page = 3000


book_logger = logging.getLogger("books")


@login_required
def all_books(request):
    page_obj = paginator_books(request, Book.objects.all().order_by("id"))
    return render(request, "books/all-books.html",
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
    return redirect('books:show_book', book_id=book_id)


@permission_required("artax.change_book", raise_exception=True)
def remove_book_cover(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        if book.cover:
            default_storage.delete(book.cover.path)
            book.cover = None
            book.save()
    return redirect('books:show_book', book_id=book_id)


@permission_required("artax.change_book", raise_exception=True)
def change_book_summary(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    book_summary = request.FILES.get('bookSummary')
    if request.method == 'POST' and book_summary and book.summary == '':
        if book_summary.content_type != "application/pdf":
            messages.warning(request, "File type for image summary invalid.")
            return redirect("books:show_book", book_id=book_id)
        book.summary = book_summary
        book.save()
    return redirect('books:show_book', book_id=book_id)


@permission_required("artax.change_book", raise_exception=True)
def change_book_cover(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    book_cover = request.FILES.get("bookCover")
    if request.method == 'POST' and book_cover and book.cover == "":
        if not book_cover.content_type.startswith("image/"):
            messages.warning(request, "File type for image cover invalid.")
            return redirect("books:show_book", book_id=book_id)
        book.cover = book_cover
        book.save()
    return redirect('books:show_book', book_id=book_id)


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
                return redirect('books:new_book')
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
                    return redirect("books:new_book")
                if book_cover is not None and not book_cover.content_type.startswith("image/"):
                    messages.warning(request, "File type for image cover invalid.")
                    return redirect("books:new_book")

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
                    return redirect("books:new_book")
                except ValidationError as error:
                    messages.warning(request, f"ValidationError: {error}")
                    return redirect("books:new_book")
                except AttributeError as error:
                    messages.warning(request, "Attribute error")
                    messages.warning(request, f"{error}")
            return redirect("books:show_book", book_id=Book.objects.all().last().id)
    return render(request, "books/new-book.html", {"book_id": book_id, "types": types, "locations": locations,
                                                   "authors": authors, "languages": languages,
                                                   "url_arg": f"books%2F{book_id}%2F"})


@login_required
def change_per_page(request):
    global per_page
    per_page = request.POST.get("number")
    return redirect('books:all_books')


@login_required
def book_queries(request):
    context = {
        "types": Type.objects.all(),
        "authors": Author.objects.all().order_by('name'),
        "locations": Location.objects.all(),
        "languages": Language.objects.all(),
    }
    return render(request, "books/queries-books.html", context)


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
            return render(request, "main/record-404.html", {'param': "book"})
        else:
            return redirect("books:show_book", book_id=book.id)
    else:
        filters = {
            "type": ("type__name__icontains", "type"),
            "location": ("location__code__icontains", "location"),
            "title": ("title__icontains", "title"),
            "content": ("subject__icontains", "content"),
            "language": ("language__name__icontains", "language"),
            "author": ("author__name__icontains", "author"),
            "publisher": ("publisher__icontains", "publisher"),
        }
        filter_params = {}
        params = {}
        for field, (lookup, param_name) in filters.items():
            value = request.GET.get(param_name)
            if value != "0" and str(value).strip() != "":
                filter_params[lookup] = value
                params[field] = value
        if filter_params:
            books = books.filter(**filter_params)
        print(params)
    if books.exists() is False:
        context = {'param': "book"}
        return render(request, "main/record-404.html", context)
    else:
        if request.GET.get('submit_button') == 'web':
            page_number = request.GET.get('page')
            paginator = Paginator(books, per_page)
            page_obj = paginator.get_page(page_number)
            return render(request, 'books/query-results.html', {'page_obj': page_obj})
        else:
            origin_path = os.path.join(settings.BASE_DIR, 'books/report-templates/book-query.docx')
            new_path = os.path.join(settings.BASE_DIR, 'books/report-templates/book-query-edit.docx')
            doc = DocxTemplate(origin_path)
            print(f"These are the parameters: {params}")
            serialized_data = []
            for my_dict in books:
                serialized_data.append(my_dict.serialize_report())

            context = {
                'user': request.user.get_full_name(),
                'date': str(datetime.today().date().strftime("%d %B %Y")),
                'nb_of_books': books.count(),
                'table_rows': serialized_data,
            }
            print(books.values())
            context.update(params)
            doc.render(context)
            doc.save(new_path)
            # comtypes.CoInitialize()
            # pdf_path = os.path.join(settings.BASE_DIR, 'book-query-edit.pdf')
            # word = comtypes.client.CreateObject('Word.Application')
            # pdf_format = 17
            # word.Visible = False
            # in_file = word.Documents.Open(new_path)
            # in_file.SaveAs(pdf_path, FileFormat=pdf_format)
            # in_file.Close()
            # word.Quit()
            # comtypes.CoUninitialize()
            response = FileResponse(open(new_path, 'rb'))
            response['Content-Disposition'] = 'attachement; filename="book-report.docx"'
            return response


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
                return redirect("books:show_book", book_id=book_id)
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
    return render(request, "books/record-book.html", {"book": book_record, "types": types, "locations": locations,
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
    return redirect("books:all_books")


def report(request):
    return render(request, "books/report.html", context={'books': Book.objects.all()})


# def generate_report(parameters, data, user, date):
#
