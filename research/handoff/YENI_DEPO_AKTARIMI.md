# REDLINE v3 — Yeni depoya ve yeni AI oturumuna aktarım

14 Kasım 2026 · Yeni uygulama sıfırdan yazılacak. Bu belge burada bulunan
skill, araştırma ve makine bağlamının yeni yerde nasıl kullanılacağını açıklar.

**Yeni ajan için esas dosyalar:** [v3 uygulama spesifikasyonu](../proje-fikirleri/REDLINE_V3_UYGULAMA_SPEKI.md)
§0–4 ve §18, ardından [v3 kılavuzunun](../proje-fikirleri/REDLINE_V3_KILAVUZU.md) ilgili bölümü.
`PROJE_KILAVUZU.md` ve diğer eski taslaklar tarihsel başvurudur; v3 ile
çelişirlerse eski kararı uygulama. Kullanıcının sonraki açık yönlendirmesi esastır.

## 1. Aynı bilgisayar ile başka bilgisayar arasındaki fark

| Nerede başlanıyor? | Otomatik gelen | Ayrıca taşınacak/kurulacak |
|---|---|---|
| Aynı Windows kullanıcısı, yeni Codex klasörü | Kullanıcı profilindeki skill'ler ve kurulu programlar erişilebilir olabilir | Bu depoya özel `.agents/skills`, v3 belgeleri ve araştırma kayıtları |
| Başka bilgisayar/kullanıcı | Bu makinenin kurulumları ve hesapları gelmez | Proje skill'leri, gereken kullanıcı skill'leri, runtime/toolchain ve yeni erişim ayarları |
| Başka AI uygulaması | Codex tool adları, sohbet bağlamı ve ajan kapasitesi gelmez | Desteklediği skill dizini/araç eşlemesi; eksik yeteneklerin açık kaydı |

Bir klasörde skill dosyalarının bulunması editör bağlantısı, ROS paketi, ücretli
abonelik veya çalışır köprü sağlamaz. Sohbet geçmişinin yeni ajan tarafından
bilindiğini varsayma; önemli kararlar bu dosyalardadır.

## 2. Projeye kurulan 18 skill

`.agents/skills` klasörünü **tamamıyla** taşı: yalnız SKILL.md değil, aynı
klasördeki `references`, `scripts`, `assets`, `agents` ve lisanslar da gerekir.

| Alan | Skill adları |
|---|---|
| REDLINE bağlamı | `redline-space-apps` — v3'e güncellendi |
| Council | `quorum` |
| ROS/Gazebo/Nav2/MoveIt | `ros2-engineering-skills` |
| Unreal | `ue-project-context`, `ue-cpp-foundations`, `ue-module-build-system`, `ue-blueprint-cpp-interop`, `ue-async-threading`, `ue-ui-umg-slate`, `ue-testing-debugging` |
| Gezegen/GIS | `planetary-geologist`, `geomaster` |
| Bilim/fikir | `scientific-brainstorming`, `scientific-critical-thinking`, `scientific-visualization` |
| Analiz | `jupyter-notebook` |
| GitHub | `gh-fix-ci`, `gh-address-comments` |

Kaynaklar, lisans ve sabit commit'ler [skill planında](../proje-fikirleri/SKILL_PLANI.md), tam
dosya hash'leri `.agents/skills-manifest.json` içinde. 17 dış kaynak skill'i
değiştirilmedi. `redline-space-apps` bu proje için yazılmış yerel skill'dir.

Quorum, seçtiğimiz LLM Council skill'idir. Mini aynı oturumdaki bakış açılarıdır;
Full için gerçekten bağımsız aday/değerlendirici ajan gerekir. Yeni uygulamanın
ajan kapasitesi veya model erişimi ayrıca kontrol edilir. Ayrı Claude/Gemini
hesapları, API kredileri ya da otomatik hafıza bu paketle oluşmaz. Burada son
kontrolde Quorum otomatik hafızası kapalıydı.

## 3. Kullanıcı profilinde olan, yalnız bu depoyu taşımakla gelmeyenler

Bu makinedeki kök: `C:\Users\USER\.codex\skills`. Aynı kullanıcıyla yeni Codex
deposunda mevcut olabilirler. Başka makinede gereken skill klasörleri kendi
referans ve lisanslarıyla kopyalanır veya asıl kaynaktan kurulur.

| İş | Burada bulunan kullanıcı skill'leri |
|---|---|
| Üretim/model | `blender-director`, `blender-modeler`, `hard-surface`, `vehicle-artist`, `environment-artist`, `prop-artist` |
| Prosedürel sahne | `procedural-modeling`, `geometry-nodes`, `scene-assembly`, `set-dressing` |
| Görünüm | `materials`, `uv-workflow`, `texture-workflow`, `lighting`, `lookdev`, `rendering` |
| Hareket | `rigging`, `animation` |
| Oyun motoruna hazırlık | `asset-optimization`, `lod-pipeline`, `collision-proxy`, `unreal-export`, `qa-review` |
| Yazım/çalışma biçimi | `intent-modeling`, `llm-writing`, `information-hierarchy` |

