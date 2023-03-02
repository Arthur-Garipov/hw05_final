from django.core.paginator import Paginator


def pagination(request, *args, **kwargs):
    paginator = Paginator(*args, **kwargs)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
