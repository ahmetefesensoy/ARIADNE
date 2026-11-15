# Karar kaydı

## D001 — Fikir aşamasından uygulamaya geçiş

14 Kasım 2026 · Kullanıcının açık yönlendirmesi.

- Fikir aşaması tamamlandı. Kodlamanın esası kökteki `proje.md`; destekleyici fikir/tasarım gelişimi `research/proje-fikirleri/` altında.
- `önceki deneme` güncel çalışma ağacından çıkarılır ve uygulamaya kaynak olarak geri alınmaz. Normal silme commit'i kullanılır; geçmiş yeniden yazılmaz.
- Üçüncü taraf skill/helper dosyaları ve lisansları korunur. Yalnız yerel `redline-space-apps` skill'inin belge bağlantıları değişti ve dosya hash'i manifestte güncellendi.
- T0'dan itibaren ROS Jazzy + Python 3.12 altyapısı, mesaj sözleşmeleri ve testler sıfırdan yazılır. Unreal 5.8.4 ilerleyen entegrasyon aşamasıdır.
- Ekran görünümü, sahne, malzeme ve 3D varlık tasarımları kullanıcıyla birlikte yapılacaktır. Bu aşamada model üretimi veya ücretli görsel API çağrısı yapılmaz.
- Fikir gelişimi SVG'si yalnız doküman şemasıdır; ürün arayüzü veya 3D tasarımı değildir.

## D002 — T0 sınırı

14 Kasım 2026 · Spek §18 ve mevcut makine envanteri.

T0 için `redline_core`/`redline_data` paket temelleri, eksen/birim ve saat sözleşme testleri, §5 ROS arayüzleri ve pytest/colcon CI kurulur. Veri işleme/rota algoritmaları T1/T2 kabul kapılarından önce tamamlanmış ilan edilmez. `CollectSample` gibi §5'te karşılığı olmayan adlar uydurma bir arayüzle doldurulmaz; belirsizlik günlüğe yazılır.

## D003 — Depo düzeninin tamamlanması

14 Kasım 2026 · `2c103eb` commit'indeki düzenleme.

Nihai plan `docs/proje.md`, ilerleme `journal/PROGRESS.md`, araştırma notları `research/notes/`, araştırma notebook'u `research/notebook/` konumuna taşındı. `AGENTS.md`, `.agents/` ve `optional-user-skills/` yerelde korunarak yayından çıkarıldı. Kod ve CI bu yerel asistan dosyalarına bağımlı değildir. Tarihsel envanterler eski yolları kaydetmeye devam eder; güncel dosya listesi olarak okunmazlar.

## D004 — ROS arayüzleri ve build kökeni

14 Kasım 2026 · İlk T0 derlemesi/testleri.

- Esas belge düzenleme sonrasında `docs/proje.md` yolundadır. Günlük `journal/PROGRESS.md` altındadır. Bu taşıma kararları uygulama sözleşmelerini değiştirmez.
- §5'teki 22 msg, 5 srv ve 11 action alan/tipleri uygulanır. Ortak aksiyon Result sabitleri §5.3 metnindeki SUCCEEDED/PARTIAL/CANCELED/FAILED/REJECTED = 0/1/2/3/4'tür. Şema değişikliği ayrı kararla izlenir.
- `FieldTile.nodata_byte` uint8, dokümanda PNG 8/16-bit olarak geçiyor. Şema aynen korunur; 16-bit nodata üretim/çözümleme kuralı sonraki veri/bridge aşamasından önce doğrulanacaktır.
- ROS derlemesi, Unicode Windows yolunun yerel rosidl configure hatası nedeniyle içerik hash'leri eşleşen, yeni ASCII Linux workspace'inde yapılır. Eski overlay veya derleme artığı test kanıtı sayılmaz.
- Yeni kod için açık lisans seçimi henüz yapılmadı; ROS manifestinde `LicenseRef-Project-Pending` ve geçersiz örnek maintainer adresi açık placeholder'dır. Üçüncü taraf lisansları bu karardan etkilenmez.

## D003 — Depo düzeni (hackathon yayını)

14 Kasım 2026 · Kullanıcının yönlendirmesi.

- Depo GitHub/hackathon için düzenlendi: kökte yalnız README, `docs/`, `journal/`, `research/` ve kod/altyapı klasörleri bulunur.
- Bütün fikir ve araştırma aşaması `research/` altına toplandı (`research-notes` → `research/notes`, `output/jupyter-notebook` → `research/notebook`, `docs/source-history` → `research/history/source-history`).
- Kullanıcının nihai uygulama belgesi `proje.md` → `docs/proje.md` (içeriği değişmedi). Kod içi `proje.md §…` atıfları bu belgeyi gösterir.
- Yapay zekâ asistanı dosyaları (`AGENTS.md`, `.agents/`, `optional-user-skills/`) yerelde kalır, `.gitignore` ile yayından çıkarıldı; CI'daki skill bütünlük adımı kaldırıldı. Üçüncü taraf skill kaynak/lisans kayıtları `research/proje-fikirleri/SKILL_PLANI.md` ve önceki commit geçmişinde durur.
- İlerleme günlüğü `journal/` altında tarih sıralı tutulur.

## D005 — Yerel T1 ve GitHub sınırı

14 Kasım 2026, 13:20 (+03:00) · Kullanıcının son yönlendirmesi.

GitHub, commit ve push kullanıcıya aittir. Ajan yerel uygulama, veri ve testlere devam eder; uzaktaki CI'yi takip etmez. Kullanıcının son paylaştığı spek `docs/proje.md` ile bağlantılar/satır sonları dışında eşleşir. Tasarım/3D ertelenir; Tripo kredisi veya internetten model bu adımda kullanılmaz.

## D006 — T1 ürün orijini, belirsizlik ve kabul sınırı

14 Kasım 2026, 13:20 (+03:00) · Kaynak metadata ve çalışan pencere deneyi.

- Gerçek Gale v3 tiled COG değil row-strip TIFF. Pencere okuması kaynak blok bütçesiyle sınırlandırılır. PixelIsPoint için GDAL/Rasterio geotransformu kullanılır.
- ENU, spek §4.2'deki yerel affine yaklaşımdır; geodetik topocentric dönüşüm değildir. Yerel grid CRS'siz engineering metreleri taşır; zorunlu sidecar source Mars WKT + E0/N0/H0 + ölçek/transform/hash saklar. Başka tüketiciye yalnız TIFF gönderilmez.
- Bu koşuda H0=0 açık SCENARIO ofsetidir. Sayısal yükseklikler kaynak referansındadır; çözülemeyen Gale düşey datumunun doğrulandığı iddia edilmez.
- 2/5 m tabanlı eğim, 1 m local DEM'den hesaplanır. 4 m grid bu tabanları desteklemez. İkinci kayıtlı DTM olmadan sigma rasterı uydurulmaz. Metre DTM farkı, derece slope_sigma'nın yerine geçmez.
- Üç nokta QA kaynak→local sayısal aktarımı doğrular. Gerçek feature, ikinci DTM veya Unreal hizalaması için ayrı kanıt gerekir. T1 kalan kontrolleri bitmeden tamamlandı yazılmaz.
- `data/stac/BXW/run_manifest.json` portable hash/metadata kaydıdır; STAC Collection değildir. Mars sınırları Dünya WGS84 gibi sunulmadan Collection/Item sözleşmesi çözülecek.

## D007 — T1 kabulü ve sonraki tüketici sözleşmesi

14 Kasım 2026, 13:44 (+03:00).

- Gale ürün-özel FGDC `MOLA/Meters` beyanı doğrulandı; belirli areoid sürümü uydurulmaz. Kaynak kanıtlarındaki `archive_status` dağıtım rolüdür; uygulama ürün/crop/katman `Provenance.status` spekteki **DERIVED** olarak kalır.
- İki DTM aynı yerel grid'e taşınır, sınırlı yatay kayıt ve medyan düşey ofsetle karşılaştırılır. Gerçek çift için ayrı tarama sonrasında 80 m aralık gerekçelendirildi; genel varsayılan 20 m. Düz/tek yönlü arazi, yetersiz destek, sınır optimumu, yakınsamama ve holdout kötüleşmesi reddedilir.
- `slope_sigma.tif` = `abs(slope5m(primary)-slope5m(aligned_reference))`, **derece**, ampirik uyuşmazlık proxy'si. Bağımsız 1σ gibi sunulmaz; √2 varsayımı uygulanmaz. T2 eksik kenar σ'sını sıfır sayamaz. İstatistik kalibrasyonu T12'de yeniden değerlendirilir.
- STAC Mars hedefi SSYS ile açık; Item core geometry null ve core bbox yok. Source WKT native Projection'da, local grid mapping ayrı kaydedilir. Yerel proj:wkt2 null kalır. Collection resmi SSYS örneğinin muhafazakâr bütün-gövde zarfını kullanır; bu ayak izi değildir. Proposal'ın core WGS84 metnini açıkça değiştirmediği sınırı kaydedilir; Dünya istemcisinde Dünya verisi gibi indekslenemez.
- `datetime` türevin gerçek işleme zamanıdır; bilinmeyen acquisition null. Kaynak hakları katalogla yeniden lisanslanmaz.
- T1 §18 zincirinin yerel mühendislik kabulüdür; §6.2'nin diğer yetenekleri, Unreal/Gazebo import, 3D ve görev kabulü buna dahil değildir.

## D008 — T2 çekirdek modeli ve BXW ilk margin haritası

