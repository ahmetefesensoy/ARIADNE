# tool_drill — kaynak ve teslim kaydı

14 Kasım 2026 · Tripo · AI üretimi.

Bu dosya bir görsel varlık kaydıdır. Boyut, yerleşim ve görevdeki kullanım SCENARIO’dur; NASA ölçümü, flight CAD, sensör kalibrasyonu veya robot kontrol sistemi sayılmaz.

Gerçekte işlenen kaynak: `incoming\tool_drill\source.glb`. Orijinal dosyalar korunmuştur.

Üretim/işleme Tripo API üzerinden yapıldı. [API koşulları](https://developers.tripo3d.ai/en/terms), [Tripo koşulları](https://www.tripo3d.ai/terms). Bu dosyalara CC0 lisansı verilmedi. Hesap abonelik türü bu paket tarafından doğrulanmaz.

- `a005625a-7eb4-4989-bc0e-50a30764a8aa` · text_to_model · success · 30 kredi
- `695a96a1-3728-4fc2-a536-c41fb26406fb` · texture_model · success · 10 kredi

Görevlerin tam istek parametreleri `asset.json → source_notice.tripo_tasks` içinde; süreli indirme URL’leri ve hesap sırları kaydedilmedi.

Prompt · `a005625a-7eb4-4989-bc0e-50a30764a8aa`:

```text
One realistic compact Mars rover coring drill end effector, upright scientific industrial instrument. Rectangular white thermal-covered motor housing attached to two parallel graphite feed rails, central silver sliding carriage and one clearly separate long spiral metal drill bit projecting straight downward, drill bit coaxial with motor, protective circular collar above bit. Rear bolted robot wrist mounting plate, secured short electrical connector. Separate editable solids for fixed motor housing, sliding carriage and drill bit, visibly distinct joint gaps, assembled neutral pose. Clean plausible aerospace engineering, graphite titanium white with small red accents, restrained wear. One complete isolated drill tool only, no robot arm, no rover, no ground, no sample rock, no pedestal, no text, no labels, no logo. Realistic PBR materials.
```

Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, ayrı parça OBJ’leri, basit çarpışma proxy’leri ve önizlemeler. Gazebo `visual.sdf` yalnız statik görsel yükleme içindir; URDF/link/joint, inertia, ROS topic, uçuş ve navigasyon kontrolü içermez.

Ölçülen LOD0: 11,103 üçgen; 1 malzeme; 20 parça. Gazebo visual: 2,987 üçgen.
Blender 5.2.3 LTS; FBX binary 7400. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı. FBX/OBJ dönüşüm ayarları ve parça pivotları asset.json içinde.

Yerel yeniden içe aktarma: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü, materyal/normal bağlama ve robot kontrolü: **yapılmadı**. 1 m test küpü ve eksen okları `assets/calibration/` içinde.

Açık sınırlar:

- Tripo SCENARIO instrument appearance; not flight CAD, measured geometry, sensor optics or calibrated detection/illumination physics.

