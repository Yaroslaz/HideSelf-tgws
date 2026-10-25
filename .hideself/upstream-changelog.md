# Upstream Changelog (v1.10.0)

**Title:** TG WS Proxy v1.10.0

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.10.0

**Published at:** 2026-08-13T12:00:04Z

## Upstream Notes

* Переработан macOS GUI: переведен на customtkinter
* Исправление сборки Docker-образа by @partoftheworlD in https://github.com/Flowseal/tg-ws-proxy/pull/1183
* Перевод документации на английский язык by @Fallout-rtg in https://github.com/Flowseal/tg-ws-proxy/pull/1101
* Исправления by @IMDelewer in https://github.com/Flowseal/tg-ws-proxy/pull/1187

## HideSelf Adaptation

- Синхронизировано с upstream тегом `v1.10.0`.
- Формат релиза HideSelf runtime не меняется: публикуется managed Windows binary `hideself-tgws_windows.exe`.
- При merge-конфликте для fork-owned файлов сохраняется версия HideSelf (`.github/workflows/build.yml`, `docs/README.md`).
- Сборка `hs.22`: предохранитель на переборе фронтов CFProxy. Упавший фронт уходит из ротации на 60 с с удвоением до 10 минут, фронт с дозвоном «в полёте» придержан, один фолбэк пробует не больше трёх фронтов.
- Раньше мёртвый пул давал 18,7 дозвонов на каждый фолбэк и больше 2000 исходящих соединений в минуту; в стеке TUN каждое стоит двух эфемерных портов на петле, и диапазон кончался. На той же нагрузке стало 8,4 в минуту.

<!--hs-upstream tag=v1.10.0 commit=b2a8074-->