14 Kasım 2026 · Claude Code ile T2 uygulaması. Kullanıcıyla ayrıca karara bağlanması gereken maddeler **[karar bekliyor]** işaretlidir.

- **Izgara:** `map` çerçevesinde orijin hücre (0,0)'ın güney-batı köşesi, `[iy, ix]` satırı kuzeye artar (OccupancyGrid/CellDelta ile aynı). T1'in kuzey-yukarı rasterları `north_up_to_grid` ile çevrilir.
- **4 m planlama katmanları:** `z` = T1 `dem_plan_4m`; eğim = 1 m `slope_5m`'in 4×4 blok ortalaması; σ = 1 m `slope_sigma` blok ortalaması (blokta tek eksik değer varsa hücre eksik); duvar eğimi = 1 m `slope_2m` blok maksimumu; rölyef = blok içi en küçük kareler düzlemi çıkarıldıktan sonra 1 m DEM artığının aralığı (düzgün eğim duvar sayılmaz).
- **σ (D007 ile uyumlu):** T1 ampirik eğim uyuşmazlığı vekili, `|μ_s| + 1,645·σ_s > 25°` kuralında σ_s olarak kullanılır. Bağımsız 1σ değildir, bu yüzden kural muhafazakâr çalışır. Eksik σ asla sıfır sayılmaz: çekirdek açık bir yedek değer ister; BXW haritasında bu değer geçerli σ'ların 95. yüzdeliğidir (12,80°). BXW'de σ=0 alındığında yasaklı hücre %17,3, vekil σ ile %38,3. **[karar bekliyor: vekilin ölçeklenmesi veya kalibrasyonu, T12 ile birlikte]**
- **Kenar modeli:** 16 komşuluk. Kenar maliyeti geçtiği hücrelere uzunlukla bölünür: düz/diagonal ½+½, knight adımı dört hücreye ¼. Knight adımı yasaklı ara hücrenin üstünden atlayamaz. Diagonal adım yanındaki iki hücreden biri yasaklıysa yapılamaz (katı köşe kuralı, spekte yok, güvenlik için seçildi). Uç noktalardan hesaplanan yönlü eğim de `atan|S| + z·σ > s_max` ise kenar silinir. Tobler hızı yatay mesafeye uygulanır (GIS kullanımı). σ_t tek yönlü sonlu farkla hesaplanır (Tobler kırığında merkezi fark sıfıra düşerdi). Kenar içindeki hücre σ'ları korele toplanır, kenarlar arasında varyanslar toplanır.
- **Katı köşe kuralının etkisi:** BXW'de habitat (0,0)'da yalnızca 3 hücrelik bir cebe düştü. Haritada senaryo habitatı, kenar kurallarına göre en büyük yürünebilir bileşenin (`walkable_components`) istenen noktaya en yakın hücresine konur; BXW'de 19 m kaydı. Bu bileşen ızgaranın %27'si. **[karar bekliyor: köşe kuralı katı mı kalsın, gerçek habitat konumu nerede]**
- **θ ölçeklemesi:** Spek "doğrusal" diyor; giysi gücü ve batarya taban yükü θ ile ölçeklenmediği için sarf θ'ya göre afindir. Dönüş alanı (süre T, kg başına yürüme enerjisi F) taşır; `E = θ·(ayakta·T + (W+L)·F) + ΔM_giysi·T` her kişi ve θ için yeniden Dijkstra gerektirmeden kesindir.
- **Risk:** `W_ε = μ + z·sqrt(Σσ² + (σ_θ μ)²)`; sarflar aynı `W_ε/μ` çarpanıyla ölçeklenir. CO₂ = RQ·(M_CO2/M_O2)·O₂ (molar kütle; sıcaklık/basınç seçimi gerekmez).
- **Pay:** Ulaşılamayan hücre `NaN` ve `LIM_NONE = 255` (MarginField sabiti değildir, tüketiciler "erişilemez" saymalıdır). SEP ihlali `-inf` ve `LIM_SHELTER`. Sayısal toleransta (göreli 1e-9) eşit tükenen sarflarda en düşük LIM kodu seçilir.
- **Çizgi poligonları:** `skimage.measure.find_contours`, alan dolgu değeriyle çevrelenerek kapalı halkalar. Harita çerçevesinde dış halkalar saat yönü tersine, delikler saat yönündedir (RedLine.msg delik ayrımı taşımadığından tüketici yönelimi kullanmalıdır).
- **PET:** İstasyon işi Pandolf V=0 artı giysi maliyetiyle modellenir; dönüş kararı PET = varış PET + varıştaki pay. Gün ışığı PET'e henüz girmedi (T6 SPICE ortamı gerekli).
- **SEP:** Arka plan = en son okumadan önceki 6 saatin medyanı. Alarm varken sığınak kuralı ihlal edilmiyorsa önem derecesi WARNING (seçim); ihlalde EMERGENCY + ReturnToShelter önerisi (spek).
- **Kaya λ:** Spekte değer yok; `rock_detour_s: null`. Kaya katmanı λ seçilmeden kullanılamaz.
- **Senaryo parametreleri:** `config/crew.yaml`, `config/suit.yaml` SCENARIO etiketli; bilinmeyen anahtar reddedilir. BXW için η = 1,1 (toprak) varsayımı.
- **Bağımlılıklar:** numpy 1.26.4 sabiti korunarak scipy, numba, scikit-image, hypothesis, networkx `scripts/requirements-core.txt` içinde sabitlendi; `bootstrap.sh` bunları yalnız wheel olarak kurar.

## D009 — T5 ROS ipliği: topic'ler, karo/çizgi biçimi, gözlem sözleşmesi, çalışma zamanı

14 Kasım 2026, 17:10 (+03:00) · Claude Code ile T5'in ROS tarafı. Kullanıcıyla ayrıca karara bağlanması gerekenler **[karar bekliyor]** işaretlidir.

