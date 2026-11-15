# science_station — kaynak ve teslim kaydı

14 Kasım 2026 · Tripo · AI üretimi.

Bu dosya bir görsel varlık kaydıdır. Boyut, yerleşim ve görevdeki kullanım SCENARIO’dur; NASA ölçümü, flight CAD, sensör kalibrasyonu veya robot kontrol sistemi sayılmaz.

Gerçekte işlenen kaynak: `incoming\science_station\source.glb`. Orijinal dosyalar korunmuştur.

Üretim/işleme Tripo API üzerinden yapıldı. [API koşulları](https://developers.tripo3d.ai/en/terms), [Tripo koşulları](https://www.tripo3d.ai/terms). Bu dosyalara CC0 lisansı verilmedi. Hesap abonelik türü bu paket tarafından doğrulanmaz.

- `d22a9e35-8dc4-4f79-a9a6-a3b7108c931c` · text_to_model · success · 30 kredi
- `c6235dab-3741-4b3f-9dc5-822f724df7f2` · texture_model · success · 10 kredi

Görevlerin tam istek parametreleri `asset.json → source_notice.tripo_tasks` içinde; süreli indirme URL’leri ve hesap sırları kaydedilmedi.

Prompt · `d22a9e35-8dc4-4f79-a9a6-a3b7108c931c`:

```text
Compact deployable Mars environmental science station, one waist-high sensor box standing on three splayed folding tripod legs, white thermal insulation panels, graphite metal hinges, muted red identification bands without text, short separate upright communication antenna, small radiation detector and weather sensor on top, compact top solar panel. Realistic engineered NASA-inspired field equipment, robust and simple, complete assembled neutral pose, distinct sensor box and separate legs and antenna with visible joints. Single isolated object, no ground, no rocks, no platform, no people, no cables on ground, no letters, no logos.
```

Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, ayrı parça OBJ’leri, basit çarpışma proxy’leri ve önizlemeler. Gazebo `visual.sdf` yalnız statik görsel yükleme içindir; URDF/link/joint, inertia, ROS topic, uçuş ve navigasyon kontrolü içermez.

Ölçülen LOD0: 23,792 üçgen; 1 malzeme; 14 parça. Gazebo visual: 6,493 üçgen.
Blender 5.2.3 LTS; FBX binary 7400. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı. FBX/OBJ dönüşüm ayarları ve parça pivotları asset.json içinde.

Yerel yeniden içe aktarma: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü, materyal/normal bağlama ve robot kontrolü: **yapılmadı**. 1 m test küpü ve eksen okları `assets/calibration/` içinde.

Açık sınırlar:

- Four legs were generated; station is delivered in a fixed deployed pose. Folding limits are undefined.

