# Upstream Changelog (v1.6.3)

**Title:** TG WS Proxy v1.6.3

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.6.3

**Published at:** 2026-04-16

## Upstream Notes

- Убраны лишние домены с `www` (Telegram не делает к ним рабочие подключения).
- Дефолтный список доменов вынесен в `.github/cfproxy-domains.txt`, чтобы его можно было обновлять через PR.

## HideSelf Adaptation

- Синхронизировано с upstream тегом `v1.6.3`.
- Формат релиза HideSelf runtime не меняется: публикуется managed Windows binary `hideself-tgws_windows.exe`.
- При merge-конфликте для fork-owned файлов сохраняется версия HideSelf (`.github/workflows/build.yml`, `docs/README.md`).
