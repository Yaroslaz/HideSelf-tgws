# Upstream Changelog (v1.11.1)

**Title:** TG WS Proxy v1.11.1

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.11.1

**Published at:** 2026-10-05T22:01:25Z

## Upstream Notes

* Исправлена обработка ошибки 404 при мультиплексировании, из-за которой загрузка медии не продолжалась

## HideSelf Adaptation

- Синхронизировано с upstream тегом `v1.11.1`.
- Формат релиза HideSelf runtime не меняется: публикуется managed Windows binary `hideself-tgws_windows.exe`.
- При merge-конфликте для fork-owned файлов сохраняется версия HideSelf (`.github/workflows/build.yml`, `docs/README.md`).

<!--hs-upstream tag=v1.11.1 commit=18175fb-->
