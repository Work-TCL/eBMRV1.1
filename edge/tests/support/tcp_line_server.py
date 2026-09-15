"""Real local TCP line-protocol server used to stand in for barcode scanner / balance / printer serial-
or-TCP hardware in tests -- Document 46 (SPEC-EDGE-004) PER-FR-025 ("Peripheral simulators available for
CI and validation"). This is a genuine `socket`/`threading` server bound to an ephemeral localhost port;
plugin tests connect to it exactly as they would a real device, so the socket I/O, reconnect and framing
logic in each plugin is exercised for real -- only the physical peripheral behind the line protocol is
simulated, and every test using this module says so explicitly.

Accepts one client connection at a time; when a connection drops it goes back to accepting, which is what
lets tests exercise PER-FR-020 (hot-plug/reconnect) for real against a real socket.
"""

from __future__ import annotations

import socket
import threading
from typing import Callable, Optional


class TCPLineServer:
    def __init__(self, handler: Optional[Callable[[str], Optional[str]]] = None) -> None:
        self._handler = handler
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind(("127.0.0.1", 0))
        self._server_sock.listen(1)
        self.port = self._server_sock.getsockname()[1]
        self._conn: Optional[socket.socket] = None
        self._conn_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self._server_sock.settimeout(0.2)
        while not self._stop.is_set():
            try:
                conn, _ = self._server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            conn.settimeout(0.2)
            with self._conn_lock:
                self._conn = conn
            buffer = b""
            while not self._stop.is_set():
                try:
                    chunk = conn.recv(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if chunk == b"":
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    text = line.decode("utf-8", errors="replace").rstrip("\r")
                    if self._handler is not None:
                        response = self._handler(text)
                        if response is not None:
                            try:
                                conn.sendall((response + "\n").encode("utf-8"))
                            except OSError:
                                break
            with self._conn_lock:
                if self._conn is conn:
                    self._conn = None
            try:
                conn.close()
            except OSError:
                pass

    def push_line(self, text: str) -> None:
        """Sends one unsolicited line to the currently connected client (scanner/balance continuous
        output). No-op if nothing is connected yet -- callers should wait for a connection first."""
        with self._conn_lock:
            conn = self._conn
        if conn is not None:
            try:
                conn.sendall((text + "\n").encode("utf-8"))
            except OSError:
                pass

    def has_client(self) -> bool:
        with self._conn_lock:
            return self._conn is not None

    def drop_client_connection(self) -> None:
        """Simulates an unplugged cable / crashed device (PER-FR-020 reconnect test trigger)."""
        with self._conn_lock:
            conn = self._conn
            self._conn = None
        if conn is not None:
            try:
                conn.close()
            except OSError:
                pass

    def stop(self) -> None:
        self._stop.set()
        try:
            self._server_sock.close()
        except OSError:
            pass
        self._thread.join(timeout=2)
