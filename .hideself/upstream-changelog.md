# Upstream Changelog (v1.7.0)

**Title:** TG WS Proxy v1.7.0

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.7.0

**Published at:** 2026-05-16T08:36:48Z

## Upstream Notes

- Добавлен новый режим **Cloudflare Worker** — бесплатный способ проксирования.
  - https://github.com/Flowseal/tg-ws-proxy/blob/main/docs/CfWorker.md
  - Это альтернатива CF-прокси, но для Worker'а не нужно покупать домен.
- Убран `--cfproxy-priority`. Теперь приоритет всегда такой: `CF-прокси (если включён)` -> `CF-worker (если указан домен)` -> `Direct`.

## HideSelf Adaptation

- Синхронизировано с upstream тегом `v1.7.0`.
- Формат релиза HideSelf runtime не меняется: публикуется managed Windows binary `hideself-tgws_windows.exe`.
- Upstream workflow-файлы не импортируются в merge-коммит, чтобы `GITHUB_TOKEN` без `workflows` permission мог push-ить результат синхронизации.
- При конфликте в `proxy/tg_ws_proxy.py` берётся upstream-реализация, чтобы новые CLI-флаги TG WS попадали в runtime.
