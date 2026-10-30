# Vendor CAD models

Every file here is the manufacturer's own model, used as-is (no edits). `proxy: step` (kerf/vendor.py) checks each one
against its catalog entry (bounding box within 0.5 mm, a real hole at every fastener site) before it is used.

| file | part | catalog entry | source (opened) | licence | sha256 |
|---|---|---|---|---|---|
| rpi_pico.step | Raspberry Pi Pico Rev3 (STEP AP203, SolidWorks export 2021-01-22, 17 solids) | boards.rpi_pico | https://datasheets.raspberrypi.com/pico/Pico-R3-step.zip, linked from the Pico datasheet sec. 1.1 "STEP 3D" (https://pip-assets.raspberrypi.com/categories/610-raspberry-pi-pico/documents/RP-008307-DS-2-pico-datasheet.pdf) (2026-10-30) | Pico datasheet sec. 1.1 design files: "Permission to use, copy, modify, and/or distribute this design for any purpose with or without fee is hereby granted. THE DESIGN IS PROVIDED AS IS ..." (ISC-style) | ea5c693afee3de73e9fcaab1892a5ed44bf789438b9b1e5906e9c4f9859cab8b |

## Placing a model (project.yaml)
`rpi_pico.step` is drawn with the board width along +X (0..21), thickness along Y (PCB -0.5..0.5, parts up +Y) and its
length along -Z with the micro-USB at Z = -52.3. Into the `board` proxy frame (centre of the PCB bottom face, length
along X with the USB at +X, +Z up):

    pico: {catalog: boards.rpi_pico, proxy: step, base: board, model: rpi_pico.step,
           model_rot: [90, -90, 0], model_pos: [-25.5, 10.5, 0.5]}
