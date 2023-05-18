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
