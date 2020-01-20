import json
import os
import shutil, tempfile
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.template import loader

from model_mommy import mommy

import forfar.tasks
from ..tasks import send_query_to_wkhtmltopdf, generate_pdf
from ..models import Check


class PdfGenerationTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super(PdfGenerationTest, cls).setUpClass()
        cls.test_dir = tempfile.mkdtemp()

    def setUp(self):
        with open('forfar/tests/test_order.json', 'r') as f:
            order = json.loads(f.read())
        self.check_invalid = mommy.make(Check)
        self.check_valid: Check = mommy.make(Check, order=order)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir)
        super(PdfGenerationTest, cls).tearDownClass()

    def test_send_query(self):
        order = self.check_valid.order
        order['total'] = 777
        rendered_html = loader.render_to_string('forfar/client_check.html', context=order)
        res = send_query_to_wkhtmltopdf(rendered_html)
        self.assertEqual(res.content[0:4], b'%PDF')

    def test_generate_pdf(self):
        with self.settings(MEDIA_ROOT=self.test_dir):
            generate_pdf(check_id=self.check_valid.id)
            check = Check.objects.get(id=self.check_valid.id)
            self.assertEqual(check.status, Check.RENDERED)
            expected_file_name = f'{check.order["id"]}_{self.check_valid.type}.pdf'
            file_path = os.path.join(self.test_dir, 'pdf', expected_file_name)
            self.assertTrue(os.path.isfile(file_path))

    @patch('os.path')
    def test_generate_exist_file(self, path):
        path.isfile.return_value = True
        with self.settings(MEDIA_ROOT=self.test_dir):
            generate_pdf(check_id=self.check_valid.id)
            check = Check.objects.get(id=self.check_valid.id)
            self.assertEqual(check.status, Check.RENDERED)
            expected_file_name = f'{check.order["id"]}_{self.check_valid.type}.pdf'
            file_path = os.path.join(self.test_dir, 'pdf', expected_file_name)
            self.assertTrue(os.path.isfile(file_path))