- **Adlar (spekte yok):** `/redline/margin/<crew_id>` (MarginField), `/redline/redline` (RedLine), `/redline/tiles/margin_min` ve `/redline/tiles/margin_min_<crew_id>` (FieldTile), `/redline/evidence` (EvidenceRecord), `/redline/query_cell` (QueryCell). Spekteki `/redline/cells/delta`, `/crew/<id>/pose`, `/crew/<id>/state`, `/redline/mission/clock` aynen kullanılır. QoS §4.4: harita/plan reliable + transient_local depth 1; olay reliable depth 50; durum reliable depth 10; poz best-effort depth 5 (rosbridge'in reliable yayıncısıyla da uyumlu).
- **Görev saati:** `/redline/mission/clock` = `rosgraph_msgs/msg/Clock`, değer EVA başından PET saniyesi (T4 UE aboneliği ve mock zaten bu tipi kullanıyordu). `sim_clock` host monotonic saatiyle ve ölçekle çalışır, `time_scale` çalışırken değiştirilebilir; Gazebo `/clock`'u okumaz ve sürmez. SEEK T6 `scenario_player`'ındır.
- **FieldTile:** PNG north-up (satır 0 = kuzey kenarı); `origin` diğer ızgara mesajlarındaki gibi hücre (0, 0)'ın güneybatı köşesi. `değer = kod·scale + offset`; `nodata_byte` yalnız kod aralığının ucunda olabilir (0; 8-bit'te 255 de olur). 16-bit karoda nodata, `nodata_byte`'ın sıfırla genişletilmiş değeridir (D004'teki açık kapanır). NaN → nodata; ±inf ve aralık dışı değerler uca kırpılır; scale/offset kuantalamadan önce float32'ye yuvarlanır. Pay karosu 8-bit, [−60, 300] dk (≈1,42 dk/kod): BXW'de 51 KB. Tam aralık 16-bit aynı alanda 330–760 KB çıkıp §17'deki 300 KB bütçesini aşıyordu. Kesin dakika `RedLine.margin_now_min` ve QueryCell'den okunur; karo renk katmanıdır.
- **MarginField:** float dakika, ızgara sırasıyla (satır 0 = güney, satır-öncelikli); ham alan yalnız ROS içinde kalır (§13.2).
- **RedLine gösterim geometrisi:** `min(EV1, EV2)` alanının konturları; Douglas-Peucker toleransı 4 m (bir hücre), 0,01 km²'den küçük kapalı delikler halkaya dönüştürülmez (T2 figür kuralı; o hücreler karoda ve MarginField'da görünür kalır). Köşe z'si planlama DEM'inin map z'sidir. Dış halka CCW, delik CW (D008). `margin_now_min` NaN ise rosbridge `null` gönderir; konumu olmayan, ızgara dışında veya erişilemez hücrede duran mürettebat en kötü sayılır. `limiting_consumable = 255` = yok (D008 LIM_NONE).
- **EvidenceRecord → hücre (spekte yok):** `summary_json.cell_observation` v1 (`schema = redline.cell_observation.v1`, `state` DETECTED | NOT_DETECTED_LIMITED, `radius_m`, isteğe bağlı `rock_density_per_m2`); frame `map` zorunlu. Ayak izi: merkezi yarıçap içindeki hücreler + konumu içeren hücre. Bilgi azalmaz (DETECTED > LIMITED > UNOBSERVED); aynı `evidence_id` ikinci kez uygulanmaz; gözlemsiz kayıt hiçbir şeyi değiştirmez. Hücrenin `provenance_status`'ü `state` alanının kaynağıdır (gözleme kadar DERIVED). **[T7'de gözden geçir: engel/kapalı koridor bulgusunun bu sözleşmeye girişi]**
- **Delta hizalaması:** `walkback_field`, CellDelta'yı yalnız site, çözünürlük ve orijin planlama ızgarasıyla tam eşitse kabul eder; bbox örtüşmesi hizalama sayılmaz. Delta, sonraki tick'te yeniden Dijkstra'yı tetikler (§7.5); arada yalnız dizi çıkarması yapılır.
- **Planlama ızgarası:** `scripts/export_planning_grid.py`, T1 kabul manifest hash'lerini doğrulayıp D008 katmanlarını `data/derived/BXW/planning/bxw_planning_4m.{npz,json}` olarak yazar (float32, DERIVED, üzerine yazılmaz). Düğümler GDAL'sız yükler; npz SHA-256'sı yan dosyayla tutmazsa reddedilir. T2 haritası bu dosyayla birebir tekrarlandı (habitat hücresi, yasak oranı, güvenli oran).
- **EV1 sarfları (`ev_sim`, Unreal pozu):** ilk pozda (egress) SCENARIO başlangıç durumuyla başlar ve yalnız PET üzerinden entegre edilir; hız/eğim 2 s'lik poz penceresinden, güç §7.2'den gelir. Yürüme-koşu sınırının üstü kırpılır; 20 m'den büyük poz sıçraması pencereyi sıfırlar; PET geri giderse tüketim geri alınmaz. Kalp hızı, giysi basıncı ve ppCO₂ T9'a kadar NaN.
- **EVA başlangıcı (`config/eva.yaml`, SCENARIO):** spek giysi kapasitesi vermiyor. Her sarf = rezerv + 240 dk nominal düz yürüyüş tüketimi (T2 kuralı); rezerv yalnız FR-01 O₂ 0,1 kg. Bu yüzden O₂/CO₂/su başlangıçta eşit dakikadır: yürürken O₂, dururken batarya (sabit 60 W taban) sınırlar. **[karar bekliyor: gerçek giysi kapasiteleri ve rezervler]** Habitat D008 kuralıyla (18, −6) m'de **[karar bekliyor, D008]**.
- **Eşitlik toleransı:** `redline.TIE_REL_TOL` 1e-9 → 1e-5 (D008'i değiştirir). Canlı girdiler float32 Consumables alanlarıyla geldiğinden eşit sarflar aksi halde tick'ten tick'e O₂/SU arasında rastgele değişiyordu (düğüm testinde gözlendi). 60 dk payda 1e-5 = 36 ms.
- **ROS çalışma zamanı:** düğümler `redline_core`'u (numba, scipy, scikit-image) import eder; sistem Python'unda bunlar yok. Launch dosyası düğümleri `prefix=<REDLINE venv python>` ile başlatır (venv numpy'ı sistemle aynı, 1.26.4). Düğüm testleri `ament_add_pytest_test(PYTHON_EXECUTABLE <venv>)` ile koşar; CMake yapılandırmasında `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` gerekir, yoksa venv'de olmayan `lark` yüzünden ament pytest'i bulamayıp testi **sessizce atlıyordu**; artık bu durumda CMake hata verir. T5 testleri ayrı ROS_DOMAIN_ID (81–85) ve LOCALHOST keşfi kullanır; BXW koşusu domain 86 / port 9190 ile T3/T4 grafiğinden (77 / 9090) ayrı tutulur.

## D010 — T2 model kararları: σ, giysi maliyeti, giysi kapasitesi, habitat, kaya λ, gösterim geometrisi

14 Kasım 2026, 21:00 (+03:00) · Claude Code. Kullanıcı D008/D009'daki **[karar bekliyor]** maddelerini "en kolay değil, en iyi sonucu verecek şekilde, kestirme yapmadan" seçme yetkisini verdi. Her seçim aşağıdaki kanıta dayanır; D008'in ilgili maddelerini değiştirir.

- **Eğim σ — iki işlemenin topluluğu.** Gale DEM v3'ün FGDC soyağacı, BXW'deki HiRISE DTM'si DTEEC_019698_1750_019988_1750_U01 ile aynı stereo çifti (ESP_019698/ESP_019988, 'T3') listeliyor; iki ürün bağımsız ölçüm değil, aynı görüntülerin iki ayrı işlenmesi. T1 hizalı çiftinde 5 m eğim farkı sıfır ortalamalı (+0,01°), RMS 7°, ≈4 m'de dekorele; pürüzlülük oranı medyanı 1,01 (düzleştirme sapması yok). Bu yüzden: planlama eğimi μ = iki ürünün hücre ortalamalarının ortalaması; σ² = RMS₂₀ₘ(D)²/4 + σ_EP², yalnız birincil varsa RMS²/2 + σ_EP². D = hücre ölçeğinde işaretli fark; RMS 5×5 hücre (20 m) penceresinde. Ortak stereo hatası farkta görünmediği için Kirk ve ark. (2008) beklenen hassasiyeti eklenir: EP = 0,2 px · 0,291 m / (tan 24,1° + tan 14,7°) = 0,082 m. Görüntüler nadirin karşı taraflarında: faz 35,5° ≈ i − e, 68,7° = i + e. Buradan σ_EP = atan(√2·EP/5 m) = 1,33°. Referans dışındaki kenar bandı en yakın yerel RMS'i alır (≤ 40 m); σ hiçbir zaman sıfır sayılmaz. Sonuç: BXW yasak oranı %38,9 → **%28,9** (pencere 12/20/36 m'de 28,8–28,9). Eşik değiştirilmedi. Ürün: `bxw_planning_4m_v2.npz` (`bf2a5f1a…`), yapılandırma `config/terrain_uncertainty.yaml`.
- **Giysi ağırlık-dışı maliyeti hızla orantılı.** D008'deki 18,8 ml/kg/dk, EWT raporunun (NASA/TP-2009-214796, Tablo 5) 3/8 g "diğer etkenler" orta değeriydi. Bu değer 1,245–1,515 m/s'lik hızlı yürüyüşte ölçülmüş ve hızla keskin artıyor (14,9 / 18,8 / 21,6). Model onu her hıza, ayakta durmaya bile, sabit ekliyordu (EV1 ayakta 708 W). Yeni terim: ΔVO₂ = c·v, c = 13,4 ml/kg/dk per m/s (orijinden geçen en küçük kareler; artıklar < 2 ml/kg/dk), yani metre başına sabit maliyet. Dijkstra artık yol mesafesini de taşıyor (`distance_m`). Giysi enerjisi = 335·c·W·D/1000. Ölçülen aralığın (≥ 1,245 m/s) altı dış değerleme. Sonuç (EV1): ayakta 708 → **236 W**, nominal yürüyüş (0,60 m/s) 756 → **486 W**.
- **İstasyon işi.** Ayakta güç + görev artışı 8,0 ml/kg/dk. Kaynaklar: EWT 1/6 g'de giysi maliyeti tüm hızlarda ≈ 8; IST yük taşıma görevlerinde 7,1–10,0 (NASA/TP-2010-216125). Bu ay değeri Mars'ta muhtemelen düşük kalır. EV1 için 437 W. PET'te görev artışı yalnız hizmet süresine uygulanır.
- **Giysi kapasitesi — tasarım noktası.** Her sarf, rezerv + 8 sa × 351,7 W tasarım tüketimi taşır, aynı dönüşümlerle. Kaynaklar: 8 sa = Apollo 15–17 uzatılmış PLSS ve xEMU hedefi (ICES-2025-61); 351,7 W = Apollo PLSS tasarım ortalaması 1200 Btu/sa (NTRS 19720019460). Rezerv = max(taban, 30 dk tasarım tüketimi); 30 dk Apollo OPS acil O₂'dir ve FR-01'in 0,1 kg O₂ tabanı korunur. Mars nominal yürüyüşünde dayanıklılık **5,8 sa** (O₂/CO₂/su birlikte), batarya 7,4 sa. Bu, Mars yürüyüşünün Apollo tasarım noktasından pahalı olmasının dürüst sonucudur. Eski "rezerv + 240 dk nominal" esası (`nominal_minutes`) testler ve T2 karşılaştırması için kalır.
- **Habitat.** `scripts/select_habitat.py`: 20×20 m zemin, her hücrede |μ| + 1,645σ ≤ 15° ve 200 m düzlemde ≤ 5° (MSL Engineering User Guide v2 iniş limitleri); en büyük yürünebilir bileşende, bilim merkezine (0,0) ≤ 600 m, 12 m kafes. Amaç: risk düzeltmeli dönüşü ≤ 60 dk olan alanı en büyütmek; eşitlikte merkeze en yakın. 194 aday içinden seçilen (290, −454) m; erişim 2,16 km², ilk 6 aday %0,6 içinde. Kayıt `habitat_selection_v1.json`, `config/eva.yaml` placement `fixed`. Habitatın bileşeni 348 409 hücre (önce 151 401); erişilebilir oran %26,9 → %61,9.
- **Köşe kuralı.** Katı kalır (D008): çapraz adım yasak hücrenin köşesine değer. Habitat sorunu kuralı gevşeterek değil, ilkeli yer seçimiyle çözüldü.
- **Kaya λ.** λ = (π−2)/2 · (D̄ + w) / v_ref = 1,45 s. Bir kayanın etrafından dolanmanın ek yolu bu formülle verilir. D̄ = D* + 1/q(k=0,3) = 0,935 m (üstel boyut dağılımında ≥ D* kayaların ortalama çapı, üst k), w = 0,6 m, v_ref = 0,7·v(0) = 0,603 m/s. Kaya katmanı henüz yok; değer T7 gözlemleri kaya yoğunluğu yazınca kullanılır.
- **Gösterim geometrisi.** İki seviye birlikte en çok 3000 köşe; aşılırsa tolerans 4 m'den 32 m'ye kadar ikiye katlanır. Köşeler 1/16 m'ye yuvarlanır (float32'de tam, rosbridge JSON'unda kısa). BXW koşusunda RedLine çerçevesi en çok 317 KB → **111 KB**. MarginField ve karo hücre ayrıntısını tutar.
- **Etki (BXW, aynı 40 dk anlık görüntü, T2 ile karşılaştırılabilir):** güvenli oran 0,048 → 0,138; abort bölgesi 0,47 → 1,32 km². 4 sa nominal yürüyüş sonrası habitatta pay 107 dk. Harita: `data/derived/BXW/margin-v2-20261114T174827Z/` (PNG `cd40d089…`).
- **Açık sınırlar:** Mars giysi verisi tek bir analog çalışmadan (6 erkek astronot, MKIII, POGO). Hız modeli Tobler×Froude olarak kaldı; EWT'de Mars yürüme-koşu geçişi Froude tahmininden hızlı (1,54–1,74 m/s), yani hızlar muhtemelen temkinli. σ kalibrasyonu yer gerçeğiyle (PLACES eğimi; V2 sızıntısını önlemek için sol < 4533) T12'de yapılmalı.

## D011 — Plan çekirdeği: bilim değeri, orienteering, hedefler, VOI, planner_server

14 Kasım 2026, 22:30 (+03:00) · Claude Code. §7.9–7.11 ve §8.4 `planner_server` uygulandı. §18 tablosunda planner_server bir T satırına atanmamıştı; kılavuz Evre 1'deki "sistem ilk EVA planını üretir" gereği için eklendi.

- **Bilim değeri (`science_value.py`, `config/science_BXW.yaml`, SCENARIO):** soru kılavuz §3'ten alındı: doğu kenarındaki sırt-kil / çukur-karbonat deseni batıda sürüyor mu? Hipotezler H1 sürüyor, H2 yok, H3 karışık; önseller eşit. İstasyon sınıfı (sırt/çukur) imzası görülür/görülmez ikili sonuç verir. p(görülür|H) = 0,85 / 0,15 / 0,5 bir duyarlılık/yanlış-pozitif varsayımıdır **[kullanıcı ve T8 verisiyle gözden geçir]**. Rota değeri, istasyon kümesinin **tam ortak bilgi kazancı**dır (bit; ≤ 14 istasyonda sonuçlar tek tek sayılır). Böylece aynı sınıftan ikinci istasyon azalan getiri sağlar; testte bağımsız karşılıklı bilgi hesabıyla eşitliği kontrol edildi.
- **Orienteering (`orienteering.py`):** rota habitat → istasyonlar → habitat. Geçerlilik: PET çizelgesi her istasyonda R0 − C_ε − W_ε ≥ R_rez, pencere içi varış (erken varışta ayakta bekleme) ve EVA (dönüş dahil) ≤ azami süre. SCIENCE en çok değer; SAFE en geniş en dar ayrılış payı; FAST en kısa süre. SAFE/FAST için değer tabanı 0,7 × SCIENCE değeridir. Sezgisel: değer/ek süre oranıyla açgözlü ekleme + yerel arama (ekle, çıkar, en iyi yere yeniden yerleştirerek takas, taşı, 2-opt). Tam referans: ≤ 12 adayda tek bir genel Held–Karp tablosu her alt kümenin en kısa sırasını verir; boşluk raporlanır. Planlayıcı yalnız habitat + aday hücrelerinden oluşan sıkıştırılmış alanda çalışır; bacaklar kaynak başına tek ileri Dijkstra'dır.
- **Hedefler (`targets.py`, `scripts/derive_targets.py`):** sırt/çukur = 1 m DEM'de topografik konum indeksi (5–25 m halka), 4 m'ye ortalanır. Uygunluk: yürünebilir, |μ|+1,645σ ≤ 15°, risk düzeltmeli dönüş ≤ 120 dk, habitattan ≥ 50 m; sınıf başına 6, aralarında ≥ 100 m. BXW'de 12 hedef bulundu (sırt TPI +4,4…+5,7 m, çukur −2,8…−3,7 m). Kayıt `targets_v1.json` planlama ızgarası hash'ine bağlı; planner_server farklı ızgaradan türetilmiş hedefleri reddeder.
- **BXW sonucu (8 sa tasarım, en çok 6 sa):** SCIENCE 4 istasyon 0,692 bit, 229 dk, en dar pay 63 dk. SAFE ve FAST aynı 3 istasyon: 0,581 bit, 165 dk, pay 154 dk. Üç hedefte de tam çözüme göre boşluk 0. İlk sürümde FAST boşluğu %5,8'di; takasa yeniden yerleştirme eklenince kapandı. Süre ≈ 9,5 s, bunun 7 s'si bacak Dijkstra'ları.
- **VOI (`voi.py`):** adaylar planlı yol (gidiş + her istasyonun dönüşü) ±50 m koridorunda, 12 m kafeste, 6 m ayak izinde UNOBSERVED/LIMITED hücreler. Açık olasılığı p = exp(−N·w·L), N = Golombek N(≥D*); açıkta hücreler DETECTED olur, engelde geçilemez. Etkilenen yürüyüşler 200 m pencere içinde pencereye giriş/çıkış noktaları arasında yeniden yönlendirilir. Yürüyüş tamamlanamıyorsa erişilemeyen istasyonu düşüren varyant kullanılır. VOI = Σ P(o)·m(o) − m(şimdi); skor = max(VOI, 0) / robot maliyeti (mesafe/hız + inceleme süresi). BXW'de aday başına medyan 23 ms, p95 29 ms (hedef ≤ 50 ms).
- **planner_server:** `/redline/plan_eva` (PlanEva) üç rotayı ve tam referansları hesaplar, isteneni döndürür. `/redline/plan` (EVAPlan) ve `/redline/decisions` (DecisionRecord) yayımlanır; karar kaydında alternatifler, seçilmeyen hedefler, değer tabanı, boşluklar ve ızgara hash'i bulunur. Birden çok astronotta rota, nominal metabolik gücü en yüksek olana göre planlanır (giysi herkes için aynı tasarım noktasında). Açık uçlu istasyon penceresi plan ufkuyla kapatılır (rosbridge'e inf gitmez).

