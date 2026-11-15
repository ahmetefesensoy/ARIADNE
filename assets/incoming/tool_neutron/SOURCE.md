# tool_neutron — kaynak ve teslim kaydı

14 Kasım 2026 · Tripo · AI üretimi.

Bu dosya bir görsel varlık kaydıdır. Boyut, yerleşim ve görevdeki kullanım SCENARIO’dur; NASA ölçümü, flight CAD, sensör kalibrasyonu veya robot kontrol sistemi sayılmaz.

Gerçekte işlenen kaynak: `incoming\tool_neutron\source.glb`. Orijinal dosyalar korunmuştur.

Üretim/işleme Tripo API üzerinden yapıldı. [API koşulları](https://developers.tripo3d.ai/en/terms), [Tripo koşulları](https://www.tripo3d.ai/terms). Bu dosyalara CC0 lisansı verilmedi. Hesap abonelik türü bu paket tarafından doğrulanmaz.

- `d1f56ecd-0f00-4164-9f46-0aac237d08a3` · text_to_model · success · 20 kredi

Görevlerin tam istek parametreleri `asset.json → source_notice.tripo_tasks` içinde; süreli indirme URL’leri ve hesap sırları kaydedilmedi.

Prompt · `d1f56ecd-0f00-4164-9f46-0aac237d08a3`:

```text
One realistic compact Mars rover neutron sensor electronics box, a low rectangular robust white insulated instrument housing with slightly rounded edges, ribbed graphite side heat sink, two separate circular gold titanium electrical connectors recessed into one short end, small dark circular detector window on the broad front panel, four visible bolted corner mounting feet, no tall antenna. Clean coherent aerospace engineering, scientifically plausible packaging, muted white graphite and titanium finish, restrained dust, small red mechanical latches without writing. Complete isolated single scientific instrument, no vehicle, no ground, no stand, no pedestal, no scene, no wires on floor, no lettering, no labels, no logo. Realistic PBR materials.
```

Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, ayrı parça OBJ’leri, basit çarpışma proxy’leri ve önizlemeler. Gazebo `visual.sdf` yalnız statik görsel yükleme içindir; URDF/link/joint, inertia, ROS topic, uçuş ve navigasyon kontrolü içermez.

Ölçülen LOD0: 6,449 üçgen; 1 malzeme; 1 parça. Gazebo visual: 1,999 üçgen.
Blender 5.2.3 LTS; FBX binary 7400. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı. FBX/OBJ dönüşüm ayarları ve parça pivotları asset.json içinde.

Yerel yeniden içe aktarma: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü, materyal/normal bağlama ve robot kontrolü: **yapılmadı**. 1 m test küpü ve eksen okları `assets/calibration/` içinde.

Açık sınırlar:

- Tripo SCENARIO instrument appearance; not flight CAD, measured geometry, sensor optics or calibrated detection/illumination physics.

