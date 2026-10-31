# Upstream Changelog (v1.11.3)

**Title:** TG WS Proxy v1.11.3

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.11.3

**Published at:** 2026-10-30T16:05:45Z

## Upstream Notes

* TLS соединение больше не будет создаваться с `X25519MLKEM768`, который создавал слишком большой ClientHello, который в свою очередь мог спровоцировать триггер DPI (из-за чего могли быть ошибки TimeoutError)
  * **Несовместимо с некоторыми ОС. Используйте пока что v1.11.2; правка совместимости будет в следующем обновлении**
* Добавлена поддержка --no-secure для Docker by @partoftheworlD in https://github.com/Flowseal/tg-ws-proxy/pull/1493
* Улучшения Fake TLS by @someden in https://github.com/Flowseal/tg-ws-proxy/pull/1473

## HideSelf Adaptation

- Синхронизировано с upstream тегом `v1.11.3`.
- Формат релиза HideSelf runtime не меняется: публикуется managed Windows binary `hideself-tgws_windows.exe`.
- При merge-конфликте для fork-owned файлов сохраняется версия HideSelf (`.github/workflows/build.yml`, `docs/README.md`).

<!--hs-upstream tag=v1.11.3 commit=73aa394-->