## D012 — T6 SEP hattı: RAD verisi, senaryo, görev durumu, kurallar, SEP modu

14 Kasım 2026, 21:50 (+03:00) · Claude Code.

- **RAD verisi:** PDS PPI `MSL-M-RAD-3-RDR-V1.0` sol 4189–4191 (`RAD_RDR_2024_1{39,40,41}_*_V00`). Ayrıştırıcı `redline_data/rad.py` (yeni modül; mevcut `redline_data` dosyalarına dokunulmadı). Doz blokları gözlemlere NN indeksiyle eşlenir; değer basamaklı tutulur; ARCHIVE. Çıktı hash'li CSV + JSON yan dosyasıdır, parquet değil: tablo sol başına ≈129 satır ve venv'de pyarrow yok; spek §6.2'den bilinçli sapma. `scripts/fetch_rad.py` spek §6.3'teki bütün [D] değerlerini gerçek dosyada doğruladı: gözlem 76–88 E serisi ve saatleri, E tepe 351,42427 @ 06:15:19, 6 sa medyan arka planla (5,60) ilk %25 alarmı gözlem 78 @ 05:21:50 (`docs/verification/T6_RAD.json`). **Fark:** V00 dosyasında 258 gözlem / 129 doz bloğu var; spek 186 / 93 diyor. Değerler aynı, dosya 2024-310 tarihli ve daha uzun bir aralığı kapsıyor.
- **Senaryo ve görev saati:** `config/scenarios/S1_SEP_4190.yaml` EVA'yı tarihsel 03:30 UTC'de başlatır; gerçek alarm PET 111,8 dk'da gelir. Tekrar eşlemesi utc = utc0 + (PET − PET0). Senaryolu koşuda `sim_clock` duraklatılmış başlar; `scenario_player`, ilk RedLine ile doz ve görev durumu yayıncıları hazır olunca `running=true` yapar. Bu, ilk uçtan uca testte saatin düğümlerden önce koşup alarmın kaçırılması üzerine eklendi. ScenarioControl: LOAD/START/PAUSE/RESUME/STOP. SEEK, robot konumlandırması (set_pose, "teleport") gelene kadar açık bir mesajla reddedilir. `pause`/`resume` eş-etkili yapıldı; önceden çalışırken resume PET'i geri atıyordu.
- **rad_replay:** her görev saati tik'inde DoseRate yayımlar; alarm, alarmlı okumanın başladığı PET'ten en fazla bir tik sonra ulaşır. `historical_utc` okumanın kendi zamanıdır; ufuk küpü yokken `sky_view_factor = 1`.
- **mission_manager (T6 alt kümesi):** SEP alarmının yükselen kenarında CONTINGENCY, EMERGENCY `SEP_ALERT` Alert ve DecisionRecord. ReturnToShelter hedefi kabul edilince RETURN, başarıyla bitince DEBRIEF. "Sığınak modu" (FR-04) = CONTINGENCY/RETURN/DEBRIEF.
- **ReturnToShelter sunucusu `walkback_field`'da:** dönüş alanını bilen düğüm o. Geri bildirim: ETA = mürettebat hücresindeki W_ε, mesafe = yol mesafesi. Başarı: bütün mürettebat habitata ≤ 10 m. `pr_1` sığınağı T9'a kadar reddedilir. Düğüm MultiThreadedExecutor ile çalışır.
- **SEP modu:** alarm sürdükçe `walkback_field`, FR-03'ü (risk düzeltmeli sığınak yürüyüşü ≤ 20 dk) MarginField/RedLine'a uygular; dışarıdaki hücreler −inf ve LIM_SHELTER olur.
- **rule_monitor (`redline_safety`, `config/rules.yaml`):** FR-04 ve FR-01 PET üzerinden 10 Hz değerlendirilir; diğer kurallar dosyada "evaluated: false" ve hedef taşla durur. FR-04 uyumu bir kez INFO kaydı olarak yayımlanır, böylece bir koşu kuralın sağlandığını kanıtlayabilir.
- **Gerçek S1 (BXW, RAD sol 4190, 60× PET):** alarm PET 6715 s (beklenen 6710 s), FR-04 gecikmesi 0 s, abort alanı 6,02 → 0,41 km², EV1 eve dönünce DEBRIEF. Kanıt `test-results/s1-bxw-20261114T184308Z-S1_SEP_4190-42/`, Unreal beslemesi `runs/20261114T184308Z-S1_SEP_4190-42/ue_feed.jsonl`.
- **T6'da açık kalanlar:** `env_server` (SPICE güneş/ışık süresi ve gün ışığı payı terimi), `rems_replay`, Unreal `WBP_SpaceWeather` ve Unreal'daki alarm/çizgi kabulü, SEEK, PR karşılaması (T9).

