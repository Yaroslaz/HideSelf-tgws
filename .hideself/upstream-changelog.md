# Upstream Changelog (v1.8.1)

**Title:** TG WS Proxy v1.8.1

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.8.1

**Published at:** 2026-06-26T22:34:35Z

## Upstream Notes

* Исправлены переподключения, если указанный ip из `DC->IP` недоступен in https://github.com/Flowseal/tg-ws-proxy/commit/9ff95d12223ed1b093fe84f046797821b34aa5cf
  * Первое подключение может занять в этом случае до 15 секунд, дальше будет обычная скорость подключения 

--- 
### [❤️ Поддержать развитие проекта](https://github.com/Flowseal/tg-ws-proxy/blob/main/docs/Funding.md)

> [!TIP]
> Не можете скачать?
> Добавьте `185.199.109.133 release-assets.githubusercontent.com` в hosts или воспользуйтесь зеркалом: https://sourceforge.net/projects/tg-ws-proxy.mirror/files/

## HideSelf Adaptation

- Синхронизировано с upstream тегом `v1.8.1`.
- Формат релиза HideSelf runtime не меняется: публикуется managed Windows binary `hideself-tgws_windows.exe`.
- При merge-конфликте для fork-owned файлов сохраняется версия HideSelf (`.github/workflows/build.yml`, `docs/README.md`).

