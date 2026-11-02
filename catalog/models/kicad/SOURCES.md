# KiCad 3D models (kicad-packages3D)

Copied unmodified from the KiCad library (https://gitlab.com/kicad/libraries/kicad-packages3D, branch master at
commit 8975715167d1a76f9b44be155ac02326f704cdbb, 2026-10-10), fetched with gitlab's raw-file URL (only the files below;
the library is several GB). `proxy: step` (kerf/vendor.py) checks each one against its catalog entry (bounding box
within 0.5 mm, a real hole at every fastener site) before it is used.

Licence: KiCad libraries, CC-BY-SA 4.0 with the KiCad design exception ("To the extent that the creation of electronic
designs that use 'Licensed Material' can be considered to be 'Adapted Material', then the copyright holder waives
article 3 of the license with respect to these designs and any generated files which use data provided as part of the
'Licensed Material'.", https://gitlab.com/kicad/libraries/kicad-packages3D/-/raw/master/LICENSE.md).

| file | part | catalog entry | source (opened 2026-11-01) | sha256 |
|---|---|---|---|---|
| AMASS_XT60-M_1x02_P7.2mm_Vertical.step | AMASS XT60 male: body 15.9 x 8.1 x 16 + two 4.3 mm contacts 4.5 mm past the body (3 solids) | drone.connectors.XT60 | https://gitlab.com/kicad/libraries/kicad-packages3D/-/raw/master/Connector_AMASS.3dshapes/AMASS_XT60-M_1x02_P7.2mm_Vertical.step | 79c46051de822e2939ebbdbe2d708897adffa66bdc61a011b7f559c4a8565679 |

## Placing a model (project.yaml)
KiCad draws the XT60-M standing on its contacts: mating face up at Z = 16, contacts down to Z = -4.5, the 16 mm body
side along X (-4.35..11.55), 8.1 along Y. Into the `box` proxy frame (centre of the bottom face, length along X, mating
face at -X, which is where fpv_5in's connector_access check plugs in):

    xt60: {catalog: drone.connectors.XT60, proxy: step, base: box, model: kicad/AMASS_XT60-M_1x02_P7.2mm_Vertical.step,
           model_rot: [0, -90, 0], model_pos: [5.75, 0, 4.35]}

## Checked and not used
Every board / connector proxy in the projects was looked up in kicad-packages3D (directory listings via the gitlab API,
2026-11-01). Only the XT60 (above) and the Raspberry Pi Pico (Module.3dshapes/RaspberryPi_Pico.step; the vendor's own
model is already in catalog/models/) are in the library. Not in it: Arduino Nano (Arduino publishes Eagle files only,
docs.arduino.cc A000005-cad-files.zip), Adafruit PCA9685 (Adafruit's own STEP is used instead, ../SOURCES.md), SpeedyBee
F405 V4 / F405 Mini stacks, SpeedyBee TX800, RunCam Phoenix 2, RadioMaster RP1, WAGO 221-415, MEAN WELL LRS-100-5 /
GST60A05, SCHURTER DD11 inlet, SparkFun PRT-10288 barrel-jack adapter, Raspberry Pi Zero 2 W / Camera Module 3, ESP32-DevKitC.
These keep their catalog proxy boxes.
