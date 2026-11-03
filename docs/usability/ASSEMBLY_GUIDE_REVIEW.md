# Assembly guide review

The Build it guide now identifies individual hardware locations, their receiving part and insertion direction. Each selected location starts still. Replay demonstrates insert pressing with a schematic iron, driving a screw, or seating a supported pivot. Pause, Show location and Assembly overview let the user inspect the action. Incoming-position ghosts and alignment paths use the existing assembly offsets; recorded instructions and joint demonstrations support the final manual check.

## Evidence

- Producer PR [#64](https://github.com/Schponken/kerf-forge/pull/64), bf3c3e5; viewer PR [#65](https://github.com/Schponken/kerf-forge/pull/65), 7ad8095. Combined application source tested at 7a97024.
- 14 combined focused tests passed in 16.91 seconds. Source-owner viewer slice: seven tests passed, then the changed final placement regression passed.
- Real saved finger desktop and phone views, paused iron contact and drone step 2 with ten installation sites were inspected. Corrections reduced duplicate explanation, exposed local replay, moved the label off the tool contact and kept phone navigation off the opening.
- Native installed Studio verified the finger insert and M3 shoulder-screw sites, local replay and step navigation after restart.
- Temporary finger recovery retained fingerprint 69c05ed7665e2c58 and exactly reproduced saved home vertices and triangles for all four parts. Only saved steps changed; all other payload fields and 20 prior modified project source files were preserved.

## Limits

No full suite, strength simulation or physical assembly validation was run. Tool shapes, speeds and smoke are illustrative. Unrecorded dowel seating remains unknown; no location is invented. Existing saved guides use the new controls immediately, while missing producer metadata requires a future build; the finger was refreshed with the verified recovery above. Small-screen labels share limited space with model context, while the selected receiver remains readable in the guide panel.

Local receipts and captures are in `.cache/assembly-guide-integration/`. Installation rollback copies and a file-hash manifest are in `~/Library/Application Support/KerfStudio/backups/20261102-230847-assembly-guide`.
