import socket, threading, time, pytest
from waitfor import wait_for_port, NotReady
def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
def test_immediate():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(1); assert wait_for_port("127.0.0.1", s.getsockname()[1], timeout=2) == 1; s.close()
def test_service_comes_up_late():
    p = free_port(); holder = {}
    def start_later():
        time.sleep(0.6); s = socket.socket(); s.bind(("127.0.0.1", p)); s.listen(1); holder["s"] = s; time.sleep(1.5)
    threading.Thread(target=start_later, daemon=True).start()
    t = time.time(); attempts = wait_for_port("127.0.0.1", p, timeout=5); assert attempts > 1 and 0.5 < time.time() - t < 3
def test_gives_up_with_clear_error():
    with pytest.raises(NotReady, match="not accepting"): wait_for_port("127.0.0.1", free_port(), timeout=0.5, initial=0.05)
def test_backoff_delays_grow_and_cap():
    delays = []; fake = [0.0]
    with pytest.raises(NotReady): wait_for_port("127.0.0.1", free_port(), timeout=10, initial=0.1, factor=2, max_delay=1.0, clock=lambda: fake[0], sleep=lambda d: (delays.append(d), fake.__setitem__(0, fake[0] + d)))
    assert delays[:5] == [0.1, 0.2, 0.4, 0.8, 1.0] and max(delays) == 1.0
