# VPf09 — Telegram-бот (aiogram + ProxyAPI)

## Запуск бота

```powershell
cd D:\vibe-coding\VPf09
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Заполните .env по образцу EnvExample
python main.py
```

## Команды

- `/start`, `/help` — справка
- `/mode` — режимы чата (см. `prompts.json`)
- `/reset` — очистить историю
- `/image <промпт>` — генерация картинки (gpt-image-2)
- `/image` — режим изображений (следующее сообщение = промпт)
- `/chat` — вернуться к текстовому диалогу

## Генерация изображений

Модель `gpt-image-2` через ProxyAPI (те же `PROXY_API_KEY` и `OPENAI_BASE_URL`):

- `/image закат над морем` — сразу сгенерировать
- `/image` — войти в режим: следующее текстовое сообщение = промпт
- `/chat` — вернуться к обычному диалогу

В `.env`: `IMAGE_MODEL=gpt-image-2` (см. `EnvExample`).

### Обновление тарифов вручную

```powershell
python scripts/update_proxyapi_pricing.py
```

## Стоимость запросов

После каждого ответа в чате и после `/image` бот показывает:

- токены ввода/вывода;
- тариф ProxyAPI из `proxyapi_pricing.json` ([страница тарифов](https://proxyapi.ru/pricing), обновляется при старте);
- итог в рублях и эквивалент в USD по курсу ЦБ (`CBR_JSON_URL`).
