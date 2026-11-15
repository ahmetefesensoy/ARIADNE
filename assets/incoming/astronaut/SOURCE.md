# astronaut — kaynak ve teslim kaydı

14 Kasım 2026 · Tripo · AI üretimi.

Bu dosya bir görsel varlık kaydıdır. Boyut, yerleşim ve görevdeki kullanım SCENARIO’dur; NASA ölçümü, flight CAD, sensör kalibrasyonu veya robot kontrol sistemi sayılmaz.

Gerçekte işlenen kaynak: `incoming\astronaut\animations\tripo-out\redline-astronaut-idle-walk-0df6992f\model.glb`. Orijinal dosyalar korunmuştur.

Üretim/işleme Tripo API üzerinden yapıldı. [API koşulları](https://developers.tripo3d.ai/en/terms), [Tripo koşulları](https://www.tripo3d.ai/terms). Bu dosyalara CC0 lisansı verilmedi. Hesap abonelik türü bu paket tarafından doğrulanmaz.

- `7583fea2-05ef-4340-8cc9-5b5a756d3eb4` · text_to_model · success · 50 kredi · oturum öncesi
- `2ddc3f89-aa39-4433-8651-bd8ea06a15a5` · animate_prerigcheck · success · 0 kredi
- `f43b5416-7d9d-4f96-8e36-66a31d3f58ad` · animate_rig · success · 25 kredi
- `0df6992f-5e0f-4687-8a32-524cdb69ca6e` · animate_retarget · success · 20 kredi

Görevlerin tam istek parametreleri `asset.json → source_notice.tripo_tasks` içinde; süreli indirme URL’leri ve hesap sırları kaydedilmedi.

Prompt · `7583fea2-05ef-4340-8cc9-5b5a756d3eb4`:

```text
Photorealistic full-body adult human astronaut, 1.85m tall, believable anatomy and natural proportions. Neutral standing A-pose, arms slightly separated from torso, feet shoulder-width apart, both gloved hands visible with five fingers. Helmet with raised visor revealing a realistic human face: natural skin, subtle pores, clear eyes, eyelids, nose, lips and calm expression. Contemporary Mars EVA suit in off-white woven fabric with muted red accents, graphite flexible joints, reinforced knees and elbows, layered seams, stitching, fabric folds and realistic pressure-suit bulk. Detailed locking neck ring, metal wrist couplings, chest life-support controls, oxygen connectors, short secured hoses and compact backpack. Thick articulated gloves and boots with treaded soles. Restrained wear and fine reddish dust around boots. Realistic fabric, rubber, painted metal and skin PBR materials. Complete coherent geometry from every angle, isolated single character, no ground or scenery.
```

Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, ayrı parça OBJ’leri, basit çarpışma proxy’leri ve önizlemeler. Gazebo `visual.sdf` yalnız statik görsel yükleme içindir; URDF/link/joint, inertia, ROS topic, uçuş ve navigasyon kontrolü içermez.

Ölçülen LOD0: 95,000 üçgen; 1 malzeme; 1 parça. Gazebo visual: 7,999 üçgen.
Blender 5.2.3 LTS; FBX binary 7400. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı. FBX/OBJ dönüşüm ayarları ve parça pivotları asset.json içinde.

Yerel yeniden içe aktarma: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü, materyal/normal bağlama ve robot kontrolü: **yapılmadı**. 1 m test küpü ve eksen okları `assets/calibration/` içinde.

Revizyon (2026-11-14): Master faced -Y (front preview showed a profile); rotated +90Â° about Z to the documented +X forward / +Y left / +Z up convention used by every robot package. Ayrıntı `asset.json → revisions`.

