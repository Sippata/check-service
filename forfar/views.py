import json

from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt

import django_rq

from .models import Printer, Check
from .serializers import CheckSerializer
from .tasks import generate_pdf


@csrf_exempt
@require_POST
def create_checks(request):
    """
    Cоздаeт в БД чеки для всех принтеров точки, указанной в заказе,
    и ставит асинхронные задачи на генерацию PDF-файлов для этих чеков.
    """
    order = json.loads(request.body.decode())
    order_exist = Check.objects.filter(order__id=order['id']).exists()
    if order_exist is not False:
        return JsonResponse({'error': "Для данного заказа уже созданы чеки"}, status=400)

    printers = Printer.objects.filter(point_id=order['point_id'])
    if not printers.exists():
        return JsonResponse({'error': "Для данной точки не настроено ни одного принтера"}, status=400)

    for printer in printers:
        check = Check.objects.create(printer_id=printer.id, type=printer.check_type, order=order)
        # асинхронная задача на генерацию PDF-файла
        django_rq.enqueue(generate_pdf, check.id)
    return JsonResponse({'ok': "Чеки успешно созданы"})


@require_GET
def get_new_checks(request, api_key):
    """
    Возвращает список новых чеков.
    """
    printer = Printer.objects.filter(api_key=api_key).first()
    if printer is None:
        return JsonResponse({'error': "Ошибка авторизации"}, status=401)

    checks = printer.check_set.filter(status=Check.NEW).order_by('id')
    return JsonResponse({'checks': CheckSerializer(checks, many=True).data})


@require_GET
def get_check_pdf(request, api_key, check_id):
    """
    Возвращает PDF-файл чека.
    """
    is_exist = Printer.objects.filter(api_key=api_key).exists()
    if is_exist is False:
        return JsonResponse({'error': "Ошибка авторизации"}, status=401)

    check = Check.objects.filter(id=check_id).first()
    if check is None:
        return JsonResponse({'error': "Данного чека не существует"}, status=400)
    if not check.pdf_file:
        return JsonResponse({'error': "Для данного чека не сгенерирован PDF-файл"}, status=400)

    check.status = Check.PRINTED
    check.save()
    return FileResponse(open(check.pdf_file.path, 'rb'))
