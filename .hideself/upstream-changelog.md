# Upstream Changelog (v1.8.0)

**Title:** TG WS Proxy v1.8.0

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.8.0

**Published at:** 2026-06-26T16:22:34Z

## Upstream Notes

## What's Changed
* Локализация (ru/en) by @rozkomnadzor in https://github.com/Flowseal/tg-ws-proxy/pull/1025
* Добавлен Fronting fallback (стандартное соединение с другим SNI как возможное решение участившихся проблем)
  * Если Вы наблюдаете в логах постоянные **`fronting failed: TimeoutError`** и **`WS connect timed out`**, то сотрите в настройках всё из поля `DC->IP`
* Увеличена доступность стандартных CF-прокси
* Откат WS keepalive (по репортам вызывал больше проблем) in https://github.com/Flowseal/tg-ws-proxy/pull/1036
* Исправлена иконка на MacOS by @IMDelewer in https://github.com/Flowseal/tg-ws-proxy/pull/1019

## New Contributors
* @rozkomnadzor made their first contribution in https://github.com/Flowseal/tg-ws-proxy/pull/1025

---
### [❤️ Поддержать развитие проекта](https://github.com/Flowseal/tg-ws-proxy/blob/main/docs/Funding.md)


> [!TIP]
> Не можете скачать?
> Добавьте `185.199.109.133 release-assets.githubusercontent.com` в hosts или воспользуйтесь зеркалом: https://sourceforge.net/projects/tg-ws-proxy.mirror/files/



## HideSelf Adaptation

- Синхронизировано с upstream тегом `v1.8.0`.
- Формат релиза HideSelf runtime не меняется: публикуется managed Windows binary `hideself-tgws_windows.exe`.
- При merge-конфликте для fork-owned файлов сохраняется версия HideSelf (`.github/workflows/build.yml`, `docs/README.md`).