## D013 — İki müzik take'inin Unreal sunum evrelerine ayrılması

14 Kasım 2026, 22:13 (+03:00) · Kullanıcının “ikisini de farklı kısımlarda kullanalım” kararı.

- Take 01 BRIEFING, PRECURSOR, TRAVERSE, STATION_SCIENCE ve DEBRIEF; take 02 CONTINGENCY ve RETURN evrelerinde kullanılır.
- Müzik yönlendirmesi yalnız Unreal sunum katmanındadır. `/redline/mission/state` okunur; ROS/Gazebo görev, fizik ve komut yetkisi değişmez.
- Geçiş 2,5 s eş-güç crossfade, başlangıç ses seviyesi 0,28'dir. İki üretimde de loop dikişi işitsel olarak doğrulanmadığı için `SoundWave.bLooping=false`; görev yatağı bölüm başına tek geçiştir.
- Kaynak MP3'ler ve Beatra artifact/hash/provenans kaydı korunur. UE 5.8.4 MP3 içe aktarması, iki stereo SoundWave süresi ve üç `Redline.Music` otomasyon testi gözlendi. Çalışma-zamanı testi ses aygıtı açık gerçek game-type Unreal dünyasında bridge fazlarıyla take 01 → take 02 → take 01 oynatma rotasını doğruladı. Final konuşma/alarm miks kabulü ayrıca yapılacaktır.

## D014 — T6 ortam durumu: SPICE güneş tablosu, LMST, gün ışığı payı ve FR-12

14 Kasım 2026, 22:45 (+03:00) · Claude Code.

- **Güneş tablosu (DERIVED):** `redline_data/spice_env.py` ve `scripts/build_sun_table.py`. Spek §6'daki NAIF genel çekirdekleri kullanılır: `naif0012.tls`, `pck00011.tpc`, `de440s.bsp`. `data/raw/` git dışında olduğu için betik eksik çekirdeği indirir ve SHA256'sını sabitlenmiş değerle karşılaştırır. Boş klasöre indirme de doğrulandı. `de440s` Mars gövdesini (499) içermez (SPKINSUFFDATA). Bu yüzden gözlemci `MARS BARYCENTER`'dır: Güneş vektörü J2000'de LT+S ile alınır ve `pxform J2000→IAU_MARS` ile döndürülür. Barycenter ile gövde merkezi arasındaki fark Phobos/Deimos kütlesinden ≈ 0,2 m'dir ve ihmal edilir. Saha: BXW −4,805° / 137,37°E, küre 3396,19 km (`sites.yaml`), ENU az/el. Ufuk geometriktir (el 0); arazi ufku, ufuk küpü gelene kadar yoktur. Işık süresi `spkpos EARTH NONE` ile alınır. Tablo 2024-05-19 12:00 → 05-22 12:00 UTC aralığında 60 s adımla 4321 satırdır; CSV `73a217a9…`. Biçim D012'deki gerekçeyle CSV + JSON'dur. `spiceypy==8.4.0` `scripts/requirements-data.txt`'e eklendi.
- **LMST:** Mars24 algoritması, `redline_core/solar.py`. RAD sol 4190'ın 258 `START_OBS_MARS` damgasıyla karşılaştırıldı (MSL LMST'si iniş yeri 137,4417°E'de tanımlı): ortalama +39,7 s, en büyük 58,1 s fark; eşik 90 s. Yaklaşık 40 s'lik sabit sapmanın kaynağı açıklanmadı; 60 s tablo adımının altında kalıyor. `env_server` LMST'yi BXW boylamında verir; bu değer MSL saatinden ≈ 17 s geridedir.
- **Kontroller (`docs/verification/T6_SPICE.json`, 3/3):** en yüksek Güneş 70,13°, az 180,15° (güney), LMST 12:00:50. S1 başlangıcından sonraki gün batımı 2024-05-20 13:00:56 UTC, LMST 18:09:38.
- **env_server:** `/env/state` (EnvState) 1 Hz yayımlar; zamanlayıcı kararlı saattedir. PET senaryo eşlemesiyle tarihsel UTC'ye çevrilir. Tablo doğrusal enterpolasyonla okunur; azimut 360/0 sarması için birim vektörle enterpole edilir; tablo dışında NaN döner. `mission_sol` = ⌊PET / sol⌋ + 1. REMS alanları `rems_replay` gelene kadar NaN'dır (rosbridge `null`). Provenance DERIVED; ürün kimliği tablo adı ve SHA256'dır.
- **Gün ışığı payı (§7.6):** `walkback_field`, `sun_table` ve `scenario_file` ikisi birlikte verilince her tikte b = (t_sunset − T_dusk) − t_now hesaplar. m_daylight = b − W_time,ε'dir; sınırlayan LIM_DAYLIGHT olur. Güneş ufkun altındaysa b = −∞ olur. Tablo dışında terim uygulanmaz. Tanılama anahtarı `daylight_budget_min`. Yeni düğüm testi bu yolu sentetik tabloyla sınar: 30 dk pay, gün batımından sonra −∞ ve boş abort bölgesi.
- **FR-12 artık değerlendiriliyor (`config/rules.yaml`):** `rule_monitor` aynı b'yi hesaplar. b ≤ 0 iken habitatın `shelter_radius_m` (10 m) içinde olmayan her mürettebat WARNING üretir. Konumu bilinmeyen dışarıda sayılır. Herkes içerideyse sınıra varıldığında bir kez INFO uyum kaydı yayımlanır. Habitat, `walkback_field` ile aynı ızgara ve yapılandırmadan aynı çekirdek fonksiyonla bulunur: `field_model.place_habitat`. Model de bu fonksiyonu kullanır ve iki yolun eşitliği test edilir. T_dusk (30 dk) ve sığınak yarıçapı tek yerde, `rules.yaml` FR-12'de tanımlıdır; launch aynı değerleri `walkback_field`'a `dusk_min` ve `arrive_radius_m` olarak geçirir.
- **FR-01 düzeltmesi:** sınırlayan mürettebat sığınaktayken iki durumda FR-01 uygulanmaz. (1) Sınır gün ışığıysa: bu FR-12'nin alanıdır; diğer herkesin payı en az o kadar olduğundan onlar da habitattadır. (2) Görev DEBRIEF'teyse: EVA bitmiştir. Gerçek S1'de bu durum oluştu: EV1 PET 9118 s'den beri evde ve `ev_sim` giysi tüketimini sürdürüyor. ≈ PET 29 500 s'den sonra pil payı −32 dk'ya düştü. Eski mantık burada içerideki mürettebat için yanlış FR-01 uyarısı verirdi; yeni koşuda FR-01 kaydı yok. FR-01 metni artık sınırlayan sarfı adlandırıyor.
- **Test kapsamı düzeltmesi:** `scripts/build-t5.sh` varsayılan listesi `redline_safety`'yi derliyor ama test etmiyordu. Bu kayıttan önceki T5/T6 ROS sayıları (27, 29, 30) `rule_monitor` testlerini içermez. Liste düzeltildi; sonuç 37/37.
- **Gerçek S1, gün batımı sınırını geçen koşu (60× PET, 600 s yakalama):** alarm PET 6713 s, bitiş 16 463 s; FR-04 gecikmesi 0 s. Abort alanı alarm öncesi 6,02 km², alarm boyunca 0,41 km²; alarm bitince 3,79 km²'ye döndü, sonra pil tükenmesiyle 0'a indi. DEBRIEF PET 9119 s'de. FR-12 INFO "all crew in shelter" kaydı PET 32 458,6 s'de geldi; beklenen sınır 32 456,5 s'dir (13:00:56,5 − 30 dk). 2 s fark, 60× hızda 10 Hz tik aralığının (6 s) içinde. Son EnvState: el −5,47°, LMST 18:33:54. Kanıt `test-results/s1-bxw-20261114T193408Z-S1_SEP_4190-42/`, besleme `runs/20261114T193408Z-S1_SEP_4190-42/ue_feed.jsonl` (`e0c68c80…`). Kısa koşu `s1-bxw-20261114T191044Z-…`: güneş tablosu açık, sonuçlar D012 koşusuyla aynı. `s1_feed_summary.py` artık `alarm_end_pet_s` ve `abort_area_km2_during_alarm_min` alanlarını da yazar; eski `after_alarm_min` alarmdan sonraki pil ve alacakaranlık sınırlarını da içerir.
- **Notlar:** Jazzy `rosapi_node` kapanışta `ExternalShutdownException` yakalamadan çıkıyor ve log'a traceback yazıyor. Bu yalnız SIGINT'ten sonra, bütün REDLINE düğümleri temiz kapandıktan sonra oluyor; bütün T5/S1 koşularında aynı ve üst akış paketine ait. Ayrıca Windows Python'un `write_text`'i bu oturumda ≈ 35 dosyayı CRLF'ye çevirdi ve bir bash betiği WSL'de çalışmadı; dosyalar LF'ye döndürüldü.
- **T6'da açık kalanlar:** `rems_replay` (REMS), ufuk küpü (arazi ufku ve `sky_view_factor`), Unreal `WBP_SpaceWeather` ve alarm/çizgi görsel kabulü, SEEK, PR karşılaması (T9). EVA sonrası giriş/giysi çıkarma modeli yok: `ev_sim` DEBRIEF'te tüketimi sürdürdüğü için çizgi o noktadan sonra anlamını yitirir (T9).

