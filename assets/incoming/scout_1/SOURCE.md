# scout_1 — kaynak ve teslim kaydı

14 Kasım 2026 · Tripo · AI üretimi.

Bu dosya bir görsel varlık kaydıdır. Boyut, yerleşim ve görevdeki kullanım SCENARIO’dur; NASA ölçümü, flight CAD, sensör kalibrasyonu veya robot kontrol sistemi sayılmaz.

Gerçekte işlenen kaynak: `incoming\scout_1\segmented\tripo-out\redline-scout-parts-97e4e850\model.glb`. Orijinal dosyalar korunmuştur.

Üretim/işleme Tripo API üzerinden yapıldı. [API koşulları](https://developers.tripo3d.ai/en/terms), [Tripo koşulları](https://www.tripo3d.ai/terms). Bu dosyalara CC0 lisansı verilmedi. Hesap abonelik türü bu paket tarafından doğrulanmaz.

- `97e4e850-f1d3-4a62-8376-3d044bd3ac73` · mesh_segmentation · success · 40 kredi
- `f91d9e38-645a-42e6-8287-a9d2266658fd` · text_to_model · success · 20.0 kredi · oturum öncesi

Görevlerin tam istek parametreleri `asset.json → source_notice.tripo_tasks` içinde; süreli indirme URL’leri ve hesap sırları kaydedilmedi.

Prompt · `f91d9e38-645a-42e6-8287-a9d2266658fd`:

```text
Compact quadrotor Mars scout drone, realistic scientific aerospace design, four separate rotors with open rotor hubs on short arms, central rectangular body with solar panel on top, small downward-facing camera on a gimbal underneath, four landing legs, matte white and grey carbon-fiber panels, neutral studio pose, single object, no ground, no text, no logo
```

Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, ayrı parça OBJ’leri, basit çarpışma proxy’leri ve önizlemeler. Gazebo `visual.sdf` yalnız statik görsel yükleme içindir; URDF/link/joint, inertia, ROS topic, uçuş ve navigasyon kontrolü içermez.

Ölçülen LOD0: 55,000 üçgen; 1 malzeme; 5 parça. Gazebo visual: 11,999 üçgen.
Blender 5.2.3 LTS; FBX binary 7400. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı. FBX/OBJ dönüşüm ayarları ve parça pivotları asset.json içinde.

Yerel yeniden içe aktarma: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü, materyal/normal bağlama ve robot kontrolü: **yapılmadı**. 1 m test küpü ve eksen okları `assets/calibration/` içinde.

Açık sınırlar:

- Tripo produced 256 fragments. Blades were grouped geometrically into four rotor candidates and original UVs restored. Rotor/guard separation requires visual review before joint binding.

