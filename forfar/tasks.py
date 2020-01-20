import json
import base64
import os

from django.template import loader
from django.conf import settings
from django.core.files.base import ContentFile

import requests

from .models import Check


def send_query_to_wkhtmltopdf(rendered_html):
    url = f'http://{settings.HTMLTOPDF_WORKER["HOST"]}:{settings.HTMLTOPDF_WORKER["PORT"]}/'
    data = {
        'contents': str(base64.b64encode(rendered_html.encode()), encoding='utf-8')
    }
    headers = {
        'Content-Type': 'application/json',
    }
    return requests.post(url, data=json.dumps(data), headers=headers)


def generate_pdf(check_id):
    check = Check.objects.get(id=check_id)

    # Если файл уже существует
    file_name = f"{check.order['id']}_{check.type}.pdf"
    if os.path.isfile(os.path.join(settings.MEDIA_ROOT, 'pdf', file_name)):
        check.pdf_file.name = file_name
        check.status = Check.RENDERED
        check.save()
        return

    rendered_html = loader.render_to_string(f'forfar/{check.type.lower()}_check.html', context=check.order)
    response = send_query_to_wkhtmltopdf(rendered_html)

    file = ContentFile(response.content)
    check.pdf_file.save(file_name, file, save=False)
    check.status = Check.RENDERED
    check.save()
