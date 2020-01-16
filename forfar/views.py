import json

from django.http import JsonResponse, FileResponse

from .models import Printer, Check
from .serializers import CheckSerializer


def create_checks(request):
    """
    Cоздаeт в БД чеки для всех принтеров точки указанной в заказе
    и ставит асинхронные задачи на генерацию PDF-файлов для этих чеков.
    """
    order = json.loads(str(request.body, encoding='utf8'))
    exist_order = Check.objects.first(order__id=order['id'])
    if exist_order is not None:
        return JsonResponse({"error": "Для данного заказа уже созданы чеки"}, status=400)

    printers = Printer.objects.filter(point_id=order['point_id'])
    if not printers.exists():
        return JsonResponse({"error": "Для данной точки не настроено ни одного принтера"}, status=400)

    for printer in printers:
        Check.objects.create(printer_id=printer.id, type=printer.check_type, order=order)
        # асинхронная задача на генерацию PDF-файла



def get_new_checks(request, api_key):
    """
    Возвращает список новых чеков.
    """
    printer = Printer.objects.first(api_key=api_key)
    if printer is None:
        return JsonResponse({'error': "Ошибка авторизации"}, status=401)

    checks = printer.check_set.filter(status=Check.NEW)
    return JsonResponse({'checks': CheckSerializer(checks, many=True)})


def create_check(request, api_key, check_id):
    """
    Возвращает PDF-файл чека.
    """
    printer = Printer.objects.first(api_key=api_key)
    if printer is None:
        return JsonResponse({'error': "Ошибка авторизации"}, status=401)

    check = Check.objects.first(id=check_id)
    if check is None:
        return JsonResponse({'error': "Данного чека не существует"}, status=400)
    if check.status != Check.RENDERED and check.pdf_file:
        return JsonResponse({'error': "Для данного чека не сгенерирован PDF-файл"}, 400)

    check.status = Check.PRINTED
    check.save()
    return FileResponse(open(check.pdf_file, 'rb'))
