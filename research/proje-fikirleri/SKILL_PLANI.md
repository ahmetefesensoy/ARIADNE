# REDLINE için skill seçimi ve kullanım planı

14 Kasım 2026 · **17 dış kaynak skill kuruldu; projeye özel 1 skill yazıldı.**

Sıfırdan başlanacak başka depo/oturum için [aktarım listesi ve başlangıç paketi](../handoff/YENI_DEPO_AKTARIMI.md). Proje skill'i v1.1 artık v3 kılavuzu ve uygulama spesifikasyonuna yönlendirir.

Kurulum bu depoya özel `.agents/skills` altında. Mevcut kullanıcı skill'leri
değiştirilmedi. Kaynak commit'leri, lisanslar ve dosya hash'leri
[manifestte](../../.agents/skills-manifest.json). İlk kullanım çıktıları:
[UE bağlamı](../../.agents/ue-project-context.md),
[NASA notebook'u](../notebook/nasa-metadata-coverage.ipynb) ve
[uygulama kaydı](../notes/SKILL_ILK_UYGULAMA.md).

## Kurulanlar

| Alan | Skill | REDLINE'daki iş |
|---|---|---|
| Proje | `redline-space-apps` | Değişen görevler, NASA veri kökeni, Mars koordinatları ve ROS–Unreal sınırları |
| Council | `quorum` | Önemli alternatifler, mimari ve görev eleştirisi |
| Robotik | `ros2-engineering-skills` | rclpy/rclcpp, QoS, TF, URDF, Nav2, MoveIt, sensörler, Gazebo ve teşhis |
| UE envanteri | `ue-project-context` | Gerçek proje, modül, eklenti ve ayarlardan bağlam çıkarma |
| UE C++ | `ue-cpp-foundations` | Reflection, nesne yaşamı, pointer, delegate ve subsystem |
| UE derleme | `ue-module-build-system` | Build.cs, Target.cs, modül/eklenti ve derleme hataları |
| UE arayüzü | `ue-blueprint-cpp-interop` | C++ verisini ve işlemlerini Blueprint'e açma |
| Köprü | `ue-async-threading` | Ağ/sensör işi, game thread ve nesne yaşam süresi |
| Ekranlar | `ue-ui-umg-slate` | Habitat haritası, tablet, kamera, grafik ve kontroller |
| UE doğrulama | `ue-testing-debugging` | İlgili test, log, Unreal Insights ve performans teşhisi |
| Gezegen | `planetary-geologist` | Hedef/jeoloji bağlamı, PDS ürünleri ve yorum sınırları |
| GIS | `geomaster` | DEM, raster, CRS, grid/no-data hizalama ve türetilmiş harita |
| Fikir | `scientific-brainstorming` | Yeni görev/araştırma yönleri, varsayım ve sınanabilir öneri |
| Kanıt | `scientific-critical-thinking` | Ölçüm bağımsızlığı, karşılaştırma, karıştırıcı etken ve belirsizlik |
| Grafik | `scientific-visualization` | Kaynak, hata aralığı ve eksik veriyle bilim grafikleri |
| Analiz | `jupyter-notebook` | Tekrar çalıştırılabilir NASA ve algoritma deneyleri |
| GitHub | `gh-fix-ci` | Gerçekten başarısız GitHub Actions kontrolünün teşhis/düzeltmesi |
| İnceleme | `gh-address-comments` | İstenen PR yorumları ve ilgili değişiklikler |

Her işte hepsi açılmaz. Köprü işinde ROS + UE build/async/interop; sahada gezegen/GIS
ve notebook; görsel üretimde Blender skill'leri kullanılır. Yalnız ilgili referans
okunur. Ana kılavuz değiştirilebilir bir tasarım kaydıdır; yeni kullanıcı yönünü
engelleyen sabit kapsam değildir.

## LLM Council için Quorum

[Quorum](https://github.com/GTuritto/quorum), MIT lisanslı ve mevcut Codex ajan
araçlarına uyarlanmış bir Council seçeneği. Ayrı inference servisi/API anahtarı
gerektirmeyen yolu var.

- **Mini:** Tek oturumda Analyst/Skeptic/Pragmatist açıları; bağımsız model incelemesi değildir.
- **Full:** Kapasite uygunsa bağımsız adaylar, yeni değerlendirici ve ana oturumda sentez. Kapasite sınırında turlar kullanabilir.
- **Super:** Açıkça istenen, gerçekten desteklenen model/çaba ayarları; farklı roller farklı model kanıtı değildir.

```text
$quorum Full ROS–Unreal köprüsü alternatiflerini mevcut depoya göre incele.
$quorum Mini Bu bilim görevinin zayıf varsayımlarını ve düzeltmelerini değerlendir.
$redline-space-apps Bir sonraki görev için uygulanabilir deney ve teslim üret.
```

Otomatik hafıza `status` sonucu `enabled: false`; açılmadı. Genel hafıza, yeni
sağlayıcı hesabı, ücretli API veya arka plan servisi kurulmadı. Görüş birliği
doğruluk kanıtı sayılmaz. İncelenen diğer Council adaylarındaki sabit beş eşzamanlı
ajan, zorunlu uzun bekleme, ek CLI/API veya açık lisans eksikliği gibi uyum
sorunları nedeniyle Quorum seçildi; bu diğer seçenekler için genel kalite hükmü değildir.

## Mevcut 3D ve teslim skill'leri

Bu makinede zaten bulunanlar yeniden indirilmedi:

| İş | Kullanılacak mevcut skill'ler |
|---|---|
| Model/üretim | `blender-director`, `blender-modeler`, `environment-artist`, `vehicle-artist`, `hard-surface`, `prop-artist` |
| Tekrarlı sahne parçaları | `procedural-modeling`, `geometry-nodes`, `scene-assembly`, `set-dressing` |
| Görünüm | `materials`, `uv-workflow`, `texture-workflow`, `lighting`, `lookdev`, `rendering` |
| Hareket | `rigging`, `animation` |
| Unreal'a hazırlık | `asset-optimization`, `lod-pipeline`, `collision-proxy`, `unreal-export`, `qa-review` |
| Rapor/sunum | Mevcut belge, sunum, spreadsheet, bilgi hiyerarşisi ve yazım skill'leri |

Blender skill'inin varlığı MCP/editör bağlantısı kanıtı değildir. Meshy/Tripo
aboneliği, UE eklentisi veya başka bir kontrol servisi bu işlemde kurulmadı.

## Kaynaklar

| Kaynak | Commit başlangıcı | Seçim / lisans |
|---|---|---|
| [GTuritto/quorum](https://github.com/GTuritto/quorum) | `c6426dfdc552` | Council / MIT |
| [dbwls99706/ros2-engineering-skills](https://github.com/dbwls99706/ros2-engineering-skills) | `d569707db488` | ROS / Apache-2.0 |
| [quodsoler/unreal-engine-skills](https://github.com/quodsoler/unreal-engine-skills) | `f3742d7b6886` | 31 skill içinden ilgili 7 UE skill'i / MIT |
| [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | `2d2065fb4520` | GIS, grafik, eleştiri, fikir / MIT |
| [K-Dense-AI/scientific-agents](https://github.com/K-Dense-AI/scientific-agents) | `98c7fae46648` | Planetary Geologist / MIT |
| [openai/skills](https://github.com/openai/skills) | `49f948faa925` | Notebook, iki GitHub skill'i / Apache-2.0 |

Tam SHA/path kayıtları manifestte. Dış kaynak SKILL.md içerikleri değiştirilmedi;
lisanslar korundu, gerekli alt klasörlere üst kaynağın LICENSE/NOTICE dosyaları
eklendi. K-Dense içeriklerindeki atıf talepleri korunuyor; bilimsel çıktıya maddi
katkı olduğunda istenen güncel kaynak ayrıca doğrulanır.

ROS için `robium-ai/robium` ve dağıtıma özel rehberler de incelendi. Aynı işi yapan
birden fazla genel ROS skill'i kurulmadı. NASA-PDS'nin `pds-agent-skills` deposundaki
sürüm/güvenlik/idare otomasyonları PDS bilim verisi okuma ihtiyacını karşılamadığı
için seçilmedi. Hazır hackathon tanıtım şablonu yerine proje skill'ine güncel
challenge, veri kökeni, deney ve teslim kontrolü bağlandı.

## Bağımlılıklar ve uygulama sınırları

- ROS kaynaklarının bilgi dosyaları taşınabilir; runtime deneyi uygun WSL ROS ortamını ister. Jazzy yükseltilmedi; Nav2/MoveIt paketi veya Claude hook'u etkinleştirilmedi.
- UE kaynakları 5.8'e odaklanıyor. Yerel 5.8.4 yeniden okundu. Yazarın API doğrulaması bizim derleme sonucumuz değildir; uygulamada yerel header/build kontrol edilir.
- GeoMaster Dünya örnekleri de içerir. Mars'a WGS84/EPSG:4326 veya Dünya uydu bandı varsayılanları taşınmaz; PDS metadata'sı kullanılır.
- Planetary Geologist NASA tarafından yazılmış ürün okuyucu veya doğrulanmış uzman hizmeti değildir. Sayısal eşik, spektral tanı ve güncel standart iddiaları birincil kaynaktan doğrulanır.
- Notebook hazırlama ve ilk metadata kontrolü standart Python'la çalıştı. Jupyter kernel, Matplotlib, Rasterio/GeoPandas gibi ortamlar bu işlemde kurulmadı; gereken görevde ayrı ortam hazırlanır.
- Skill örnekleri görev yetkisini genişletmez; yeni harici hizmet, ücretli API, hesap işlemi veya yayınlama otomatik başlamaz.

## Sonraki işte kullanım

Önceki planla uyumlu iki paralel uygulama adayı var: bilim tarafında ürün/CRS ve
footprint QA'sını kapatmak; entegrasyonda mevcut deneme sahasında poz, zaman,
hedef/komut ve kopma davranışı için küçük ROS–Unreal bağlantısı kurmak. Kullanıcının
önceliği değişirse ilgili skill'ler ve teslim de değişir.

Depo kökünden kurulum bütünlüğünü yeniden kontrol etmek için:

```powershell
python -X utf8 .\tools\verify_skill_installation.py
```

Bu kontrol ağ veya dış skill kodu çalıştırmaz; kayıtlı hash, ad ve lisans varlığını
denetler. Teknik içerik ve runtime doğruluğunu kanıtlamaz. Bilinçli güncellemede
fark incelenir; yalnız kontrol yeşil olsun diye manifest yenilenmez.

Codex'in [resmî skill belgesi](https://learn.chatgpt.com/docs/build-skills)
repo içi `.agents/skills` keşfini açıklıyor. Sonraki mesajda kullanılabilirler;
listede görünmezse Codex'i yeniden yüklemek gerekebilir. İlk kullanım bu oturumda
ilgili dosyalar doğrudan okunarak yapıldı.