**Mevcut bir eksik:** Blender Director ve bazı uzman skill'ler
`../references/asset-pipeline.md` gibi ortak dosyalara bağlanıyor. Beklenen
`C:\Users\USER\.codex\skills\references` dizini burada da yok. İlgili kaynak
paketinin ortak referansları tamamlanmadan bu skill'lerin tüm kaynakları hazır
sayılmaz. `unreal-export/references/unreal-checklist.md` gibi bazı yerel
referanslar ise mevcut. Eksik dosya yerine uydurma içerik koyma.

OpenAI skill-creator/installer, imagegen ve bağlı belge/sunum/bilgisayar kontrolü
skill'leri bu oturumun sistem/plugin ortamından geliyor. Bunlar yalnız bir metin
dosyasını kopyalayarak yeni uygulamaya aynı araç yetkisini kazandırmaz. Kişisel
Codex config'i, plugin önbellekleri ve hesap oturumları taşınmaz.

## 4. Taşınacak araştırma ve kaynak kayıtları

| İçerik | Nerede? | Nasıl yorumlanacak? |
|---|---|---|
| Güncel tasarım ve uygulama | İki `REDLINE_V3_*.md` | Kodlamanın esası |
| Veri/varlık/araç seçimi | `KAYNAK_VE_VARLIK_KATALOGU.md`, `SKILL_PLANI.md` | V3 ile birlikte; eski adaylar kurulmuş sayılmaz |
| Araştırma kayıtları | `research-notes/` | Ürün, label ve metadata kontrolleri; sonuçların sınırı korunur |
| Tekrar çalıştırılabilir kontrol | `output/jupyter-notebook/nasa-metadata-coverage.ipynb` ve `.validation.json` | Python hücreleri çalıştı; raster hizalaması ve Jupyter kernel testi değil |
| Ayrıntılı v0.3 araştırması | `önceki deneme/docs/REDLINE_RESEARCH.md` | V3'ün atıf verdiği araştırma; eski uygulama kodu değil |
| Eski arazi kaynak kaydı | `önceki deneme/ros2_ws/src/redline_mars_sim/TERRAIN_PROVENANCE.json`, `önceki deneme/assets/mars/gale_aoi/crop.json` | Önceki ürün/orijin/kırpım bilgisi; yeni BXW/YKB sahası değil |
| Yerel UE envanteri | `.agents/ue-project-context.md` | Eski makine ve Blueprint şablonu gözlemi; yeni C++ projesinde yeniden çıkarılır |
| Konsey araştırması | `research-notes/council-v3-source/` | TEMP'ten kurtarılan karar/inceleme çıktıları; kaynak/hash kaydı korunur |

Paketin araştırma kopyalarında eski dosya yolları korunabilir; bu, eski kod
klasörünün tamamının aktarıldığı anlamına gelmez. `.agents/skills-validation.json`
önceki kontrolün kaydıdır; yeni klasörde bütünlük yeniden kontrol edilir.

## 5. Skill'lerin kurmadığı yazılımlar ve makine bilgileri

| Bileşen | Hedef/son bilinen | Yeni yerde gereken |
|---|---|---|
| Unreal | Yerel engine `C:\Users\USER\Desktop\UE_5.8`, 5.8.4 | UE ve uygun C++ toolchain; yeni `unreal/Redline` C++ projesi |
| Eski UE şablonu | `C:\Users\USER\Documents\Unreal Projects\MyProject` | Bu Blueprint şablonu yeni REDLINE projesi olarak kopyalanmaz |
| WSL | `Ubuntu-24.04` dağıtımı listede mevcut | Gerçek ROS ortamı, kullanıcı ve workspace yeniden kontrol edilir |
| ROS/Gazebo | Jazzy / Harmonic, son bilinen kurulum | Gerekli paketler: ros_gz_bridge, rosbridge, Nav2, ros2_control/gz_ros2_control; ilgili aşamada MoveIt |
| Alan/partition | `ROS_DOMAIN_ID=77`, v3 hedefi `GZ_PARTITION=redline` | Yeni workspace bunu açıkça ayarlasın; eski demo değerini körlemesine kopyalamasın |
| Python | V3 hedefi 3.12 | İzole veri/çekirdek ortamları; GDAL/rasterio/pyproj, PDS/SPICE ve ilgili bilim paketleri |
| Telemetri/web | Open MCT, Node.js; sürüm spec'te [?] | Gerçek package.json/engine gereksinimine göre pin ve kurulum |
| Araçlar | Git, Python, gh, Node/uv bu makinede erişilebildi | Başka makinede PATH ve sürümler doğrulanır |
| Görsel üretim | Blender skill dosyaları mevcut | Blender uygulaması ve gerçekten erişilebilir MCP/kontrol bağlantısı ayrı |

