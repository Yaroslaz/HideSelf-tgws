# Upstream Changelog (v1.7.1)

**Title:** TG WS Proxy v1.7.1

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.7.1

**Published at:** 2026-05-30T17:39:15Z

## Upstream Notes

* Добавлена возможность указания нескольких пользовательских доменов Cloudflare Proxy и Cloudflare Worker
  * В GUI домены указываются через запятую
  * В консоли домены указываются через повтор аргументов `--cfproxy-domain` и `--cfproxy-worker-domain`
* Добавлен Pool для Cloudflare Worker
* Оптимизация: нарезка MTProto-пакетов за O(N) вместо O(N²) by @f4rceful in https://github.com/Flowseal/tg-ws-proxy/pull/913
* Системный libcrypto как fallback, если cryptography недоступен by @k1zn in https://github.com/Flowseal/tg-ws-proxy/pull/894

## 
### [❤️ Поддержать развитие проекта](https://github.com/Flowseal/tg-ws-proxy/blob/main/docs/Funding.md)

> [!TIP]
> Не можете скачать?
> Добавьте `185.199.109.133 release-assets.githubusercontent.com` в hosts или воспользуйтесь зеркалом: https://sourceforge.net/projects/tg-ws-proxy.mirror/files/

## HideSelf Adaptation

- Синхронизировано с upstream тегом `v1.7.1`.
- Формат релиза HideSelf runtime не меняется: публикуется managed Windows binary `hideself-tgws_windows.exe`.
- При merge-конфликте для fork-owned файлов сохраняется версия HideSelf (`.github/workflows/build.yml`, `docs/README.md`).

