# habitat — kaynak ve teslim kaydı

14 Kasım 2026 · NASA hazır model.

Bu dosya bir görsel varlık kaydıdır. Boyut, yerleşim ve görevdeki kullanım SCENARIO’dur; NASA ölçümü, flight CAD, sensör kalibrasyonu veya robot kontrol sistemi sayılmaz.

Gerçekte işlenen kaynak: `incoming\habitat\source.glb`. Orijinal dosyalar korunmuştur.

Kaynak: [https://science.nasa.gov/3d-resources/habitat-demonstration-unit/](https://science.nasa.gov/3d-resources/habitat-demonstration-unit/).
Atıf: NASA/LaRC/Advanced Concepts Lab; part 1.
Kullanım: [NASA Media Usage Guidelines; third-party/identifier restrictions remain](https://www.nasa.gov/nasa-brand-center/images-and-media/).

NASA tanımlayıcıları ve üçüncü taraf haklarına ilişkin kaynak koşulları sürer; NASA desteği/onayı ima edilmez.

Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, ayrı parça OBJ’leri, basit çarpışma proxy’leri ve önizlemeler. Gazebo `visual.sdf` yalnız statik görsel yükleme içindir; URDF/link/joint, inertia, ROS topic, uçuş ve navigasyon kontrolü içermez.

Ölçülen LOD0: 2,264 üçgen; 1 malzeme; 2 parça. Gazebo visual: 2,264 üçgen.
Blender 5.2.3 LTS; FBX binary 7400. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı. FBX/OBJ dönüşüm ayarları ve parça pivotları asset.json içinde.

Yerel yeniden içe aktarma: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü, materyal/normal bağlama ve robot kontrolü: **yapılmadı**. 1 m test küpü ve eksen okları `assets/calibration/` içinde.

Açık sınırlar:

- NASA source part 1 is used; source part 2 is an optional reference. The airlock end door is separated for presentation. Interior, hinge operation and ingress collision remain unverified.

Revizyon (2026-11-14): NASA insignia, US flags, the HAB X logo and HDU emblems removed (proje kÄ±lavuzu Â§8: no NASA brand elements; NASA media guidelines restrict insignia use). Generic Segment/AIRLOCK signage kept. Ayrıntı `asset.json → revisions`.

