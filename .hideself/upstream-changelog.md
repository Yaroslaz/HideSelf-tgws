# Upstream Changelog (v1.10.1)

**Title:** TG WS Proxy v1.10.1

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.10.1

**Published at:** 2026-09-04T15:05:08Z

## Upstream Notes

### What's Changed
* Улучшена стабильность прямых подключений, что должно снизить общую нагрузку на CF-прокси
* Добавлена кнопка для вызова диалогового окна обновления в трей и меню настроек by @f4rceful in https://github.com/Flowseal/tg-ws-proxy/pull/1213
* Исправлены ошибки запуска на старых версиях Linux by @mvanhorn in https://github.com/Flowseal/tg-ws-proxy/pull/1238
* Открытие страницы нового релиза больше не закрывает диалоговое окно обновления

### New Contributors
* @mvanhorn made their first contribution in https://github.com/Flowseal/tg-ws-proxy/pull/1238

**Full Changelog**: https://github.com/Flowseal/tg-ws-proxy/compare/v1.10.0...v1.10.1

## HideSelf Adaptation

- Синхронизировано с upstream тегом `v1.10.1`.
- Формат релиза HideSelf runtime не меняется: публикуется managed Windows binary `hideself-tgws_windows.exe`.
- При merge-конфликте для fork-owned файлов сохраняется версия HideSelf (`.github/workflows/build.yml`, `docs/README.md`).

<!--hs-upstream tag=v1.10.1 commit=be485a3-->
