# tool_multispectral — kaynak ve teslim kaydı

14 Kasım 2026 · Tripo · AI üretimi.

Bu dosya bir görsel varlık kaydıdır. Boyut, yerleşim ve görevdeki kullanım SCENARIO’dur; NASA ölçümü, flight CAD, sensör kalibrasyonu veya robot kontrol sistemi sayılmaz.

Gerçekte işlenen kaynak: `incoming\tool_multispectral\source.glb`. Orijinal dosyalar korunmuştur.

Üretim/işleme Tripo API üzerinden yapıldı. [API koşulları](https://developers.tripo3d.ai/en/terms), [Tripo koşulları](https://www.tripo3d.ai/terms). Bu dosyalara CC0 lisansı verilmedi. Hesap abonelik türü bu paket tarafından doğrulanmaz.

- `1d1334b7-6e5f-4f38-b3ce-736803da0b83` · text_to_model · success · 20 kredi

Görevlerin tam istek parametreleri `asset.json → source_notice.tripo_tasks` içinde; süreli indirme URL’leri ve hesap sırları kaydedilmedi.

Prompt · `1d1334b7-6e5f-4f38-b3ce-736803da0b83`:

```text
One realistic compact Mars exploration multispectral camera head, sturdy rectangular white thermal-insulated optical housing with six small round glass lens apertures in a clean two by three array on the front, each aperture has a recessed dark baffle and a titanium ring. Subtle lens coating reflections, graphite rear electronics module, small bolted mounting plate underneath and a secured rear electrical connector. Plausible precision optical instrument, clean aerospace machining, white graphite titanium with tiny red fasteners, no bright lights. Complete isolated single camera, no gimbal, no mast, no drone, no rover, no tripod, no terrain, no base, no pedestal, no writing, no labels, no logos. Realistic PBR materials.
```

Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, ayrı parça OBJ’leri, basit çarpışma proxy’leri ve önizlemeler. Gazebo `visual.sdf` yalnız statik görsel yükleme içindir; URDF/link/joint, inertia, ROS topic, uçuş ve navigasyon kontrolü içermez.

Ölçülen LOD0: 10,757 üçgen; 1 malzeme; 1 parça. Gazebo visual: 2,999 üçgen.
Blender 5.2.3 LTS; FBX binary 7400. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı. FBX/OBJ dönüşüm ayarları ve parça pivotları asset.json içinde.

Yerel yeniden içe aktarma: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü, materyal/normal bağlama ve robot kontrolü: **yapılmadı**. 1 m test küpü ve eksen okları `assets/calibration/` içinde.

Açık sınırlar:

- Tripo SCENARIO instrument appearance; not flight CAD, measured geometry, sensor optics or calibrated detection/illumination physics.

