"""Расчёт стоимости запросов: токены × тариф ProxyAPI (₽) + курс ЦБ."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from config import Settings
from utils.cbr_rates import CbrRateService
from utils.proxyapi_pricing import ProxyApiPricingStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    image_input_tokens: int = 0


@dataclass(frozen=True)
class CostBreakdown:
    usage: TokenUsage
    cost_rub: float
    usd_rub_rate: float
    cost_usd: float
    input_price_per_1m: float
    output_price_per_1m: float
    image_input_price_per_1m: float
    model_label: str


class CostCalculator:
    def __init__(
        self,
        settings: Settings,
        cbr: CbrRateService,
        pricing: ProxyApiPricingStore,
    ) -> None:
        self._settings = settings
        self._cbr = cbr
        self._pricing = pricing

    async def from_chat_usage(
        self,
        usage: Any,
        model_label: str | None = None,
    ) -> CostBreakdown:
        token_usage = _parse_chat_usage(usage)
        model = model_label or self._settings.chat_model
        input_price, output_price, image_price = self._resolve_rates(
            model,
            fallback_input=self._settings.chat_input_price_rub_per_1m,
            fallback_output=self._settings.chat_output_price_rub_per_1m,
        )
        return await self._build_breakdown(
            token_usage,
            input_price=input_price,
            output_price=output_price,
            image_input_price=image_price,
            model_label=model,
        )

    async def from_image_usage(
        self,
        usage: Any,
        model_label: str | None = None,
    ) -> CostBreakdown:
        token_usage = _parse_image_usage(usage)
        model = model_label or self._settings.image_model
        input_price, output_price, image_price = self._resolve_rates(
            model,
            fallback_input=self._settings.image_input_price_rub_per_1m,
            fallback_output=self._settings.image_output_price_rub_per_1m,
            fallback_image=self._settings.image_image_input_price_rub_per_1m,
        )
        return await self._build_breakdown(
            token_usage,
            input_price=input_price,
            output_price=output_price,
            image_input_price=image_price,
            model_label=model,
        )

    def _resolve_rates(
        self,
        model_id: str,
        *,
        fallback_input: float,
        fallback_output: float,
        fallback_image: float = 0.0,
    ) -> tuple[float, float, float]:
        parsed = self._pricing.get(model_id)
        if parsed is not None:
            return (
                parsed.input_rub_per_1m,
                parsed.output_rub_per_1m,
                parsed.image_input_rub_per_1m,
            )
        logger.warning(
            "Тариф для %s не найден в proxyapi_pricing.json, используем .env",
            model_id,
        )
        return fallback_input, fallback_output, fallback_image

    async def format_footer(self, breakdown: CostBreakdown) -> str:
        u = breakdown.usage
        lines = [
            "<b>💰 Стоимость запроса</b>",
            f"Модель: <code>{breakdown.model_label}</code>",
            f"Токены — ввод: {u.input_tokens}, вывод: {u.output_tokens}",
        ]
        if u.image_input_tokens:
            lines.append(f"Токены изображения (ввод): {u.image_input_tokens}")

        tariff_line = (
            "Тариф <a href=\"https://proxyapi.ru/pricing\">ProxyAPI</a> (₽/1M): "
            f"ввод {breakdown.input_price_per_1m:g}, "
            f"вывод {breakdown.output_price_per_1m:g}"
        )
        if self._pricing.fetched_at:
            tariff_line += f" <i>({self._pricing.fetched_at[:10]})</i>"
        lines.append(tariff_line)
        if breakdown.image_input_price_per_1m > 0:
            lines.append(
                f"изображение (ввод): {breakdown.image_input_price_per_1m:g}"
            )

        lines.append(f"<b>Итого: {breakdown.cost_rub:.4f} ₽</b>")
        lines.append(
            f"Курс ЦБ (USD): {breakdown.usd_rub_rate:.4f} ₽ "
            f"(≈ ${breakdown.cost_usd:.6f})"
        )
        return "\n".join(lines)

    async def _build_breakdown(
        self,
        usage: TokenUsage,
        *,
        input_price: float,
        output_price: float,
        image_input_price: float,
        model_label: str,
    ) -> CostBreakdown:
        cost_rub = _calc_rub(
            usage,
            input_price=input_price,
            output_price=output_price,
            image_input_price=image_input_price,
        )
        usd_rub = await self._cbr.get_usd_rub()
        cost_usd = cost_rub / usd_rub if usd_rub > 0 else 0.0

        logger.info(
            "Стоимость %s: %.4f ₽ (ввод=%d, вывод=%d, USD=%.4f)",
            model_label,
            cost_rub,
            usage.input_tokens,
            usage.output_tokens,
            usd_rub,
        )

        return CostBreakdown(
            usage=usage,
            cost_rub=cost_rub,
            usd_rub_rate=usd_rub,
            cost_usd=cost_usd,
            input_price_per_1m=input_price,
            output_price_per_1m=output_price,
            image_input_price_per_1m=image_input_price,
            model_label=model_label,
        )


def _calc_rub(
    usage: TokenUsage,
    *,
    input_price: float,
    output_price: float,
    image_input_price: float,
) -> float:
    cost = (usage.input_tokens / 1_000_000) * input_price
    cost += (usage.output_tokens / 1_000_000) * output_price
    cost += (usage.image_input_tokens / 1_000_000) * image_input_price
    return cost


def _parse_chat_usage(usage: Any) -> TokenUsage:
    if usage is None:
        return TokenUsage()

    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)

    if prompt == 0 and completion == 0:
        prompt = int(getattr(usage, "input_tokens", 0) or 0)
        completion = int(getattr(usage, "output_tokens", 0) or 0)

    return TokenUsage(input_tokens=prompt, output_tokens=completion)


def _parse_image_usage(usage: Any) -> TokenUsage:
    if usage is None:
        return TokenUsage()

    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    image_input_tokens = 0

    details = getattr(usage, "input_tokens_details", None)
    if details is not None:
        text_tokens = int(getattr(details, "text_tokens", 0) or 0)
        image_tokens = int(getattr(details, "image_tokens", 0) or 0)
        if text_tokens or image_tokens:
            input_tokens = text_tokens
            image_input_tokens = image_tokens

    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        image_input_tokens=image_input_tokens,
    )
