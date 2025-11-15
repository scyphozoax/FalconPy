# -*- coding: utf-8 -*-
"""
简单的 i18n 管理器
通过加载 src/i18n/<lang>.json 提供文本翻译。

使用方式：
    i18n = I18n(lang_code)
    text = i18n.t("设置")

说明：
    - 若不存在词典或缺少键，则回退为原文本。
    - 词典文件为 UTF-8 JSON，键使用中文原文，值为目标语言翻译。
"""

import json
from pathlib import Path
from typing import Dict


class I18n:
    def __init__(self, language: str = "zh_CN"):
        self.language = language
        self.translations: Dict[str, str] = {}
        self.fallback_translations: Dict[str, str] = {}
        self._load_language(language)

    @staticmethod
    def i18n_dir() -> Path:
        # src/core/i18n.py -> src/i18n/
        return Path(__file__).resolve().parents[1] / "i18n"

    @staticmethod
    def supported_languages() -> Dict[str, str]:
        return {
            "zh_CN": "简体中文",
            "en": "英语",
            "ja_JP": "日语",
            "ru": "俄语",
            "de": "德语",
            "fr": "法语",
            "es": "西班牙语",
            "pt": "葡萄牙语",
        }

    def _load_language(self, language: str):
        self.language = language
        self.translations = {}
        self.fallback_translations = {}
        try:
            lang_file = self.i18n_dir() / f"{language}.json"
            if lang_file.exists():
                with open(lang_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.translations = data
            en_file = self.i18n_dir() / "en.json"
            if en_file.exists():
                with open(en_file, "r", encoding="utf-8") as f:
                    data_en = json.load(f)
                    if isinstance(data_en, dict):
                        self.fallback_translations = data_en
        except Exception:
            # 加载失败时保持空词典，回退为原文
            self.translations = {}
            self.fallback_translations = {}

    def set_language(self, language: str):
        self._load_language(language)

    def t(self, text: str) -> str:
        # 简单键值映射：中文原文 -> 目标语言
        value = self.translations.get(text)
        if value is None or value == text:
            if self.language != "zh_CN":
                fb = self.fallback_translations.get(text)
                if fb is not None:
                    return fb
            return text
        return value