# Upstream Changelog (v1.10.4)

**Title:** TG WS Proxy v1.10.4

**Source:** https://github.com/Flowseal/tg-ws-proxy/releases/tag/v1.10.4

## Upstream Notes

TLS использует корневые сертификаты Certifi и проверяет цепочку сертификата.
Добавлены режим Cloudflare без TLS и отключение IP-маршрутов DC флагом --dc-ip без значения.

## HideSelf Adaptation

- Сохранены ограничения повторных подключений и восстановление пула Worker для стабильной работы с TUN.
- Windows-сборка остаётся headless managed-бинарником hideself-tgws_windows.exe.
- CI проверяет тесты и запуск упакованного EXE до публикации. Конфликты runtime больше не разрешаются заменой всей реализации upstream.

<!--hs-upstream tag=v1.10.4 commit=70b982d-->
