# relay_mast — kaynak ve teslim kaydı

14 Kasım 2026 · REDLINE prosedürel · özgün.

Radio relay point (kılavuz M10 'röle direği', S05 röle noktası).

Flat-panel antenna with pan head (antenna_head, pivot at its base) and a whip.

Kaynak: `production/procedural_assets.py` (SHA256 `c4d5b67d5f01b015…`), REDLINE için yazılmış özgün prosedürel geometri. Üçüncü taraf mesh veya üretken AI kullanılmadı. Ölçüler SCENARIO tasarım seçimidir; gerçek donanım ölçüsü değildir.

Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, parça OBJ'leri, basit çarpışma kutuları ve önizlemeler. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı.

Ölçülen LOD0: 816 üçgen; 7 parça. Gazebo visual: 816 üçgen.

Yerel yeniden içe aktarma ve pivot kontrolleri: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü ve materyal bağlama: **yapılmadı**.

Açık sınırlar:

- SCENARIO engineering prop: dimensions are design choices, not measured hardware.
- Flat PBR colours (textures only where noted); bevels, wear and decals are left to engine materials.
- No mass, inertia, joint limits or controller; moving parts are presentation pivots only.
