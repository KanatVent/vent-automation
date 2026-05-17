import json
import re
from abc import ABC, abstractmethod
from pathlib import Path

import fitz  # PyMuPDF


class BaseSupplier(ABC):
    """
    Базовый класс для всех поставщиков.
    Каждый поставщик наследует этот класс и при необходимости
    переопределяет методы под свою специфику.
    """

    # Коэффициент пересчёта: курс × наценка × НДС КЗ
    RATE = 7.3
    MARKUP = 1.40
    VAT_KZ = 1.16

    @property
    @abstractmethod
    def supplier_name(self) -> str:
        """Название поставщика"""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Системный промпт для Claude API — специфика поставщика"""
        pass

    def extract_text(self, pdf_path: str) -> str:
        """Извлекает текст из PDF"""
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text

    def parse(self, pdf_path: str) -> list[dict]:
        """
        Главный метод. Принимает путь к PDF счёта.
        Возвращает список систем со стандартным форматом:
        [
            {
                "system": "П1",
                "items": [
                    {
                        "name": "Вентиляционная установка RW-14...",
                        "qty": 1,
                        "unit": "шт",
                        "price_rub": 551035.08,
                        "price_kzt": 6532631.0,
                        "summa_kzt": 6532631.0
                    },
                    ...
                ]
            },
            ...
        ]
        """
        text = self.extract_text(pdf_path)
        raw = self._call_claude(text)
        result = self._apply_conversion(raw)
        return result

    def _call_claude(self, text: str) -> list[dict]:
        """Вызов Claude API для парсинга текста счёта"""
        import anthropic
        client = anthropic.Anthropic()

        user_prompt = f"""
Вот текст счёта от поставщика. Извлеки все позиции, сгруппированные по системам.

ТЕКСТ СЧЁТА:
{text}
"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        raw_text = response.content[0].text
        # Убираем markdown-обёртку если есть
        clean = re.sub(r"```json|```", "", raw_text).strip()
        return json.loads(clean)

    def _apply_conversion(self, systems: list[dict]) -> list[dict]:
        """Применяет формулу пересчёта цен: руб × курс × наценка × НДС КЗ"""
        k = self.RATE * self.MARKUP * self.VAT_KZ
        for system in systems:
            for item in system.get("items", []):
                price_rub = item.get("price_rub", 0)
                qty = item.get("qty", 1)
                item["price_kzt"] = round(price_rub * k)
                item["summa_kzt"] = round(price_rub * k * qty)
        return systems
