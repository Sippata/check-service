import json
import hashlib

from django.test import TestCase
from django.urls import reverse
from django.core.files.base import File, ContentFile

from model_mommy import mommy
from mock import patch
import django_rq

from ..models import Check, Printer


class GetNewChecksTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.printer_1: Printer = mommy.make(Printer, check_type=Printer.CLIENT, point_id=1)
        cls.printer_2: Printer = mommy.make(Printer, check_type=Printer.KITCHEN, point_id=2)

    def setUp(self) -> None:
        self.check_1 = mommy.make(Check, type=Check.CLIENT, printer=self.printer_1)
        self.check_2 = mommy.make(Check, type=Check.KITCHEN, printer=self.printer_2)
        self.check_3 = mommy.make(Check, type=Check.KITCHEN, printer=self.printer_2)
        self.check_rendered = mommy.make(Check, type=Check.KITCHEN, printer=self.printer_2, status=Check.RENDERED)
        self.check_printed = mommy.make(Check, type=Check.KITCHEN, printer=self.printer_2, status=Check.PRINTED)

    def test_error_handling(self):
        res = self.client.get(reverse('forfar:new_checks', kwargs={'api_key': 'nonexistent_api'}))
        self.assertEqual(res.status_code, 401)
        self.assertJSONEqual(res.content.decode('utf-8'), {'error': "Ошибка авторизации"})

    def test_success_get(self):
        res = self.client.get(reverse('forfar:new_checks', kwargs={'api_key': self.printer_1.api_key}))
        expected_res = {'checks': [{'id': self.check_1.id}]}
        self.assertEqual(res.status_code, 200)
        self.assertJSONEqual(res.content.decode('utf-8'), expected_res)

    def test_check_ordering(self):
        res = self.client.get(reverse('forfar:new_checks', kwargs={'api_key': self.printer_2.api_key}))
        expected_res = {'checks': [{'id': self.check_2.id}, {'id': self.check_3.id}]}
        self.assertEqual(res.status_code, 200)
        self.assertJSONEqual(res.content.decode('utf-8'), expected_res)

    def test_only_new_checks(self):
        res = self.client.get(reverse('forfar:new_checks', kwargs={'api_key': self.printer_2.api_key}))
        self.assertEqual(res.status_code, 200)
        self.assertNotIn({'id': self.check_printed.id}, json.loads(res.content, encoding='utf8')['checks'])
        self.assertNotIn({'id': self.check_rendered.id}, json.loads(res.content, encoding='utf8')['checks'])


def calc_hash_sum(obj):
    hash_md5 = hashlib.md5()
    obj.open('rb')
    for chunk in obj.chunks():
        hash_md5.update(chunk)
    obj.close()
    return hash_md5.digest()


class GetCheckPdfTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.printer: Printer = mommy.make(Printer, check_type=Printer.KITCHEN, point_id=2)

        cls.check: Check = mommy.make(Check, printer=cls.printer)

        cls.test_file: File = File(open('forfar/tests/test_check.pdf', 'rb'))
        cls.test_file.name = 'test_check.pdf'
        cls.check_with_file: Check = mommy.make(
            Check, printer=cls.printer, pdf_file=cls.test_file, status=Check.RENDERED, _create_files=True)

    def test_success_result(self):
        data = {'api_key': self.printer.api_key, 'check_id': self.check_with_file.id}
        res = self.client.get(reverse('forfar:check', kwargs=data))

        self.assertEqual(res.status_code, 200)
        res_file = ContentFile(b''.join(res.streaming_content))
        self.assertEqual(calc_hash_sum(res_file), calc_hash_sum(self.test_file))

    def test_invalid_api_key(self):
        data = {'api_key': 'invalid_api_key', 'check_id': self.check_with_file.id}
        res = self.client.get(reverse('forfar:check', kwargs=data))
        self.assertEqual(res.status_code, 401)
        self.assertJSONEqual(res.content.decode('utf-8'), {'error': "Ошибка авторизации"})

    def test_non_existing_check(self):
        data = {'api_key': self.printer.api_key, 'check_id': 210434}
        res = self.client.get(reverse('forfar:check', kwargs=data))
        self.assertEqual(res.status_code, 400)
        self.assertJSONEqual(res.content.decode('utf-8'), {'error': "Данного чека не существует"})

    def test_unprinted_check(self):
        data = {'api_key': self.printer.api_key, 'check_id': self.check.id}
        res = self.client.get(reverse('forfar:check', kwargs=data))
        self.assertEqual(res.status_code, 400)
        self.assertJSONEqual(res.content.decode('utf-8'), {'error': "Для данного чека не сгенерирован PDF-файл"})

    @classmethod
    def tearDownClass(cls):
        cls.test_file.close()
        cls.check_with_file.pdf_file.delete()
        super(GetCheckPdfTest, cls).tearDownClass()


class CreateChecksTest(TestCase):

    def setUp(self):
        with open('forfar/tests/test_order.json') as f:
            self.order = json.load(f)
        self.printer = mommy.make(Printer, point_id=1)
        self.check = mommy.make(Check, printer=self.printer, type=Check.CLIENT, order=self.order)

    def test_order_existing(self):
        res = self.client.post(reverse('forfar:create_checks'), json.dumps(self.order), content_type='application/json')
        self.assertEqual(res.status_code, 400)
        self.assertJSONEqual(res.content.decode('utf-8'), {"error": "Для данного заказа уже созданы чеки"})

    def test_not_existing_point(self):
        self.order['id'] = 777
        self.order['point_id'] = 777
        res = self.client.post(reverse('forfar:create_checks'), json.dumps(self.order), content_type='application/json')
        self.assertEqual(res.status_code, 400)
        self.assertJSONEqual(res.content.decode('utf-8'), {"error": "Для данной точки не настроено ни одного принтера"})

    @patch('django_rq.enqueue')
    def test_success_result(self, _):
        self.order['id'] = 151413
        res = self.client.post(reverse('forfar:create_checks'), json.dumps(self.order), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertJSONEqual(res.content.decode('utf-8'), {'ok': "Чеки успешно созданы"})
