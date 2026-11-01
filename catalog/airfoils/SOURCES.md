# Airfoil coordinates

Files are saved unchanged (Selig format: name line, then x/c y/c from the trailing edge over the upper surface to the
leading edge and back along the lower surface). Aerodynamic numbers per airfoil are in `airfoils.json`.

| File | Airfoil | Coordinates URL | Retrieved | Licence / use note |
|---|---|---|---|---|
| mh45.dat | Martin Hepperle MH 45, 9.85 %, reflexed flying-wing section | https://m-selig.ae.illinois.edu/ads/coord/mh45.dat | 2026-11-01 (curl) | UIUC Airfoil Coordinates Database (https://m-selig.ae.illinois.edu/ads/coord_database.html) states no licence. The designer's page (https://mh-aerotools.de/airfoils/foil_flyingwings.htm) says "You may use the data given in this document for your personal use" and "If you use this document for a publication, you have to cite the source." Cite: M. Hepperle, MH 45, via UIUC (M. Selig). |
| mh60.dat | Martin Hepperle MH 60, 10.08 %, reflexed flying-wing section | https://m-selig.ae.illinois.edu/ads/coord/mh60.dat | 2026-11-01 (curl) | Same as mh45.dat. |

Checked after download (catalog/airfoils/*.dat, 0..1 chord resampled, `numpy.interp`): MH 45 max thickness 9.85 % at
27.6 % chord, max camber 1.71 %, camber line below the chord aft of ~90 % (reflex: -0.085 % at 98 %); MH 60 10.08 % at
27.7 %, camber 1.82 %, -0.092 % at 98 %. These match the header lines and airfoiltools.com (9.8 % / 10.1 % at 26.9 %).

MH 64 (8.59 %, https://m-selig.ae.illinois.edu/ads/coord/mh64.dat) was also downloaded and rejected as a thin tip
section: its XFOIL Cm0 at Re 200k is -0.0245 (twice MH 45's) and CLmax 1.06 (vs 1.19), i.e. a thinner tip would add
nose-down moment and stall earlier exactly where tip stall must be avoided.
