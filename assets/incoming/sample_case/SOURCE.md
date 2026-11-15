# sample_case — kaynak ve teslim kaydı

14 Kasım 2026 · Poly Haven · CC0.

Bu dosya bir görsel varlık kaydıdır. Boyut, yerleşim ve görevdeki kullanım SCENARIO’dur; NASA ölçümü, flight CAD, sensör kalibrasyonu veya robot kontrol sistemi sayılmaz.

Gerçekte işlenen kaynak: `incoming\industrial_pastic_container\source.gltf`. Orijinal dosyalar korunmuştur.

Kaynak: [https://polyhaven.com/a/industrial_pastic_container](https://polyhaven.com/a/industrial_pastic_container).
Atıf: {'Galo Benivegna': 'All'}.
Kullanım: [CC0-1.0](https://polyhaven.com/license).

Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, ayrı parça OBJ’leri, basit çarpışma proxy’leri ve önizlemeler. Gazebo `visual.sdf` yalnız statik görsel yükleme içindir; URDF/link/joint, inertia, ROS topic, uçuş ve navigasyon kontrolü içermez.

Ölçülen LOD0: 7,118 üçgen; 1 malzeme; 3 parça. Gazebo visual: 1,999 üçgen.
Blender 5.2.3 LTS; FBX binary 7400. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı. FBX/OBJ dönüşüm ayarları ve parça pivotları asset.json içinde.

Yerel yeniden içe aktarma: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü, materyal/normal bağlama ve robot kontrolü: **yapılmadı**. 1 m test küpü ve eksen okları `assets/calibration/` içinde.

Açık sınırlar:

- CC0 industrial container is a scenario carrying/cache case. Sterility and sample containment are not physically modeled.

Revizyon (2026-11-14): Blue Earth warehouse tote recoloured to the project's light-grey palette; wear and labels kept. Ayrıntı `asset.json → revisions`.

