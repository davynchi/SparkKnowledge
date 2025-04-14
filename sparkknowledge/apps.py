"""
Файл с кратким заданием названия проекта для Django
"""


from django.apps import AppConfig


class SparkKnowledgeConfig(AppConfig):
    """
    Класс конфигурации приложения SparkKnowledge.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "sparkknowledge"
