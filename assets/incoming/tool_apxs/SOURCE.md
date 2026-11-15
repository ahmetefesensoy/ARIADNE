# tool_apxs — kaynak ve teslim kaydı

14 Kasım 2026 · Tripo · AI üretimi.

Bu dosya bir görsel varlık kaydıdır. Boyut, yerleşim ve görevdeki kullanım SCENARIO’dur; NASA ölçümü, flight CAD, sensör kalibrasyonu veya robot kontrol sistemi sayılmaz.

Gerçekte işlenen kaynak: `incoming\tool_apxs\source.glb`. Orijinal dosyalar korunmuştur.

Üretim/işleme Tripo API üzerinden yapıldı. [API koşulları](https://developers.tripo3d.ai/en/terms), [Tripo koşulları](https://www.tripo3d.ai/terms). Bu dosyalara CC0 lisansı verilmedi. Hesap abonelik türü bu paket tarafından doğrulanmaz.

- `759649d6-e41f-4274-afbf-d93d718c8177` · text_to_model · success · 20 kredi

Görevlerin tam istek parametreleri `asset.json → source_notice.tripo_tasks` içinde; süreli indirme URL’leri ve hesap sırları kaydedilmedi.

Prompt · `759649d6-e41f-4274-afbf-d93d718c8177`:

```text
One realistic Mars rover contact-science sensor head inspired by APXS, compact short cylindrical metal instrument with a broad circular flat sensing window at the front, protective annular contact rim, small recessed round detector apertures arranged around the central window, bolted flange at the back for mounting on a robot wrist. White ceramic thermal sleeve, brushed titanium rings, dark graphite rear connector block, small secured cable connector. Functional restrained aerospace engineering, clear coherent manufactured geometry, no decorative spikes. Complete isolated single instrument, mounted axis horizontal, no arm, no rover, no ground, no pedestal, no words, no labels, no logos. Realistic PBR materials.
```

Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, ayrı parça OBJ’leri, basit çarpışma proxy’leri ve önizlemeler. Gazebo `visual.sdf` yalnız statik görsel yükleme içindir; URDF/link/joint, inertia, ROS topic, uçuş ve navigasyon kontrolü içermez.

Ölçülen LOD0: 10,896 üçgen; 1 malzeme; 1 parça. Gazebo visual: 1,999 üçgen.
Blender 5.2.3 LTS; FBX binary 7400. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı. FBX/OBJ dönüşüm ayarları ve parça pivotları asset.json içinde.

Yerel yeniden içe aktarma: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü, materyal/normal bağlama ve robot kontrolü: **yapılmadı**. 1 m test küpü ve eksen okları `assets/calibration/` içinde.

Açık sınırlar:

- Tripo SCENARIO instrument appearance; not flight CAD, measured geometry, sensor optics or calibrated detection/illumination physics.

