# Upstream Changelog (v1.7.3)

**Title:** TG WS Proxy v1.7.3

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.7.3

**Published at:** 2026-06-17T08:15:57Z

## Upstream Notes

## What's Changed
* Добавлен портативный режим
  * Автоматически активируется, если рядом с исполняемым файлом есть папка с названием `TgWsProxy_data`
  * Либо запуском исполняемого файла с флагом `--portable`
* Добавлена сборка Windows ARM64 в Build & Release workflow by @Yan4ik000 in https://github.com/Flowseal/tg-ws-proxy/pull/943
* Фикс ротации логов (#885) by @f4rceful in https://github.com/Flowseal/tg-ws-proxy/pull/932
* Добавлено уведомление на часто возникающие ошибки вместо системного текста by @f4rceful in https://github.com/Flowseal/tg-ws-proxy/pull/924
* WS keepalive-пинги против обрыва простаивающих сессий (#646) by @f4rceful in https://github.com/Flowseal/tg-ws-proxy/pull/925
* Добавлена переменная для использования Cloudflare Worker в докер контейнере by @partoftheworlD in https://github.com/Flowseal/tg-ws-proxy/pull/996

## New Contributors
* @keeniGithub made their first contribution in https://github.com/Flowseal/tg-ws-proxy/pull/958
* @partoftheworlD made their first contribution in https://github.com/Flowseal/tg-ws-proxy/pull/996
* @Yan4ik000 made their first contribution in https://github.com/Flowseal/tg-ws-proxy/pull/943

## 
### [❤️ Поддержать развитие проекта](https://github.com/Flowseal/tg-ws-proxy/blob/main/docs/Funding.md)

> [!TIP]
> Не можете скачать?
> Добавьте `185.199.109.133 release-assets.githubusercontent.com` в hosts или воспользуйтесь зеркалом: https://sourceforge.net/projects/tg-ws-proxy.mirror/files/

## HideSelf Adaptation

- Синхронизировано с upstream тегом `v1.7.3`.
- Формат релиза HideSelf runtime не меняется: публикуется managed Windows binary `hideself-tgws_windows.exe`.
- При merge-конфликте для fork-owned файлов сохраняется версия HideSelf (`.github/workflows/build.yml`, `docs/README.md`).

