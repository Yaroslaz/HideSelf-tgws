# Upstream Changelog (v1.11.2)

**Title:** TG WS Proxy v1.11.2

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.11.2

**Published at:** 2026-10-11T17:01:53Z

## Upstream Notes

* Различные оптимизации и улучшение мультиплексирования
* Добавлена ручная проверка обновления, если автоматическая проверка выключена
* Добавлено авто-обновление на Linux by @Fgeeha in https://github.com/Flowseal/tg-ws-proxy/pull/1223
* Исправления CF-worker pool, актуализация документации by @holdingq0 in https://github.com/Flowseal/tg-ws-proxy/pull/1411
* Исправление некоторых переводов by @Fallout-rtg in https://github.com/Flowseal/tg-ws-proxy/pull/1419
* Исправлены комбинации клавиш (Ctrl+C/V/A) на других раскладках

## HideSelf Adaptation

- Синхронизировано с upstream тегом `v1.11.2`.
- Формат релиза HideSelf runtime не меняется: публикуется managed Windows binary `hideself-tgws_windows.exe`.
- При merge-конфликте для fork-owned файлов сохраняется версия HideSelf (`.github/workflows/build.yml`, `docs/README.md`).

<!--hs-upstream tag=v1.11.2 commit=307a384-->
