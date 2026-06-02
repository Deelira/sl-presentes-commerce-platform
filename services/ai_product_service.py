import json
import os
from urllib.parse import quote

import requests

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class AIProductDescriptionService:
    PLACEHOLDER_KEYS = {
        "",
        "sua-chave-huggingface-aqui",
        "sua-chave-openai-aqui",
        "sua-chave-huggingface",
        "sua-chave-openai",
        "placeholder",
        "dummy",
        "changeme",
        "change-me",
    }

    def __init__(self):
        self.provider_mode = os.getenv("AI_PROVIDER", "auto").lower()
        self.openai_api_key = self._normalize_api_key(os.getenv("OPENAI_API_KEY"))
        self.openai_client = (
            OpenAI(api_key=self.openai_api_key) if self.openai_api_key and OpenAI else None
        )
        self.hf_api_key = self._normalize_api_key(os.getenv("HUGGINGFACE_API_KEY"))
        self.hf_model = os.getenv("HUGGINGFACE_MODEL", "google/flan-t5-large")

    def _normalize_api_key(self, raw_key: str | None) -> str | None:
        if raw_key is None:
            return None

        key = raw_key.strip()
        if not key:
            return None

        if key.lower() in self.PLACEHOLDER_KEYS:
            return None

        return key

    def build_product_prompt(
        self,
        product_name: str,
        current_description: str = "",
        references: dict | None = None,
    ) -> str:
        return f"""Você é um redator premium de e-commerce, com expertise em marketplaces grandes e em copy que converte.

Objetivo: escrever uma descrição de produto em português, com tom sofisticado, aspiracional e altamente persuasivo, para aumentar a intenção de compra.

Produto: {product_name}
Descrição atual do lojista: {current_description or 'Nenhuma descrição informada'}
Referências de e-commerce: {json.dumps(references or {}, indent=2, ensure_ascii=False)}

Diretrizes de escrita:
- Escreva entre 110 e 150 palavras.
- Use linguagem premium, fluida e segura, como se fosse uma descrição editorial de loja de luxo.
- Destaque benefícios reais, qualidade, praticidade, acabamento e experiência do cliente.
- Inclua palavras-chave naturais para SEO, sem soar mecânico.
- Crie desejo e confiança, com um CTA leve e elegante ao final.
- Não invente especificações técnicas que não estejam no contexto.
- Preserve o significado do produto e, quando houver uma descrição atual, refiná-la em vez de reescrever do zero.
- Evite frases genéricas como "produto incrível" ou "super qualidade".
- Use um tom moderno, belo e conversível, com foco em percepção de valor.

Exemplo de estrutura:
1. Apresentação do valor principal
2. Benefícios e diferenciais
3. Conexão emocional e percepção de exclusividade
4. CTA elegante

Descrição:"""

    def search_ecommerce(self, product_name: str) -> dict:
        """Busca referências rápidas em e-commerces populares."""
        results = {"mercadolivre": None}

        try:
            url = f"https://api.mercadolibre.com/sites/MLB/search?q={quote(product_name)}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                first_result = data.get("results", [None])[0]
                if first_result:
                    results["mercadolivre"] = {
                        "title": first_result.get("title"),
                        "description": first_result.get("description", ""),
                        "price": first_result.get("price"),
                    }
        except Exception as e:
            print(f"Erro ao buscar referências de e-commerce: {e}")

        return results

    def generate_description_with_openai(
        self,
        product_name: str,
        current_description: str = "",
        references: dict | None = None,
    ) -> str | None:
        """Gera descrição com OpenAI quando a chave estiver configurada."""
        if not self.openai_client:
            return None

        try:
            prompt = self.build_product_prompt(
                product_name,
                current_description=current_description,
                references=references,
            )

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um redator premium de e-commerce com foco em copy para conversão, marca e SEO.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                max_tokens=260,
            )

            content = response.choices[0].message.content
            if not content:
                return None

            return content.strip()
        except Exception as e:
            print(f"Erro na OpenAI: {e}")
            return None

    def generate_description_with_huggingface(
        self,
        product_name: str,
        current_description: str = "",
        references: dict | None = None,
    ) -> str | None:
        """Usa um modelo gratuito do Hugging Face com chave do usuário."""
        if not self.hf_api_key:
            return None

        try:
            prompt = self.build_product_prompt(
                product_name,
                current_description=current_description,
                references=references,
            )
            headers = {"Authorization": f"Bearer {self.hf_api_key}"}
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 220,
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "do_sample": True,
                },
            }

            response = requests.post(
                f"https://api-inference.huggingface.co/models/{self.hf_model}",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code != 200:
                print(f"Erro no HuggingFace: {response.status_code} - {response.text}")
                return None

            data = response.json()
            if isinstance(data, list):
                text = data[0].get("generated_text") or ""
            elif isinstance(data, dict):
                text = data.get("generated_text") or data.get("summary_text") or ""
            else:
                text = str(data)

            if text:
                return text.strip()

            return None
        except Exception as e:
            print(f"Erro no HuggingFace: {e}")
            return None

    def generate_description_fallback(
        self, product_name: str, current_description: str = ""
    ) -> str:
        """Gera uma descrição segura quando a IA externa não estiver disponível."""
        base = current_description.strip()

        if base:
            return (
                f"{base.rstrip('.')} — produto {product_name} com qualidade, praticidade e ótimo custo-benefício, ideal para quem busca desempenho e conveniência."
            )

        templates = [
            f"Descubra o {product_name} e aproveite um produto com qualidade, durabilidade e acabamento que valorizam seu dia a dia.",
            f"{product_name} foi pensado para oferecer conforto, praticidade e bom desempenho em cada uso.",
            f"O {product_name} combina boa relação custo-benefício, facilidade de uso e acabamento premium.",
        ]

        if "camiseta" in product_name.lower():
            return (
                f"{templates[0]} Confeccionado com materiais de boa qualidade, oferece conforto e estilo para diferentes ocasiões."
            )

        if "calça" in product_name.lower():
            return (
                f"{templates[1]} Modelagem moderna e tecido resistente para uso prático e duradouro."
            )

        return templates[0]

    def generate_product_description(
        self, product_name: str, current_description: str = ""
    ) -> dict:
        """Retorna descrição pronta e a origem da geração."""
        references = self.search_ecommerce(product_name)

        if self.provider_mode in {"hf", "auto"} and self.hf_api_key:
            description = self.generate_description_with_huggingface(
                product_name,
                current_description=current_description,
                references=references,
            )
            if description:
                return {
                    "description": description,
                    "source": "huggingface",
                    "references": references,
                }

        if self.provider_mode in {"openai", "auto"} and self.openai_client:
            description = self.generate_description_with_openai(
                product_name,
                current_description=current_description,
                references=references,
            )
            if description:
                return {
                    "description": description,
                    "source": "openai",
                    "references": references,
                }

        return {
            "description": self.generate_description_fallback(
                product_name, current_description
            ),
            "source": "fallback",
            "references": references,
        }

    def get_complete_description(self, product_name: str) -> dict:
        """Obtém descrição completa com dados de outros e-commerces."""
        result = self.generate_product_description(product_name)
        return {
            "description": result["description"],
            "ecommerce_references": result["references"],
            "source": result["source"],
        }


ai_service = AIProductDescriptionService()