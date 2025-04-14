from django import forms


class QuizSetupForm(forms.Form):
    """
    Форма для настройки параметров викторины.
    """

    nickname = forms.CharField(
        max_length=50,
        label="Никнейм",
        error_messages={"required": 'Поле "Никнейм" не заполнено.'},
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Ваш никнейм"}
        ),
    )
    theme = forms.CharField(
        max_length=100,
        label="Тема",
        error_messages={"required": 'Поле "Тема" не заполнено.'},
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Например, английский язык, физика",
            }
        ),
    )
    difficulty = forms.ChoiceField(
        choices=[("easy", "Легко"), ("medium", "Средне"), ("hard", "Сложно")],
        label="Сложность",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    question_type = forms.ChoiceField(
        choices=[
            ("multiple", "Множественный выбор"),
            ("numeric", "Числовой ответ"),
        ],
        label="Тип задания",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    timer = forms.IntegerField(
        label="Время викторины (секунды)",
        min_value=10,
        initial=60,  # Значение по умолчанию 60 секунд
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
