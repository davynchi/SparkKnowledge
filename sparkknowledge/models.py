from django.db import models


class QuizAttempt(models.Model):
    """
    Модель для хранения информации о попытке пользователя пройти викторину.
    """

    nickname = models.CharField(max_length=50)
    theme = models.CharField(max_length=100)
    difficulty = models.CharField(max_length=50)
    question_type = models.CharField(
        max_length=50,
        help_text="Тип вопроса: множественный выбор, правда/ложь, числовой",
    )
    timer = models.PositiveIntegerField(help_text="Время викторины в секундах")
    created_at = models.DateTimeField(auto_now_add=True)
    # Поле для хранения итоговой оценки, ошибок или сохраненного диалога
    result_summary = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nickname} - {self.theme} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class QuizDialogue(models.Model):
    """
    Модель для хранения диалога между моделью и пользователем по конкретной попытке.
    """

    attempt = models.ForeignKey(
        QuizAttempt, related_name="dialogues", on_delete=models.CASCADE
    )
    sender = models.CharField(
        max_length=20, choices=[("user", "Пользователь"), ("model", "Модель")]
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.sender}: {self.message[:30]}..."
