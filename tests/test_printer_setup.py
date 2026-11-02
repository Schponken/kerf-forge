"""kerf printer setup / status (kerf/bambu.py): serial from the printer's SSDP announce, login proven by a status
read, config saved owner-only; nothing here touches a real network."""
import json
import stat

import pytest

from kerf import bambu


class FakeSock:
    def __init__(self, packets):
        self.p = list(packets)

    def settimeout(self, t):
        pass

    def recvfrom(self, n):
        if not self.p:
            raise OSError("timeout")
        return self.p.pop(0)


def test_ssdp_reads_the_serial_of_the_right_printer():
    other = (b"NOTIFY * HTTP/1.1\r\nLocation: 10.0.0.9\r\nUSN: 01P00A999999999\r\n", ("10.0.0.9", 2021))
    mine = (b"NOTIFY * HTTP/1.1\r\nHost: 239.255.255.250:1990\r\nLocation: 10.11.16.171\r\nUSN: 0309DA123456789\r\n",
            ("10.11.16.171", 2021))
    assert bambu.ssdp_serial("10.11.16.171", wait_s=2, sock=FakeSock([other, mine])) == "0309DA123456789"
    assert bambu.ssdp_serial("10.11.16.171", wait_s=0.5, sock=FakeSock([other])) is None


def test_setup_saves_owner_only_config_after_a_status_read(tmp_path):
    f = tmp_path / "bambu.json"
    f.write_text(json.dumps({"slicer": {"bin": "/x"}}))
    seen = {}
    r = bambu.setup_printer("10.11.16.171", "abcd1234", ssdp=lambda h: None, mqtt=lambda h, c: "SER1",
                            probe=lambda cfg: seen.update(cfg) or {"gcode_state": "IDLE"}, path=str(f), say=lambda s: None)
    assert r["serial"] == "SER1" and seen["printer"]["serial"] == "SER1"
    cfg = json.loads(f.read_text())
    assert cfg["printer"] == {"host": "10.11.16.171", "serial": "SER1", "access_code": "abcd1234"} and cfg["slicer"] == {"bin": "/x"}
    assert stat.S_IMODE(f.stat().st_mode) == 0o600
    with pytest.raises(RuntimeError, match="no answer"):
        bambu.setup_printer("10.0.0.1", "x", ssdp=lambda h: None, mqtt=lambda h, c: None, path=str(f), say=lambda s: None)


def test_status_needs_a_setup_and_reads_reports():
    with pytest.raises(ValueError, match="kerf printer setup"):
        bambu.status({"printer": {"host": "h"}})

    class Link:
        reports = [{"print": {"gcode_state": "IDLE", "mc_percent": 0}}]

        def publish(self, p):
            pass
    assert bambu.status({"printer": {"host": "h", "serial": "s", "access_code": "c"}}, link=Link())["gcode_state"] == "IDLE"
