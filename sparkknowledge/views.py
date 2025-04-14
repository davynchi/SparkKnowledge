"""
Модуль представлений приложения SparkKnowledge.
"""

import json
import time

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from httpx import ConnectError, HTTPStatusError
from mistralai.models.sdkerror import SDKError

from sparkknowledge.forms import QuizSetupForm
from sparkknowledge.llm_client import MistralClient
from sparkknowledge.models import QuizAttempt

# Инициализируем LLM-клиент
llm_client = MistralClient()


def setup_view(request):
    """
    Представление для настройки викторины. Отображает форму и создаёт попытку.
    После создания новой попытки очищает сессионные ключи для диалога и времени.
    """
    if request.method == "POST":
        form = QuizSetupForm(request.POST)
        if form.is_valid():
            attempt = QuizAttempt.objects.create(
                nickname=form.cleaned_data["nickname"],
                theme=form.cleaned_data["theme"],
                difficulty=form.cleaned_data["difficulty"],
                question_type=form.cleaned_data["question_type"],
                timer=form.cleaned_data["timer"],
            )
            # Очистка сессионных ключей для нового задания
            conv_key = f"conversation_{attempt.id}"
            start_key = f"quiz_start_time_{attempt.id}"
            if conv_key in request.session:
                del request.session[conv_key]
            if start_key in request.session:
                del request.session[start_key]
            return redirect(
                reverse("sparkknowledge:quiz_run", kwargs={"attempt_id": attempt.id})
            )
    else:
        form = QuizSetupForm()
    return render(request, "sparkknowledge/setup.html", {"form": form})


