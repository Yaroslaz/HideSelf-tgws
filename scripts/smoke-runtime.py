"""Validate the managed EXE without accessing Telegram or changing VPN settings."""
import socket
import subprocess
import sys
import time
from pathlib import Path


def main():
    binary = str(Path(sys.argv[1]).resolve())
    help_result = subprocess.run([binary, '--help'], capture_output=True,
                                 text=True, timeout=30, check=True)
    for flag in ('--host', '--port', '--secret', '--no-secure', '--dc-ip [DC:IP]', '--no-h2'):
        if flag not in help_result.stdout:
            raise RuntimeError(f'Missing runtime capability: {flag}')

    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    process = subprocess.Popen([
        binary, '--host', '127.0.0.1', '--port', str(port),
        '--secret', '0123456789abcdef0123456789abcdef',
        # Explicit domains prevent the startup refresh from accessing GitHub.
        # With no DC redirects or warm pool, H2 initializes without dialing out.
        '--cfproxy-domain', 'smoke.invalid', '--dc-ip', '--pool-size', '0',
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f'Runtime exited: {process.communicate()[0]}')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.3):
                    print('Frozen runtime: CA bundle, H2 imports, CLI and loopback listener OK')
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError('Runtime listener did not become ready')
    finally:
        if sys.platform == 'win32' and process.poll() is None:
            # A onefile EXE has a bootloader parent and a runtime child.
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, timeout=10, check=True)
        elif process.poll() is None:
            process.terminate()
        process.communicate(timeout=10)


if __name__ == '__main__':
    main()
