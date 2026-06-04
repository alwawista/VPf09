# VPf09 — Telegram-бот (aiogram + ProxyAPI)

## Запуск бота

```powershell
cd D:\vibe-coding\VPf09
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Заполните .env по образцу EnvExample
python main.py
```

## Telegram через Tor

Бот ходит в Telegram API через SOCKS5 (как в VPf08 / VPf08_hometask). В `.env`:

```env
TELEGRAM_PROXY_URL=socks5://127.0.0.1:9050
```

**Tor daemon не входит в репозиторий** — он установлен отдельно (например `D:\Tor`). В git попадают только обёртки `scripts/start-tor.ps1` и `scripts/check-tor.ps1`.

### Запуск Tor (с мостами)

Конфиг: `D:\Tor\data\torrc` (Snowflake, meek, obfs4 из Expert Bundle).

```powershell
D:\Tor\start-tor.ps1
# или из корня проекта:
.\scripts\start-tor.ps1
```

Проверка circuit (`Bootstrapped 100%` в логе Tor):

```powershell
.\scripts\check-tor.ps1
```

Затем запускайте бота.

## Генерация изображений

Модель `gpt-image-2` через ProxyAPI (те же `PROXY_API_KEY` и `OPENAI_BASE_URL`):

- `/image закат над морем` — сразу сгенерировать
- `/image` — войти в режим: следующее текстовое сообщение = промпт
- `/chat` — вернуться к обычному диалогу

В `.env`: `IMAGE_MODEL=gpt-image-2` (см. `EnvExample`).

### Если bootstrap застрял на 10%

Без мостов Tor может не подняться в заблокированной сети. Свежие мосты:

- Telegram: [@GetBridgesBot](https://t.me/GetBridgesBot)
- Email: `bridges@torproject.org` (тема пустая, тело: `get transport obfs4`)
- https://bridges.torproject.org/

Добавьте `Bridge ...` в `D:\Tor\data\torrc`, перезапустите `D:\Tor\start-tor.ps1`.

### Без Tor

Оставьте `TELEGRAM_PROXY_URL` пустым в `.env` — бот подключится к Telegram напрямую (если сеть позволяет).
