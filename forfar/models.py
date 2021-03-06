from django.db import models
from django.contrib.postgres.fields import JSONField


class CommonInfo(models.Model):
    CLIENT = 'client'
    KITCHEN = 'kitchen'
    CHECK_TYPES = [(CLIENT, 'client'), (KITCHEN, 'kitchen')]

    class Meta:
        abstract = True


class Printer(CommonInfo):

    name = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255)
    check_type = models.CharField(max_length=7, choices=CommonInfo.CHECK_TYPES)
    point_id = models.IntegerField()

    def __str__(self):
        return self.name


class Check(CommonInfo):

    NEW = 'new'
    RENDERED = 'rendered'
    PRINTED = 'printed'
    STATUSES = [(NEW, 'new'),
                (RENDERED, 'rendered'),
                (PRINTED, 'printed')]

    printer = models.ForeignKey(Printer, on_delete=models.CASCADE)
    type = models.CharField(max_length=7, choices=CommonInfo.CHECK_TYPES)
    order = JSONField()
    status = models.CharField(max_length=8, choices=STATUSES, default=NEW)
    pdf_file = models.FileField(upload_to='pdf/', null=True, blank=True)

    def __str__(self):
        return f'{self.order["id"]}_{self.type}'
