from django.db import models


class Contact(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128, verbose_name='Name')
    message = models.TextField(verbose_name='Message')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} - {}'.format(self.name, self.message[:16])

    class Meta:
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'


# class Plots(models.Model):
#     id = models.AutoField(primary_key=True)
#     channel = models.IntegerField(max_length=24, verbose_name='Channel ID')
#     guild = models.IntegerField(max_length=24, verbose_name='Guild ID')
#     title = models.CharField(max_length=128, verbose_name='Title')
#     names = models.JSONField(verbose_name='Names List')
#     values = models.JSONField(verbose_name='Values List')
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created')
#
#     def __str__(self):
#         return '{} - {}'.format(self.id, self.title[:18])
#
#     class Meta:
#         verbose_name = 'Plot'
#         verbose_name_plural = 'Plots'
