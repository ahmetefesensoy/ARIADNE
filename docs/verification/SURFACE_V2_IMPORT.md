# BXW yüzey v2 — Unreal içe aktarma

15 Kasım 2026, 11:56 (+03:00). Gerçek içe aktarma ve kaydedilmiş haritanın
yeniden yükleme kontrolü geçti. Yeni harita
`/Game/EVAFixtures/BXW_EVA_SurfaceV2`; özgün EVA haritası korunur.

`data/engines/BXW/surface-v2-1m/manifest.json` içindeki 121 adet 1 m karo ve
4 m dış halka, toplam **15.317.568 üçgen** içerir. Kaynak OBJ özetleri,
boyutlar ve ENU→Unreal eksen/birim dönüşümü her karoda denetlendi.
Kaynak manifest SHA-256:
`6abbd353a238b7bda38867f6041a2ade54336a2dae88fc33f93bfd79e923acbc`.

Yeni dosyalar `/Game/DerivedSurfaceV2/Meshes` altındadır. Mevcut sahnenin
yalnız 17 eski arazi aktörü değiştirilir; 178 diğer aktör korunur. Yeni
harita 300 aktördür. Terrain query collision, Unreal insanı içindir;
robot fiziği ve kontrolü ROS/Gazebo'da kalır.

| Kontrol | Kaydedilmiş haritada DEM farkı |
|---|---:|
| P1 | 0,01965 m |
| P2 | 0,01114 m |
| P3 | 0,00538 m |

Üçü de 0,1 m sınırını geçti. Sonuçlar gerçek complex collision çizgi
sorgularıdır. Kaynak arazinin datum'u ve `map` pozu değiştirilmez.

Özgün OBJ'ler değiştirilmeden, Blender 5.2 ile ayrı FBX türevleri ve 3 km
bağlam atlasına UV üretildi. HiRISE renk mozaiği ve kaynak/kredi kayıtları
`surface-v1/imagery.json` altında korunur. Mevcut
`M_ScenarioSand_context` malzemesi kullanılır. Merkezdeki eski 1 km ops
atlası yerine 3 km bağlam atlası kullanılması, merkezde renk dokusu
örneklemesini yaklaşık 0,24 m/pikselden 0,73 m/piksele düşürür. Geometrik
örnekleme 2,75 km boyunca 1 m'dir. GPU görüntüsü, kare hızı ve nihai yakın
plan malzeme kalitesi bu kontrolde kabul edilmiş sayılmaz.

ASCII derleme önbelleğindeki EVA ve kum malzemesi, depodakilerden farklı
11:39 tarihli düzenlemeler içerir. İki sürüm de korundu; mevcut ana
malzemenin üzerine yazılmadı. Harita kopyası güncel önbellek sahnesinden
üretildi. Dosya özetleri `test-results/surface-v2-dependencies.json` içinde.

Betikler: `prepare_surface_v2_fbx.py`, `import_surface_v2.py`,
`verify_surface_v2_scene.py`. Kanıtlar:
`surface-v2-unreal-import.json`, `surface-v2-saved-scene.json` ve
`surface-v2-dependencies.json` (`test-results/`).