Port hedefleri: rosbridge **9090**, Foxglove **8765**, Open MCT **8080**,
geçmiş servisi **8081**, web harita **8082**. Port yazmak servisi başlatmaz.
Windows–WSL localhost ve GPU/sensör render yolu küçük testle doğrulanır.

GitHub kimlik doğrulaması, Epic/Fab erişimi, varsa Cesium ion token ve
Meshy/Tripo aboneliği ayrıca gerekir. Burada Tripo satın alındığı veya yeni
Cesium/Blender bağlantısı kurulduğu doğrulanmadı. Sırlar ve kişisel oturum
dosyaları pakete konmaz. Parsec yalnız uzak erişim katmanıdır.

## 6. Yeni ajanın bilmesi gereken mevcut durum

- Eski araştırma deposunun remote'u `https://github.com/ahmetefesensoy/space-apps-redline.git`.
  Yeni uygulama için henüz bir hedef depo/klasör belirtilmedi; burada yeni remote oluşturulmadı.
- V3: **BXW ileri EVA, YKB kalibrasyon/tutarlılık, tek EVA'nın beş evresi**.
  Eski “YKB ana, Gobabeb yedek, beş ayrı demo” tasarımı geri getirilmez.
- İlk uçtan uca hat v3 spec §18.1'de: BXW veri → çekirdek çizgi → ROS
  FieldTile/RedLine → Unreal → RAD4190 replay → alarm/çizgi daralması.
  Gazebo/Nav2 akışı §18.2'deki sözleşmeyle birleşir.
- Yeni ROS–Unreal köprüsü, BXW/YKB veri hattı, on bilim aksiyonu, Open MCT ve
  yeni C++ proje tamamlanmış değildir. Metindeki paket/class/msg tanımları
  uygulanacak sözleşmelerdir; var olan kaynak dosyaları gibi import edilmez.
- Bu aktarım taramasında ham RAD4190/242, yeni DTM/STAC ürünleri veya kalibre
  BXW ölçüm dosyaları bulunmadı. Belgede ürün/değer yazması dosyanın hazır olduğu
  anlamına gelmez. V3 etiketlerinin dayandığı birincil kanıt tekrar bulunabilir olmalı.
- APXS koordinat anlamında kayıtlar arasında fark var: v3 “rover pozu” diyor;
  eski QA hedef/örnek/analiz ayrımını açık bırakıyor. İlgili ürün label'ı ve
  PLACES eşleştirme kanıtıyla çöz; bütün satırlara doğrulanmamış tek yorum uygulama.
- Fizik `/clock` ile görev/PET saati ayrıdır. Senaryo zaman atlaması, fiziksel
  sürüş testiyle karıştırılmaz; konum atlamaları kayıtta işaretlenir.
- ARCHIVE / DERIVED / SIMULATED / SCENARIO ayrımı, örnek kökeni–analiz yeri
  ayrımı ve Mars CRS doğrulaması korunur. [?] maddeler doğrulama günlüğüne gider.

## 7. Kopyalanmayacaklar ve ilk çalışma

Yeni uygulamaya eski `önceki deneme/ros2_ws/src` kodu, önceki web uygulaması,
`roversim27` kaynakları, build/install/log, UE DerivedDataCache/Intermediate,
API anahtarları veya hesap ayarları taşınmaz. Eski DEM mesh/doku yeni iki sahanın
yerine geçirilmez. Skill paketlerindeki üçüncü taraf helper'lar ve aktarım
bütünlük aracı önceden var olan geliştirme araçlarıdır; sıfırdan yazılan
REDLINE uygulama kodundan ayrı beyan edilir.

Yeni ajana şu mesaj verilebilir:

```text
Bu yeni REDLINE v3 uygulama deposu. YENI_DEPO_AKTARIMI.md dosyasını, sonra
REDLINE_V3_UYGULAMA_SPEKI.md §0–4 ve §18'i oku. V3 kılavuzuyla birlikte uygula.
Proje skill'leri .agents/skills altında; konuya göre ilgili SKILL.md'yi aç.
Eski uygulama kodunu kopyalamadan T0'dan başla. Gerçek ortamı kontrol et;
paket/class adlarının yalnız taslak olabileceğini unutma. [?] maddeleri küçük
deneyle doğrula ve docs/VERIFICATION_LOG.md'ye yaz. Her taşı gerçekten test edip
docs/PROGRESS.md'yi güncelle. Kaynak verisi olmayan ölçüm veya başarı sonucu uydurma.
```

Taşınabilir arşiv `output/handoff/REDLINE_V3_BASLANGIC_PAKETI.zip` altında
hazırlanır. Yeni **boş** klasöre çıkarılır; mevcut uygulama dosyalarının üzerine
otomatik yazılmaz. Arşivdeki README aktarılacak ve ayrıca kurulacak şeyleri ayırır.