## D015 — T7/T9 sözleşmeleri: mürettebat, sızıntı, görev akışı, engelli gözlem, VOI, gizli gerçek, LOS, keşif saplaması

15 Kasım 2026, 01:20 (+03:00) · Claude Code. Plan: [T7_T9_T12_PLANI.md](T7_T9_T12_PLANI.md). Plan üç üyeli bir LLM konseyinde incelendi. Bulguların dayandığı satırlar kaynakta yeniden okundu.

- **Mürettebat:** senaryonun `crew` listesi, launch tarafından bütün düğümlere `crew_ids` olarak geçirilir; yoksa `eva.yaml` kullanılır. Her kimlik `crew.yaml`'da tanımlı olmalı. `eva.yaml` tek kişilik (S1) kalır. Gerekçe: `walkback_field` yalnız `eva.yaml` mürettebatına abone oluyordu ve diğerleri için ReturnToShelter'ı reddediyordu.
- **Zaman ve poz yetkisi:** otomatik koşularda iki EV de `ev_sim` `motion: plan` modunda PET üzerinde yürür (SIMULATED). Unreal pozuyla yürüyen EV1 yalnız `time_scale` 1'de kullanılır; o zaman EV2 `follow` modundadır. Her EV'nin tek poz yayıncısı olur.
- **Sızıntı:** `ev_sim` O₂ hızını `k_leak` ile çarpar (spek §8.2, SCENARIO). Fiziksel olarak sızıntı basınç sürümlü bir akıştır; bu bir sınırlamadır. Çekirdek `leak_factor = o2_rate / O2(metabolic_w)` değerini Consumables'tan çıkarır; dönüş için O₂ ihtiyacı bu faktörle ölçeklenir. Önceden yalnız hız ölçekleniyordu ve çizgi yaklaşık k kat iyimserdi.
- **Senaryo olayları:** kanonik yük `redline.scenario_event.v1`; `Alert.text` alanında insan metni, `" | "` ve ardından JSON taşınır. Çekirdekte encode/parse fonksiyonları vardır. `SUIT_LEAK`'i yalnız `ev_sim` tüketir. `mission_manager` sızıntıyı telemetriden, eşik ve kalıcılık penceresiyle tespit eder; enjeksiyon zamanını bilmez.
- **Görev akışı:** başlangıç evresi senaryo parametresidir; S1 TRAVERSE'te kalır. Nominal akış çekirdekteki `mission_flow`'dadır: BRIEFING (PlanEva → v1) → PRECURSOR (PET duraklatılır; robotlar kendi zamanında) → TRAVERSE ⇄ STATION_SCIENCE → RETURN → DEBRIEF (giriş; habitatta tüketim durur). Her geçiş bir DecisionRecord yazar. Diğer ajanın `intro_enabled` oryantasyon akışı ayrıdır; ikisi aynı anda açılamaz. Yeniden plan yalnız PRECURSOR'da yapılır, çünkü planlayıcı hep habitattan başlar.
- **Gözlem v2 (`redline.cell_observation.v2`):** isteğe bağlı `"passable": false`; v1 geçerli kalır. Engelli hücre ayrı bir `blocked` katmanında tutulur, CellState'te `speed_factor = 0` ve `state = DETECTED` olarak yayımlanır, `prepare_terrain`'de yasaktır. "Blocked kazanır" kuralı geçerlidir: daha sonraki bir gözlem engeli kaldırmaz. Saplama yanlış pozitif üretmediği için bu sınırlama kabul edildi. `walkback_field` ile `planner_server` aynı çekirdek delta fonksiyonunu kullanır. `cell_store` ek olarak birikimli, transient-local `/redline/cells/known` (CellDelta) yayımlar. Planlayıcı uyguladığı evidence id'lerini DecisionRecord'a yazar; `mission_manager` keşif kanıtı uygulanmadan v2'yi kabul etmez.
- **Robot görev önerisi:** `/redline/robot_tasks/proposed` üzerinde yalnız DecisionRecord yayımlanır (transient-local, depth 1); `candidates` alanı aday başına `redline.robot_task_proposal.v1` JSON taşır. `mission_manager` gönderim için ayrı bir `robot_task_dispatch` kaydı yazar. Tipli bir `RobotTask.msg` ertelendi.
- **Gizli gerçek:** spek biçiminde `scenario_rocks_<seed>.json` (kaya listesi, `decor`/`navigation` sınıfı; S4 için senaryo yazarının yerleştirdiği kaya kümesi). Senaryodan referanslanır ve yalnız SIMULATED gözlemciler okur. Planlayıcı, VOI ve walkback düğümlerinin dosyayı okumadığı testle sınanır.
- **Tehlike modeli ve VOI (D011 VOI maddesinin yerine):** tek kaya modeli kullanılır. D < D_block kaya sapma süresi ekler (D010 λ); D ≥ D_block kaya hücreyi geçilemez yapar. Planlayıcının önseli Golombek k'dır: SCENARIO, `config/voi.yaml`, BXW'de kaya katmanı yok. VOI = E_o[m(o'ya göre en iyi plan)] − E[m(mevcut plan gözlemsiz yürütülürse, geç keşif dahil)] ≥ 0; bu, spek §7.11 "margin_plan_şimdi" teriminin beklenen değer okumasıdır. Eski değer tanı alanında kalır; düşen istasyon bilim biti olarak cezalandırılır. Önceki VOI, yol üstündeki olası engelli ayak izine 0 puan veriyordu.
- **Görüş hattı ve FR-05:** spek yükseklikleri kullanılır (anten 3 m, EV 2 m). Örneklenen DTM profili üzerinden hesaplanır, eğrilik yok; açıklık payı ve histerezis `rules.yaml`'dadır, sonuç DERIVED'dir. FR-05 tek kişilik mürettebatta uygulanmaz.
- **Keşif saplaması:** `redline_env/scout_stub`, SIMULATED. Donmuş `ExecuteScout`/`SurveyArea` action'larını tam uygular. TF, odom veya `cmd_vel` yayımlamaz; Gazebo'da `scout_1` varsa başlamaz. Algılama sınırlıdır; yalnız PRECURSOR'da uçar, bu yüzden FR-14 uygulanamaz. T7 "alt küme" olarak işaretlenir; Gazebo drone bekliyor.
- **Diğer ajana etkiler:** CellDelta'da `speed_factor = 0` artık "geçilemez" anlamına gelir; `scenario_rocks` biçimi Gazebo spawn'ı için paylaşılır; yeni topic'ler `/redline/cells/known` ve `/redline/robot_tasks/proposed`; `mission_manager`'a akış parametreleri eklenir. Uyumluluk kapısı olarak oryantasyon testi ve S1 her fazda koşar.
- **Konseyin ikinci tur ekleri:**
  - *Oryantasyon akışı:* `eva_intro` PRECURSOR'u atlıyor (0→2→3→4→6). Nominal akış bu akışın yerine geçmez; aynı evre sabitlerini kullanan ayrı bir moddur.
  - *Engelli kodlaması:* yalnız `state` alanını ileten güncellenmemiş bir tüketici, engelli hücreyi "gözlenmiş ve hızlı" görür; bu sessiz bir hatadır. Depodaki iki tüketici (`walkback_field`, `planner_server`) aynı değişiklikte çekirdek delta fonksiyonuna geçer; ikisinin de düğüm testi, engelli bir deltanın sonucu değiştirdiğini doğrular. Diğer ajanın gelecekteki hücre katmanı tüketicisi için bu anlam burada kayıtlıdır.
  - *Yeniden plan:* yalnız PRECURSOR'da yapılır. Donmuş `PlanEva.srv`'de başlangıç konumu ya da kalan sarf alanı yok; EVA sırasında yeniden plan için §5'te bir istisna gerekir.
  - *V3:* spek §16'da V3_MONTE_CARLO bir senaryo kimliğidir. 1000 ROS koşusu yerine çekirdekte koşmak bilinçli bir sapmadır. Kılavuzdaki "1000 koşu ≤ 60 s" hedefi için plan v1 ve VOI sıralaması bir kez hesaplanır, sonuçlar gözlem sonuç vektörüne göre önbelleğe alınır. Hedef tutmazsa bu da sapma olarak kaydedilir.
  - *Taş sırası:* §0.2'ye göre T8, T7 ile T9 arasındadır. T8'in kalan işleri (B1/B2/B5) Gazebo algılayıcılarına bağlı olduğu için T7 ve T9'un alt kümeleri önce yapılıyor. T7 ve T9 "tamam" değil "alt küme" olarak işaretlenir.
- **Engelli kodlaması düzeltmesi (15 Kasım, uygulama sırasında):** ROS mesajında `float` alanların varsayılan değeri 0.0'dır. Bu yüzden `speed_factor` alanını doldurmayan bir yayıncı, bütün hücreleri engelli göstermiş olurdu. Mevcut bir düğüm testi tam bunu yakaladı. Yeni kural: bir hücre ancak DETECTED, `speed_factor == 0` ve `evidence_id` dolu olduğunda engellidir. Gerçek bir engel her zaman bir gözlemden gelir; varsayılan değerlerle kurulmuş bir CellState'in kanıtı yoktur. `cells.delta_updates` bu kuralı uygular ve testi vardır.

## D016 — EV1 oryantasyon başlangıcı ve Unreal T5 bağı

15 Kasım 2026, 01:16 (+03:00) · Codex.

- Kullanıcının hikâyeli astronot başlangıcı isteğiyle mevcut habitat dışı, harita
  masası ve bağlam istasyonu ayrı `EVAFixtures/BXW_EVA` sahnesine alındı. Kaynak
  modeller/dokular değiştirilmedi; yeni üretim kredisi harcanmadı. İstasyon
  SCENARIO bağlam incelemesidir; bilim ürünü veya NASA numune noktası değildir.
- E isteği için yeni `/redline/mission/advance` (`std_srvs/srv/Trigger`) servisi
  yalnız `intro_enabled` modunda açılır. Algoritma `redline_core/eva_intro.py`'dadır.
  Donmuş MissionState kodlarıyla 0→2→3→4→6 oryantasyon dizisi kullanılır.
  PRECURSOR/T7 atlandığı için nominal EVA planı olarak sunulmaz (D015 ile uyumlu).
  Konum 2 s içinde alınmış ve ilgili noktaya ≤4 m uzakta olmalıdır. Sonuçlar
  MissionState ve DecisionRecord'dadır; servis yanıtı yalnız kabulü bildirir.
- Bu modda PET sıfırda bekler; brifing onayından sonra sim_clock parametre
  servisi başarıyla yanıt verince TRAVERSE'e geçilir. Gerçek SEP/etkin sığınak
  aksiyonu etkileşimin önüne geçer. Mevcut S1 modu varsayılan TRAVERSE kalır;
  oryantasyon ve S1 replay aynı koşuda başlatılmaz. Kapanışta yalnız bu betiğin
  açtığı süreç grupları sonlandırılır; rover graph'ına dokunulmaz.
- Unreal EV1 pozu tek yayıncıdan 20 Hz gelir; foot-origin, ENU metre/quaternion
  dönüşümü korunur. Görev hesabı yalnız ROS/core'dadır. M1 hız tablosu core'dan
  dışa aktarılır; QueryCell hücre çarpanını verir. Robot fizik/kontrolü Gazebo'dadır.
- Eksik iskelet/malzeme bağımlılığı kaydı ve kopya struct slot ataması düzeltildi.
  İlk klipler süre/kanal kontrolünü geçse de animasyon kökü ile mesh kökü farklı
  ölçekteydi; yeni baş–ayak geometrisi testi bu hatayı yakaladı. Kök anahtarları
  kendi mesh bağlama ölçeğine çevrilir, in-place root lock kullanılır. Kaynak
  FBX/master dosyaları değiştirilmez. Teknik dayanak UE 5.8.4 yerel kaynak API'sidir.
- Gösterim: FieldTile PNG ≤300 KiB, 8-bit ve metadata boyutu doğrulanır;
  satır 0 güney olduğundan haritada V çevrilir, zemin projeksiyonu dünya/ENU
  koordinatı kullanır. Eski veri gizlenir/etiketlenir; son aktif RAD alarmı
  bağlantı kesilince sessizce kaybolmaz. Dedektör B/E bilgisi korunur.
- Teknik T5 kabulü ile hikâye/nihai UI ayrıdır. Ayrıntılar ve gerçek kabul
  kayıtları: `docs/EVA_PLAYABLE.md`, `docs/verification/T5_ACCEPTANCE.json`.
  T6'nın tam S1 görsel kabulü ve SpaceWeather grafiği tamamlandı sayılmaz.

## D017 — Oyunculu kampanya, sonuç kapıları ve sunum

15 Kasım 2026 · Codex · Kullanıcının uzun görev ve gerçek işlem isteği.

- Donmuş §5 enstrüman action'ları korunur. İki ek arayüz:
  `MissionCommand.srv` (`request_id`, `command`, `target_id`, `expected_revision`
  → kabul/gerekçe/operation_id/revision) ve `CollectSample.action`
  (crew/target/point/container → outcome/sample/product; phase/progress).
  Kabul, yürütme sonucu değildir. Tekrar kimliği ve eski revision yeniden
  yürütme yaratmaz. Kaybolan bağlantı komutları otomatik tekrarlamaz.
- `campaign_controller` yalnız kampanya modunda tek MissionState sahibidir;
  oryantasyon/nominal manager aynı graph'ta çalışmaz. On iki adım tek EVA'yı
  genişletir, belgede belirtilen beş evreyi on iki ayrı EVA'ya çevirmez.
  İlk keşif ve açık saha kararı boyunca PET bekler; saat kontrolünün kabulü
  gelmeden egress açılmaz. Gazebo fizik saati değiştirilmez.
- Güncel gerçek EV1 PoseStamped konumu istenir; türetilmiş CrewState'in
  tekrar yayımlanması eski insan konumunu taze saydırmaz. Bilim başarısı
  ürün + ürünün evidence bağlantısı + ilgili numune durumuyla doğrulanır.
  Scout hata/iptal/boş sonuç temiz rota sayılmaz. Geç action callback'i yeni
  işlemi ilerletemez. Robot pozu yalnız gerçek TF/odom'dan türetilir.
- `redline_science` şimdilik tek ortak lifecycle altında açık SIMULATED
  prototiptir. Mevcut 20 s el tipi ölçüm ve BXW kimyası kalibre edilmemiş
  SCENARIO'dur; D018 arşiv hassasiyeti modeli bu ürünlere bağlanmış sayılmaz.
  Ürün JSON/XML, kalıcı request/kap/numune kayıtları ve ayrı origin/analysis
  noktaları vardır. Fiziksel temas/sondaj/çok noktalı DAN kabulü açık kalır.
- Native kapı ve ayrı poseable numune sunumu ROS görevini tamamlamaz.
  Kamera/kontrol sonuç veya iptal ile geri gelir. Komuta duvarı ve büyük
  konsol ROS durumunu/grafiklerini kullanır. Drone görseli ROS scout TF/odom
  izler; UE rotor dönüşü kozmetiktir. Gazebo motor kontrolü tek fizik sahibidir.
- Fiziksel scout'un truth gözlem adaptörü SIMULATED etiketlidir. Algı yoksa
  uçuş başarısı PARTIAL döner. Yeni sensör/kuvvet kanıtı üretilmiş sayılmaz.
  Başlatma, sınırlamalar ve tarihli kanıt: [CAMPAIGN_PLAYABLE.md](CAMPAIGN_PLAYABLE.md).

## D018 — APXS hassasiyeti arşivden; kampanya bölümünün zamanı ve mesafesi

D017 numarası, diğer ajanın kampanya/oyuncu komut sözleşmesine ayrılmıştır (`MissionCommand.srv`, `campaign_controller.py`). Bu kayıt onu değiştirmez.

- **APXS gürültüsü.** proje.md §9.2 B1 σ_i(t) = σ_ref,i·√(t_ref/t) der. MSL APXS ekinin "Precision Error" sütunları (690 ölçüm, ARCHIVE, SHA pinli) bunu desteklemez. Ana oksitlerde süre üssü yalnız −0,04 ile −0,1 arasında. Hata, standoff ile cm başına +%6 ile +%30 artıyor (log katsayısı 0,060–0,265). Simüle APXS ve temas bilimi ürünleri bu yüzden `redline_core.apxs_precision` modelini kullanır: log σ = log σ_ref + a·log(t/1 sa) + b·log(v/v_ref) + c·max(standoff, 0). Model DERIVED, ürün SIMULATED olarak etiketlenir. Kalibre aralığın dışı (540–41 657 s, standoff ≤ 5,6 cm) reddedilir; dışarıya uzatılmaz. Oyun açısından sonuç: uzun ölçüm az kazandırır, iyi yerleştirme çok kazandırır. Kanıt: `docs/verification/APXS_PRECISION.json`.
- **Bölüm zamanı.** Kısa bir oynanışta gerçek SEP alarmı görünür olsun diye doz verisi kaydırılmaz; çıkış saati seçilir. C1'de çıkış 05:10:00 UTC'dir; gerçek alarm (05:21:50 UTC) PET 11,8 dk'ya düşer. ×1 korunur (D015).
- **Bölüm mesafesi.** Kırmızı çizginin oyunda bağlaması için bilim durağı, riskli dönüş süresi T_ε'nin 12–18 dk olduğu bantta olmalı: gerçek ızgarada habitata 280–454 m. 16–31 m'deki duraklarda FR-03 hiçbir zaman devreye girmez. Bu bir öneridir; kampanya hedef dosyası diğer ajanındır ve değiştirilmedi. Kanıt: `docs/verification/CHAPTER_REACH.json`.

## D019 — S2 giysi kaçağı: telemetriden tespit, eve dönüş; bilinen hücre görüntüsünün hızı

- **Tespit (proje.md §8.7, §16 S2).** Spesifikasyonda kaçak için bir FR yok. `rules.yaml`'a `SUIT_LEAK` kuralı eklendi:
  - Ölçü, bildirilen O₂ hızının metabolik modelin beklediği hıza oranı (D015 leak_factor).
  - Oran ≥ 1,5 olarak 30 s (PET) sürerse `rule_monitor` WARNING RuleViolation ve `/redline/alerts` üzerinde `SUIT_LEAK` uyarısı yayımlar; uyarı mürettebat üyesinin adını taşır.
  - Oran 1,2'nin altına inince INFO yazar.
  - Eşikler SCENARIO'dur. Kaçak sinyali senaryodan güvenlik zincirine doğrudan verilmez; yalnız telemetriden bulunur.
- **Tepki.** `mission_manager` TRAVERSE veya STATION_SCIENCE evresinde WARNING+ SUIT_LEAK uyarısı alınca CONTINGENCY'ye geçer ve bütün mürettebat için ReturnToShelter (habitat) başlatır. Gerekçesi bir DecisionRecord'a yazılır. BRIEFING / PRECURSOR'da kimse dışarıda olmadığı için, RETURN / CONTINGENCY / DEBRIEF'te ise dönüş zaten sürdüğü veya bittiği için uyarı yok sayılır. SEP yine yalnız `/env/dose_rate`'ten tetiklenir; kendi yayımlanan SEP_ALERT yankısı tetiklemez.
- **Bilinen hücre görüntüsü (D015 değişikliği).** `/redline/cells/known` artık her gözlemden sonra değil, en fazla `known_period_s` (0,5 s) aralıkla ve yalnız değişiklik varsa yayımlanır; son görüntü her zaman tamdır. Delta yine gözlem başına birdir. Gerekçe: BXW S4'te (1420 drone gözlemi) görüntü trafiği gözlem sayısının karesiyle büyüdü, mission_manager geride kaldı ve 4 delta kayboldu; D017 kanıt kapısı öncü keşfi bekletti.
- **Simüle yürüyüşte acil dönüş.** mission_manager, ReturnToShelter kabul edilince CONTINGENCY'den RETURN'e milisaniyeler içinde geçer. Bu yüzden ev_sim (plan modu) aktif bir sığınak görevi olan RETURN'ü de acil dönüş sayar ve dönüş alanının yolunu yürür. Görevsiz RETURN, planın son ayağıdır. S2'nin ilk koşusunda bu ayrım yoktu: mürettebat istasyonları gezmeyi sürdürdü ve FR-01 ihlal edildi.

## D020 — Bilim kampanyası yerleri, tablet atlası ve 1 m yüzey v2

- **Görevler ve yerler.** `config/science_campaign_BXW.yaml`, proje.md §9.2'deki yüzey görevlerini istasyonlara dağıtır. Dağıtılan görevler B1, B2, B3, B4, B5, B6, B7 ve B10, ayrıca laboratuvar analizi ve drone keşfi.
  - İstasyon noktası elle yazılmaz: DERIVED bir arazi hedefinin (`targets_v1.json`) kimliği verilir ve istasyonun iddia ettiği sınıf (sırt/çukur) hedefinkiyle aynı olmak zorundadır. Kendi noktasını yalnız altyapı istasyonları (habitat önü, laboratuvar) verebilir.
  - `redline_core.science_campaign` bunu ve şunları denetler: görevler dondurulmuş bir aksiyona ya da iki görev türüne (saha notu, laboratuvar analizi) bağlı, 3D modeller depoda var, amaç metinleri TR ve EN.
  - Tasarım bir deneydir: doğuda kontrol (bilinen örüntü), batıda test (sorunun kendisi). Uzak batı yalnız robotla taranır.
- **pH.** pH laboratuvarda, getirilen numuneden ölçülür ve numunenin alındığı noktaya bağlanır (araştırma notu §4). Phoenix WCL (pH 7,7 ± 0,3, Kounaves vd. 2010) başka bir sahanın prosedür referansıdır, Gale sonucu olarak gösterilmez.
- **Tablet atlası.** `scripts/build_tablet_atlas.py`, 3×3 km'lik harita çerçevesinde kuzeyi yukarıda katmanlar üretir: HiRISE renkli görüntü, kabartma, eğim sınıfı, TPI birimleri, EVA başında dönüş süresi konturları ve SEP sınırı, istasyonlar. Hepsi tek bir `manifest.json`'da (piksel karşılığı, hash'ler, görev amacı, istasyon kartları). İstasyonlar yürünebilir zeminde değilse betik durur. Canlı çizgi ve ürünler ROS'tan üstüne çizilir.
- **Yüzey v2.** Mevcut dışa aktarıcı değiştirilmeden 1 m bölge 1 km'den 2,75 km'ye genişletildi (`surface-v2-1m`). Unreal'a alınması diğer ajanın işidir.
- **Hızlı yolculuk (öneri, uygulanmadı).** Sunumda ışınlanma olabilir, ama yürüyüşün süresi ve sarfı ROS'ta ödenir. Bunun için ayrı bir D kaydı gerekir.

## D021 — Elde tablet, gerçek RViz pikselleri ve isteğe bağlı numune analizi

15 Kasım 2026, 12:01 (+03:00) · Codex · Kullanıcının Tripo tablet ve uzaktan bilim isteği.

- Tripo saha tableti SCENARIO görseldir; kaldırma/indirme ve kol IK'sı Unreal sunumudur. Robot kontrol/fizik sahibi değişmez. T açar, Tab sayfa değiştirir, Z yakınlaştırır.
- `/redline/rviz/image/compressed` gerçek, projeye ait özel Xvfb üzerinde çalışan RViz'in kayıpsız PNG'sidir. Kullanıcı masaüstü yakalanmaz. `/redline/rviz/status` kaynak/akış kimliği, fizik damgası, tazelik ve PNG özeti taşır. Eski görüntü gizlenir. Fizik geri sararsa yeni akış kimliği açılır. Sözleşme: `verification/TABLET_CONTRACT.md`.
- Dondurulmuş bilim action'ları korunur. Ek `AnalyzeSample.srv`, `/redline/science/analyze_sample`: istek/numune/metot/integration_s → kabul/gerekçe/operation_id. Kabul sonuç değildir. Yalnız laboratuvara teslim edilmiş, kap ve kanıt zinciri bulunan numuneler kabul edilir. İşlem sonu zincir yeniden denetlenir; yinelenen istek yeniden analiz başlatmaz.
- `WCL_SCENARIO` pH/iletkenlik serisi açık yazılmış tarif ve tohumu kullanır. Ürün SIMULATED / UNCALIBRATED_SCENARIO, `model_only=true`; köken ve analiz noktası ayrıdır. Tarif ve numune özeti girdilere yazılır. Gale/Phoenix ölçümü veya oksitlerden çıkarılan pH değildir.
- Kampanya durumuna en çok 128 alınmış scout kanıtı eklenir; geç bağlanan tablet mevcut gözlemleri görür. Saklama yeni algı/harita üretmez; SIMULATED truth-adaptörü etiketi korunur. Atlas arayüzü statik katmanları ve canlı veriyi ayırt eder. İstasyon kartı seçmek görev veya yolculuk başlatmaz.

## D022 — Hızlı yolculuğun süre ve sarfı ROS'ta yürütülür

15 Kasım 2026, 12:01 (+03:00) · Codex · Uygulama sınırı; özellik henüz açık değildir.

Unreal yalnız yolculuk sunumunu kısaltabilir. Gidilen yön için ROS'un hesapladığı yol, PET ve fizyoloji birlikte yürütülür; anlık poz değiştirip sonradan süre eklemek kullanılmaz. Gazebo `/clock` değişmez. İstek/sonuç kalıcı ve yinelenmeye dayanıklı olur; manuel/ROS insan pozu sahipliği onaylı devredilir. Alarm, eski veri ve kopma hızlandırmayı durdurur; ödenmiş süre/sarf geri verilmez. Aktif robot işleriyle ilk sürüm yolculuk çakıştırılmaz.

D015'in mevcut UE poz modundaki ×1 sınırı sürer. Atlasın uzak insan istasyonları, gerçek kampanya rota bağları ve sığınak/PR ile alarm zinciri kabulü olmadan açılmaz. Şimdiki kampanya launch'ında scenario_player/RAD/rule_monitor bütünü bulunmadığı için bunlar hazır sayılmaz. `FAST_TRAVEL_CONTRACT.md` mevcut kodu, önerilen action/lease akışını ve gerekli deneyleri kaydeder. Çalışan yolculuk veya güvenlik kabulü iddiası yoktur.
