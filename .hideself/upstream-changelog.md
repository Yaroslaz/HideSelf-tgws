# Upstream Changelog (v1.12.0)

**Title:** TG WS Proxy v1.12.0

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.12.0

**Published at:** 2026-11-23T09:29:33Z

## Upstream Notes

- Исправлено возникновение большого числа занятых сокетов (#1614)
- Добавлен автоматический fallback на HTTP при CF-проксировании в случае TimeoutError
- Защита от пробинга в FakeTLS повторением ClientHello
- Исправление зависания при обновлении в папке без прав записи
- Cooldown rate-limited worker-доменов
- Различные фиксы при перезапуске прокси
- Обновление Dockerfile

## HideSelf Adaptation

- Синхронизировано с upstream тегом `v1.12.0`.
- Формат релиза HideSelf runtime не меняется: публикуется managed Windows binary `hideself-tgws_windows.exe`.
- При merge-конфликте для fork-owned файлов сохраняется версия HideSelf (`.github/workflows/build.yml`, `docs/README.md`).
- Из upstream взято исправление занятых сокетов (#1614): дозвон отменяется, когда клиент уже ушёл, а соединение, не принявшее первый пакет, сбрасывается. Взяты и починки перезапуска.
- Переход на соединение без TLS оставлен в варианте HideSelf (`hs.34`): `ws://` пробуется рядом с `wss://` через 2,5 с тишины, домены Cloudflare-прокси идут наперегонки по три. Вариант upstream перебирает их по очереди и здесь не используется.
- Предохранитель Worker оставлен свой (с `hs.23`): на ответ 429 Worker отдыхает 15 минут, а не до полуночи по UTC.
- Из `hs.34` сохранено: зависшее соединение мост закрывает через 6 секунд (`--stall-timeout`), а при всех доменах на выдержке пробует их, а не отказывает.

<!--hs-upstream tag=v1.12.0 commit=3fc8b9e-->
