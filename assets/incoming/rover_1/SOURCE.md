# rover_1 — kaynak ve teslim kaydı

14 Kasım 2026 · NASA hazır model.

Bu dosya bir görsel varlık kaydıdır. Boyut, yerleşim ve görevdeki kullanım SCENARIO’dur; NASA ölçümü, flight CAD, sensör kalibrasyonu veya robot kontrol sistemi sayılmaz.

Gerçekte işlenen kaynak: `incoming\curiosity_reference\source.blend`. Orijinal dosyalar korunmuştur.

Kaynak: [https://github.com/nasa/NASA-3D-Resources/tree/master/3D%20Models/Curiosity%20Rover%20(MSL)](https://github.com/nasa/NASA-3D-Resources/tree/master/3D%20Models/Curiosity%20Rover%20(MSL)).
Atıf: NASA/JPL-Caltech; NASA-3D-Resources.
Kullanım: [NASA Media Usage Guidelines; third-party/identifier restrictions remain](https://www.nasa.gov/nasa-brand-center/images-and-media/).

NASA tanımlayıcıları ve üçüncü taraf haklarına ilişkin kaynak koşulları sürer; NASA desteği/onayı ima edilmez.

Üretim/işleme Tripo API üzerinden yapıldı. [API koşulları](https://developers.tripo3d.ai/en/terms), [Tripo koşulları](https://www.tripo3d.ai/terms). Bu dosyalara CC0 lisansı verilmedi. Hesap abonelik türü bu paket tarafından doğrulanmaz.

- `310774f0-cd27-4265-8657-3c02c288e33d` · text_to_model · success · 50 kredi
- `089df3c5-f7e8-45c4-8072-8760fd8f6b2c` · texture_model · success · 10 kredi

Görevlerin tam istek parametreleri `asset.json → source_notice.tripo_tasks` içinde; süreli indirme URL’leri ve hesap sırları kaydedilmedi.

Prompt · `310774f0-cd27-4265-8657-3c02c288e33d`:

```text
Realistic Mars science rover, exactly six independent metal wheels, three wheels on each side, exposed rocker bogie suspension. Rectangular low insulated chassis, off-white panels, graphite mechanisms, restrained red accents, bronze metal wheel rims. Tall camera mast with separate pan and tilt head, two forward stereo camera eyes. Five-link folded robotic arm at front with shoulder elbow wrist joints and round contact science turret. Each wheel and steering knuckle, suspension member, mast head and arm link an editable separate solid, assembled neutral pose with visible gaps at moving joints. Scientific aerospace construction, physically plausible panel seams and bolts, clean silhouette, moderate dust. No astronaut, no terrain, no platform, no scenery, no text, no logos. One complete vehicle.
```

Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, ayrı parça OBJ’leri, basit çarpışma proxy’leri ve önizlemeler. Gazebo `visual.sdf` yalnız statik görsel yükleme içindir; URDF/link/joint, inertia, ROS topic, uçuş ve navigasyon kontrolü içermez.

Ölçülen LOD0: 48,492 üçgen; 4 malzeme; 82 parça. Gazebo visual: 25,003 üçgen.
Blender 5.2.3 LTS; FBX binary 7400. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı. FBX/OBJ dönüşüm ayarları ve parça pivotları asset.json içinde.

Yerel yeniden içe aktarma: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü, materyal/normal bağlama ve robot kontrolü: **yapılmadı**. 1 m test küpü ve eksen okları `assets/calibration/` içinde.

`source.glb`, teker yerleşimi nedeniyle seçilmeyen orijinal Tripo adayını korur. Teslim edilen master ve motor türevleri, `curiosity_reference/source.blend` kaynağından üretilmiştir.

Açık sınırlar:

- Tripo six-wheel candidate has the wrong wheel arrangement; native NASA Curiosity source is the delivered master. Source arm/mast pose is preserved; dynamic joint behavior remains unverified.
- NASA source provides diffuse/AO art, not calibrated instrument optics or measured material channels.

