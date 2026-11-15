# valve_panel — kaynak ve teslim kaydı

14 Kasım 2026 · REDLINE prosedürel · özgün.

Habitat service-line valve panel (kılavuz H06, optional Evre 5 sub-task: ArUco ID + arm action).

Handwheels and gauge needle rotate about the panel normal (master +X). ArUco plates carry the exact OpenCV pattern; keep the texture unfiltered/uncompressed so the bit cells stay sharp.

Kaynak: `production/procedural_assets.py` (SHA256 `c4d5b67d5f01b015…`), REDLINE için yazılmış özgün prosedürel geometri. Üçüncü taraf mesh veya üretken AI kullanılmadı. Ölçüler SCENARIO tasarım seçimidir; gerçek donanım ölçüsü değildir.

ArUco: `DICT_4X4_50`, kimlikler [10, 11], işaret 0.15 m, plaka 0.200 m (1 hücre beyaz kenar). Desenler OpenCV 5.0.0 ile üretildi ve PNG'den yeniden okunarak doğrulandı. Motor dokusu sıkıştırmasız/filtresiz kullanılmalı.

Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, parça OBJ'leri, basit çarpışma kutuları ve önizlemeler. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı.

Ölçülen LOD0: 3,104 üçgen; 9 parça. Gazebo visual: 3,104 üçgen.

Yerel yeniden içe aktarma ve pivot kontrolleri: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü ve materyal bağlama: **yapılmadı**.

Açık sınırlar:

- SCENARIO engineering prop: dimensions are design choices, not measured hardware.
- Flat PBR colours (textures only where noted); bevels, wear and decals are left to engine materials.
- No mass, inertia, joint limits or controller; moving parts are presentation pivots only.
- ArUco detection was verified on the source PNGs only; in-engine camera detection is NOT_RUN.
