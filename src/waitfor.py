"""Wait until a TCP service accepts connections (for CI service containers). Exponential backoff with a deadline; returns the attempts used."""
import socket, time

class NotReady(Exception): pass

def wait_for_port(host, port, timeout=30.0, initial=0.1, factor=2.0, max_delay=2.0, clock=time.monotonic, sleep=time.sleep):
    deadline, delay, attempts = clock() + timeout, initial, 0
    while True:
        attempts += 1
        try:
            with socket.create_connection((host, port), timeout=min(1.0, max(0.05, deadline - clock()))): return attempts
        except OSError:
            if clock() + delay > deadline: raise NotReady(f"{host}:{port} not accepting connections after {attempts} attempts / {timeout} s")
            sleep(delay); delay = min(delay * factor, max_delay)
