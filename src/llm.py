import os
from dotenv import load_dotenv
import anthropic
from src.db import log_llm_call

load_dotenv()

# Prices in USD per million tokens (input, output)
_PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-4-7":    (15.00, 75.00),
    "claude-sonnet-4-6":  ( 3.00, 15.00),
    "claude-haiku-4-5-20251001": ( 0.80,  4.00),
}

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def complete(
    *,
    system: str = "",
    prompt: str,
    purpose: str,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 1024,
) -> str:
    messages = [{"role": "user", "content": prompt}]
    kwargs = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = system

    response = _client.messages.create(**kwargs)

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    input_price, output_price = _PRICES.get(model, (0.0, 0.0))
    cost_usd = (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price

    log_llm_call(
        model=model,
        purpose=purpose,
        prompt_tokens=input_tokens,
        completion_tokens=output_tokens,
        cost_usd=cost_usd,
    )

    return response.content[0].text
