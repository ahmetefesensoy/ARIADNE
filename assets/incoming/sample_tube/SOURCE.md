# sample_tube — kaynak ve teslim kaydı

14 Kasım 2026 · NASA hazır model.

Bu dosya bir görsel varlık kaydıdır. Boyut, yerleşim ve görevdeki kullanım SCENARIO’dur; NASA ölçümü, flight CAD, sensör kalibrasyonu veya robot kontrol sistemi sayılmaz.

Gerçekte işlenen kaynak: `incoming\sample_tube\source.stl`. Orijinal dosyalar korunmuştur.

Kaynak: [https://science.nasa.gov/3d-resources/mars-2020-sample-tube/](https://science.nasa.gov/3d-resources/mars-2020-sample-tube/).
Atıf: NASA/JPL-Caltech; printable sample-tube model.
Kullanım: [NASA Media Usage Guidelines; third-party/identifier restrictions remain](https://www.nasa.gov/nasa-brand-center/images-and-media/).

NASA tanımlayıcıları ve üçüncü taraf haklarına ilişkin kaynak koşulları sürer; NASA desteği/onayı ima edilmez.

Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, ayrı parça OBJ’leri, basit çarpışma proxy’leri ve önizlemeler. Gazebo `visual.sdf` yalnız statik görsel yükleme içindir; URDF/link/joint, inertia, ROS topic, uçuş ve navigasyon kontrolü içermez.

Ölçülen LOD0: 6,998 üçgen; 1 malzeme; 2 parça. Gazebo visual: 1,498 üçgen.
Blender 5.2.3 LTS; FBX binary 7400. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı. FBX/OBJ dönüşüm ayarları ve parça pivotları asset.json içinde.

Yerel yeniden içe aktarma: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü, materyal/normal bağlama ve robot kontrolü: **yapılmadı**. 1 m test küpü ve eksen okları `assets/calibration/` içinde.

Açık sınırlar:

- The printable NASA STL was split into a tube and a separate scenario cap at source z=4.05. The cut was closed; flight sealing, internal volume and sample containment are not modeled.

