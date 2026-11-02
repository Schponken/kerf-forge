# Vendor CAD models

Every file here is the manufacturer's own model, used as-is (no edits). `proxy: step` (kerf/vendor.py) checks each one
against its catalog entry (bounding box within 0.5 mm, a real hole at every fastener site) before it is used.

| file | part | catalog entry | source (opened) | licence | sha256 |
|---|---|---|---|---|---|
| rpi_pico.step | Raspberry Pi Pico Rev3 (STEP AP203, SolidWorks export 2021-01-22, 17 solids) | boards.rpi_pico | https://datasheets.raspberrypi.com/pico/Pico-R3-step.zip, linked from the Pico datasheet sec. 1.1 "STEP 3D" (https://pip-assets.raspberrypi.com/categories/610-raspberry-pi-pico/documents/RP-008307-DS-2-pico-datasheet.pdf) (2026-10-30) | Pico datasheet sec. 1.1 design files: "Permission to use, copy, modify, and/or distribute this design for any purpose with or without fee is hereby granted. THE DESIGN IS PROVIDED AS IS ..." (ISC-style) | ea5c693afee3de73e9fcaab1892a5ed44bf789438b9b1e5906e9c4f9859cab8b |
| adafruit_815_pca9685.step | Adafruit 16-Channel 12-bit PWM/Servo Driver (PCA9685), product 815 (STEP AP214, Autodesk export 2023-01-20, 100 solids: PCB, 4 x 3x4 servo headers, V+ terminal block, parts) | boards.pca9685_adafruit | https://raw.githubusercontent.com/adafruit/Adafruit_CAD_Parts/main/815%20Servo%20Driver%2016%20Channel/815%20Servo%20Driver%2016%20Channel.step (Adafruit_CAD_Parts repo HEAD 36eea8c2589a779c3dc77e68fc2b26ab1978930a, the folder the catalog's source_3d names) (2026-11-01) | MIT (Adafruit_CAD_Parts LICENSE: 'Copyright (c) 2016 Adafruit Industries ... Permission is hereby granted, free of charge ...') | 71200cd8d6e03f5cd99293314124ca0f2c97ded824d0acda33f065fa140c3f6a |

## Placing a model (project.yaml)
`rpi_pico.step` is drawn with the board width along +X (0..21), thickness along Y (PCB -0.5..0.5, parts up +Y) and its
length along -Z with the micro-USB at Z = -52.3. Into the `board` proxy frame (centre of the PCB bottom face, length
along X with the USB at +X, +Z up):

    pico: {catalog: boards.rpi_pico, proxy: step, base: board, model: rpi_pico.step,
           model_rot: [90, -90, 0], model_pos: [-25.5, 10.5, 0.5]}

`adafruit_815_pca9685.step` is drawn in Adafruit's Eagle board frame (PCB bottom at Z = 0, outline x -1.905..60.325,
y -6.477..18.923; servo headers along the -y edge, V+ terminal block on the +y edge). Into the `board` proxy frame (centre
of the PCB bottom face) it only moves by the board centre; its solder tails 1.4 / 2.0 mm under the PCB are the catalog's
component_height_below + component_below_box, so the plain board proxy carries them too:

    driver: {catalog: boards.pca9685_adafruit, proxy: step, base: board, model: adafruit_815_pca9685.step,
             model_pos: [-29.21, -6.223, 0], groups: {holes: driver}}

KiCad library models are in kicad/ (kicad/SOURCES.md).
