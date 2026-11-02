# Checking a bring-up program

Run `.venv/bin/kerf firmware-check servo_link` (or your project name). It regenerates the bring-up program,
compiles the Arduino sketch for the Nano, and runs it in the simavr simulator. Pi programs run against a temporary
PWM interface that records their output. The result is saved in `out/firmware/FIRMWARE_CHECK.json`.

- **PASS**: compilation and simulation passed for all checked programs. Exit code 0.
- **FAIL**: a program failed to compile, simulate, or produce the expected output. Exit code 1; fix the listed problem.
- **NOT RUN**: required tools are missing. Exit code 2. Install the missing tool reported by `kerf doctor`.
- **COMPILED ONLY**: compilation passed, but the simulator is unavailable. Exit code 2; this is incomplete proof.
- **No firmware**: the project has no generated controller program. Exit code 0 does not claim a firmware test.

`kerf build` also records this check when it generates a program. A firmware FAIL becomes a build problem;
missing simulation remains explicitly unverified. Every matching `firmware/<folder>/<folder>.ino` is checked,
including older folders already in the output. A broken second sketch cannot hide behind the first one's pass.
If an old sketch is obsolete, move it out of that directory and rerun the check.

The trace lists each joint, output pin, centre pulse and sweep. It checks the existing joint ranges, pulse limits,
50 Hz frame, no movement command before centring, and stopping output after `x`. A Nano may drive some servos
directly and others through the PCA9685 (the 16-channel servo board); both outputs are checked separately.
Project/joint labels with quotes, backslashes, newlines and Unicode are treated as text in generated source.

Setup pins Arduino CLI 1.3.1, arduino:avr 1.8.6, Servo 1.2.2, Adafruit PWM Servo Driver 3.0.2 and BusIO 1.16.2.
Arduino CLI needs its own proxy setting: setup and checks copy the session's HTTP(S) proxy into
`ARDUINO_NETWORK_PROXY` unless you explicitly set it. TLS and download checksum checks remain enabled.
The simulator needs simavr plus its development library (`simavr libsimavr-dev` on Debian/Ubuntu); a compiled
harness is cached under `.cache/arduino/avrsim`.

The simulation checks the generated program and the configured models, including the existing assumed PCA9685
oscillator frequency. It does not measure a physical servo or prove wiring on an assembled device.

## Validation in this cloud task (2026-11-02)

The Arduino index/core/library install succeeded through the configured session proxy. This container has no
sudo, so simavr 1.6+dfsg-3+b3 libraries/headers were downloaded from Debian's signed trixie package index and
extracted into a user-local cache. The real C harness was linked to that library; no simulator output was mocked
in the real-toolchain tests. No packages, ELF files, libraries or traces are committed.

`kerf firmware-check servo_link` returned PASS with a real Nano build: 7,858 bytes of flash, D9 centre
1499.94–1500.12 us, sweep −88.92° to +88.90° within the declared ±90° band. Real compiler/simulator regressions
also check PCA9685, mixed outputs, Pi, overtravel, unwired pins, an invalid second sketch and deliberately broken
programs. No physical hardware, paid simulator, full test suite or all-project build was used.
