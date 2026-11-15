# tool_libs — kaynak ve teslim kaydı

14 Kasım 2026 · Tripo · AI üretimi.

Bu dosya bir görsel varlık kaydıdır. Boyut, yerleşim ve görevdeki kullanım SCENARIO’dur; NASA ölçümü, flight CAD, sensör kalibrasyonu veya robot kontrol sistemi sayılmaz.

Gerçekte işlenen kaynak: `incoming\tool_libs\source.glb`. Orijinal dosyalar korunmuştur.

Üretim/işleme Tripo API üzerinden yapıldı. [API koşulları](https://developers.tripo3d.ai/en/terms), [Tripo koşulları](https://www.tripo3d.ai/terms). Bu dosyalara CC0 lisansı verilmedi. Hesap abonelik türü bu paket tarafından doğrulanmaz.

- `c6ce5d78-a4cb-4265-8e9a-9110cfeb6f50` · text_to_model · success · 20 kredi

Görevlerin tam istek parametreleri `asset.json → source_notice.tripo_tasks` içinde; süreli indirme URL’leri ve hesap sırları kaydedilmedi.

Prompt · `c6ce5d78-a4cb-4265-8e9a-9110cfeb6f50`:

```text
One realistic Mars rover remote LIBS optical instrument head, compact rectangular telescope housing with one large recessed circular optical aperture and a smaller adjacent camera aperture facing forward, black internal baffles inside a thick titanium lens collar, white multilayer thermal panels, graphite electronics enclosure at back, short rigid mounting flange underneath, secured rear electrical connector. Clean functional aerospace engineering and plausible panel seams. Muted white grey black metal palette, small red fasteners without symbols, no weapon appearance. Complete isolated single scientific instrument, no mast, no rover, no terrain, no pedestal, no lettering, no labels, no logos. Realistic PBR materials.
```

Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, ayrı parça OBJ’leri, basit çarpışma proxy’leri ve önizlemeler. Gazebo `visual.sdf` yalnız statik görsel yükleme içindir; URDF/link/joint, inertia, ROS topic, uçuş ve navigasyon kontrolü içermez.

Ölçülen LOD0: 10,639 üçgen; 1 malzeme; 1 parça. Gazebo visual: 3,000 üçgen.
Blender 5.2.3 LTS; FBX binary 7400. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı. FBX/OBJ dönüşüm ayarları ve parça pivotları asset.json içinde.

Yerel yeniden içe aktarma: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü, materyal/normal bağlama ve robot kontrolü: **yapılmadı**. 1 m test küpü ve eksen okları `assets/calibration/` içinde.

Açık sınırlar:

- Tripo SCENARIO instrument appearance; not flight CAD, measured geometry, sensor optics or calibrated detection/illumination physics.

