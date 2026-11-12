# Upstream Changelog (v1.11.4)

**Title:** TG WS Proxy v1.11.4

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.11.4

**Published at:** 2026-11-01T11:27:41Z

## Upstream Notes

- Исправление совместимости с другими ОС
- Различные улучшения и исправления

## Upstream main after v1.11.4

- `6690b78` Не зависать при самообновлении в папке без прав записи (#1531)
- `dbc8b78` Fake TLS: маскировать повторённый ClientHello (#1532)

## HideSelf Adaptation

- Синхронизировано с upstream тегом `v1.11.4`.
- Формат релиза HideSelf runtime не меняется: публикуется managed Windows binary `hideself-tgws_windows.exe`.
- При merge-конфликте для fork-owned файлов сохраняется версия HideSelf (`.github/workflows/build.yml`, `docs/README.md`).

<!--hs-upstream tag=v1.11.4 commit=2085861-->
