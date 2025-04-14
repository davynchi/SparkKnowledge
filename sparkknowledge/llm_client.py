import time

from django.conf import settings
from mistralai import Mistral

LLM_API_KEY = settings.LLM_API_KEY


REQUEST_DELAY = 1.0  # Не более 1 запроса в секунду


class MistralClient:
    """
    Клиент для работы с API LLM Mistral.
    """

    def __init__(self, api_key: str = LLM_API_KEY):
        self.api_key = api_key
        self.llm_model = Mistral(api_key=self.api_key)
        self.last_request_time = 0

    def complete_chat(self, prompt: str = "", messages=None) -> str:
        """
        Отправляет запрос к LLM Mistral и возвращает ответ. Можно передавать либо
        простое сообщение (prompt), либо полный список сообщений для поддержания диалога.

        :param prompt: Текст запроса для модели.
        :param messages: Список сообщений в формате [{"role": "user"|"assistant"|"system", "content": ...}, ...]
        :return: Ответ модели.
        """
        now = time.time()
        if now - self.last_request_time < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - (now - self.last_request_time))
        self.last_request_time = time.time()

        # Если список сообщений не передан, используем prompt в виде одного сообщения.
        if messages is None:
            messages = [{"role": "user", "content": prompt}]
        elif prompt:
            messages.append({"role": "user", "content": prompt})

        chat_response = self.llm_model.chat.complete(
            model="mistral-large-latest",
            messages=messages,
            temperature=0.8,  # Более детерминированный вывод
        )
        answer = chat_response.choices[0].message.content
        return answer
