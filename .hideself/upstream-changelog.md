# Upstream Changelog (v1.9.0)

**Title:** TG WS Proxy v1.9.0

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.9.0

**Published at:** 2026-07-28T08:54:30Z

## Upstream Notes

- Исправлен баг, когда автозапуск не применялся
- Pool прямых соединений теперь всегда пересоздаёт idle соединения, если они закрылись
- Более быстрые подключения к DC
- Поддержка тестовых DC by @itzme1on in https://github.com/Flowseal/tg-ws-proxy/pull/1087
  - https://github.com/Flowseal/tg-ws-proxy/blob/main/docs/TestDc.md

## HideSelf Adaptation

- Синхронизировано с upstream тегом `v1.9.0`.
- Формат релиза HideSelf runtime не меняется: публикуется managed Windows binary `hideself-tgws_windows.exe`.
- При merge-конфликте для fork-owned файлов сохраняется версия HideSelf (`.github/workflows/build.yml`, `docs/README.md`).