def quiz_run_view(request, attempt_id):
    """
    Представление для проведения викторины.
    Если тип задания "multiple", из ответа модели выделяются последние 4 строки как варианты.
    Поддерживается LaTeX: в системных инструкциях требуем
    использовать формат LaTeX для математических выражений.
    Отображается только блок "Ответ модели" (feedback) без отдельного вывода текста задания.
    """
    attempt = get_object_or_404(QuizAttempt, id=attempt_id)
    conv_key = f"conversation_{attempt_id}"
    start_key = f"quiz_start_time_{attempt_id}"
    conversation = request.session.get(conv_key, [])

    # Сохраняем время начала викторины, если ещё не сохранено.
    if start_key not in request.session:
        request.session[start_key] = time.time()
    quiz_start_time = request.session[start_key]
    elapsed_time = int(time.time() - quiz_start_time)
    remaining_time = max(attempt.timer - elapsed_time, 0)

    def parse_multiple_options(text):
        """
        Разбивает текст на непустые строки.
        Если строк 4 и более, считает последние 4 как варианты ответа.
        """
        lines = [
            line.strip() for line in text.strip().split("\n") if line.strip() != ""
        ]
        if len(lines) >= 4:
            options = lines[-4:]
        else:
            options = []
        return options

    if request.method == "GET":
        if not conversation:
            initial_prompt = (
                f"Ты образовательная модель для викторин по теме '{attempt.theme}'. "
                f"Уровень сложности: '{attempt.difficulty}'. "
                f"Тип задания: '{attempt.question_type}'. "
                "Сформулируй ТОЛЬКО задание без лишнего текста. "
                "Если задание имеет формат множественного выбора, "
                "последние четыре строки должны быть вариантами "
                "(A, B, C, D) и не содержать пустых строк. "
                "Если выбран тип 'Числовой ответ', не печатай варианты ответа. "
                "Если необходимо записать математическое выражение, используй формат LaTeX "
                "(оборачивай его в $...$ или $$...$$)."
            )
            try:
                initial_assignment = llm_client.complete_chat(
                    prompt="",
                    messages=[{"role": "system", "content": initial_prompt}],
                )
            except (SDKError, ConnectError, HTTPStatusError) as exc:
                if isinstance(exc, ConnectError):
                    error_message = (
                        "Возникли проблемы с соединением. Повторите попытку позже."
                    )
                else:
                    error_message = (
                        "Сервис Mistral временно недоступен из-за превышения "
                        "количества запросов. Повторите попытку позже."
                    )
                conversation = [{"role": "assistant", "content": error_message}]
                request.session[conv_key] = conversation
                context = {
                    "attempt": attempt,
                    "history": conversation,
                    "error": error_message,
                    "remaining_time": remaining_time,
                }
                return render(request, "sparkknowledge/quiz_run.html", context)
            conversation = [{"role": "assistant", "content": initial_assignment}]
            request.session[conv_key] = conversation

        # Формируем отображаемый диалог:
        if len(conversation) == 1:
            history = conversation
            feedback = conversation[0]["content"]
        else:
            history = conversation[:-1]
            feedback = conversation[-1]["content"]

        context = {
            "attempt": attempt,
            "history": history,
            "feedback": feedback,
            "remaining_time": remaining_time,
        }
        if attempt.question_type == "multiple":
            options = parse_multiple_options(conversation[-1]["content"])
            context.update(
                {
                    "multiple_options": options,
                }
            )
        return render(request, "sparkknowledge/quiz_run.html", context)

    if request.method == "POST":
        if "finish" in request.POST:
            attempt.result_summary = json.dumps(conversation, ensure_ascii=False)
            attempt.save()
            request.session.pop(conv_key, None)
            request.session.pop(start_key, None)
            return redirect(
                reverse(
                    "sparkknowledge:attempt_detail", kwargs={"attempt_id": attempt.id}
                )
            )

        if attempt.question_type == "multiple":
            user_answer = request.POST.get("selected_option", "").strip()
        else:
            user_answer = request.POST.get("answer", "").strip()

        if not user_answer:
            context = {
                "attempt": attempt,
                "error": "Пожалуйста, введите ответ.",
                "history": conversation,
                "remaining_time": remaining_time,
            }
            if attempt.question_type == "multiple":
                options = parse_multiple_options(conversation[-1]["content"])
                context.update({"multiple_options": options})
            return render(request, "sparkknowledge/quiz_run.html", context)

        conversation.append({"role": "user", "content": user_answer})
        messages = []
        for msg in conversation:
            role = msg["role"] if msg["role"] != "model" else "assistant"
            messages.append({"role": role, "content": msg["content"]})
        evaluation_prompt = (
            "Оцени правильность ответа пользователя. Если ответ неверный, "
            "кратко объясни ошибки и приведи правильный ответ. "
            "Затем сформулируй ТОЛЬКО новое задание по той же теме. "
            "Если задание имеет формат множественного выбора, "
            "последние четыре строки должны быть вариантами "
            "(A, B, C, D) и не содержать пустых строк. "
            "Если выбран тип задания 'Числовой ответ', не включай никаких вариантов ответа. "
            "Если необходимо записать математическое выражение, "
            "используй формат LaTeX (оборачивай его в $...$ или $$...$$)."
        )
        messages.append({"role": "system", "content": evaluation_prompt})
        try:
            model_response = llm_client.complete_chat(prompt="", messages=messages)
        except (SDKError, ConnectError, HTTPStatusError) as exc:
            if isinstance(exc, ConnectError):
                error_message = (
                    "Возникли проблемы с соединением. Повторите попытку позже."
                )
            else:
                error_message = (
                    "Сервис Mistral временно недоступен из-за превышения "
                    "количества запросов. Повторите попытку позже."
                )
            context = {
                "attempt": attempt,
                "history": conversation,
                "error": error_message,
                "remaining_time": remaining_time,
            }
            if attempt.question_type == "multiple":
                options = parse_multiple_options(conversation[-1]["content"])
                context.update({"multiple_options": options})
            return render(request, "sparkknowledge/quiz_run.html", context)

        conversation.append({"role": "assistant", "content": model_response})
        request.session[conv_key] = conversation

        if len(conversation) > 1:
            history = conversation[:-1]
            feedback = conversation[-1]["content"]
        else:
            history = conversation
            feedback = conversation[-1]["content"] if conversation else ""
        context = {
            "attempt": attempt,
            "history": history,
            "feedback": feedback,
            "remaining_time": remaining_time,
        }
        if attempt.question_type == "multiple":
            options = parse_multiple_options(model_response)
            context.update({"multiple_options": options})
        return render(request, "sparkknowledge/quiz_run.html", context)


def attempt_list_view(request):
    """
    Отображает список всех попыток викторины.
    """
    attempts = QuizAttempt.objects.all().order_by("-created_at")
    return render(request, "sparkknowledge/attempt_list.html", {"attempts": attempts})


def attempt_detail_view(request, attempt_id):
    """
    Отображает детали конкретной попытки викторины.
    """
    attempt = get_object_or_404(QuizAttempt, id=attempt_id)
    conversation_lines = []
    if attempt.result_summary:
        try:
            conversation_lines = json.loads(attempt.result_summary)
        except json.JSONDecodeError:
            conversation_lines = []
    return render(
        request,
        "sparkknowledge/attempt_detail.html",
        {"attempt": attempt, "conversation_lines": conversation_lines},
    )


def about_view(request):
    """
    Отображает страницу с правилами викторины.
    """
    return render(request, "sparkknowledge/about.html")
