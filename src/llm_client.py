import os
import yaml
import logging
import requests
import json
from src.database import get_data_path

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Çoklu LLM sağlayıcılarını (Gemini, OpenAI, Claude) yöneten
    ve HTTP REST istekleri ile tek bir arayüzden hizmet veren sınıf.
    """
    def __init__(self):
        self.config_path = get_data_path("config.yaml")
        self.provider = "none"
        self.settings = {}
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                if cfg and "settings" in cfg:
                    self.provider = cfg["settings"].get("active_llm_provider", "none")
                    self.settings = cfg["settings"].get("llm_providers", {})
        except Exception as e:
            logger.error(f"LLMClient yapılandırması yüklenirken hata: {e}")

    def is_enabled(self) -> bool:
        """Herhangi bir LLM sağlayıcısı aktif ve yapılandırılmış mı?"""
        if self.provider == "none":
            return False
        
        provider_settings = self.settings.get(self.provider, {})
        api_key = provider_settings.get("api_key", "")
        return bool(api_key)

    def complete(self, prompt: str, json_response: bool = True) -> str:
        """
        Aktif LLM sağlayıcısına istek atar ve yanıtı döner.
        """
        if not self.is_enabled():
            logger.warning("Aktif bir LLM sağlayıcısı veya API anahtarı tanımlı değil.")
            return ""

        provider_settings = self.settings.get(self.provider, {})
        api_key = provider_settings.get("api_key", "")
        model = provider_settings.get("model", "")

        if self.provider == "gemini":
            return self._call_gemini(api_key, model, prompt, json_response)
        elif self.provider == "openai":
            base_url = provider_settings.get("base_url", "https://api.openai.com/v1")
            return self._call_openai(api_key, model, base_url, prompt, json_response)
        elif self.provider == "claude":
            return self._call_claude(api_key, model, prompt, json_response)
        
        return ""

    def _call_gemini(self, api_key: str, model: str, prompt: str, json_response: bool) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        if json_response:
            payload["generationConfig"] = {"responseMimeType": "application/json"}
            
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30, verify=False)
            r.raise_for_status()
            res = r.json()
            text = res["candidates"][0]["content"]["parts"][0]["text"]
            return text.strip()
        except Exception as e:
            logger.error(f"Gemini API çağrı hatası: {e}")
            return ""

    def _call_openai(self, api_key: str, model: str, base_url: str, prompt: str, json_response: bool) -> str:
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }
        if json_response:
            payload["response_format"] = {"type": "json_object"}
            
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30, verify=False)
            r.raise_for_status()
            res = r.json()
            text = res["choices"][0]["message"]["content"]
            return text.strip()
        except Exception as e:
            logger.error(f"OpenAI/Uyumlu API çağrı hatası: {e}")
            return ""

    def _call_claude(self, api_key: str, model: str, prompt: str, json_response: bool) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        system_instruction = "Yanıtı sadece JSON formatında ver. Başka hiçbir açıklama metni ekleme." if json_response else ""
        
        payload = {
            "model": model,
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_instruction:
            payload["system"] = system_instruction
            
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30, verify=False)
            r.raise_for_status()
            res = r.json()
            text = res["content"][0]["text"]
            return text.strip()
        except Exception as e:
            logger.error(f"Claude API çağrı hatası: {e}")
            return ""
