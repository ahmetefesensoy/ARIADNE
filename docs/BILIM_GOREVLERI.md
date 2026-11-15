# Bilim görevleri, yerleri ve tablet haritası

15 Kasım 2026 · Claude Code · Kaynak: `config/science_campaign_BXW.yaml` ([D020](DECISIONS.md)).

Bu belge oyunun başında okunacak görev amacını, istasyonları ve her görevin içeriğini tanımlar. Görev içerikleri proje.md §9.2'deki B1–B10'dan alınmıştır. İstasyon yerleri elle seçilmedi; gerçek HiRISE arazisinden türetilmiş sırt/çukur hedeflerine (`targets_v1.json`, DERIVED) bağlıdır. Unreal bağlantısı, animasyonlar ve hızlı yolculuk diğer ajanın işidir; aşağıdaki kartlar onun için yazılmıştır.

## Görevin amacı (başlangıç ekranı)

> Bu EVA'nın amacı tek bir soruya cevap aramak: doğuda bilinen sırt-çukur örüntüsü batıda da var mı?
>
> Önce doğudaki iki kontrol istasyonunda aletlerimizi bilinen örüntü üzerinde sınarız. Sonra batıdaki test istasyonlarında aynı ölçümleri yaparız; rover en uzak batı alanını tarar. Her ölçüm haritaya ve inanç çubuğuna işlenir.
>
> Her dakika dönüş payından ödenir: kırmızı çizginin dışına çıkılmaz, alarm gelirse bilim bekler. Numuneler laboratuvara getirilir; pH ve bileşim orada ölçülür ve numunenin alındığı noktaya bağlanır.
>
> Sonuçlar simülasyondur: Mars'ta yeni bir keşif iddiası yoktur. Amaç doğru kararı, doğru kanıtla, güvenle vermektir.

İngilizcesi aynı dosyada (`mission_brief.en`). Bilim sorusu `config/science_BXW.yaml` ile aynıdır.

## İstasyonlar

Kontrol istasyonları doğuda, test istasyonları batıdadır, çünkü soru batı uzantısını soruyor. Mesafeler gerçek ızgaradan hesaplandı: düz çizgi, yürüyüş yolu, ortalama yürüme süresi ve riskli dönüş süresi T_ε. T_ε, SEP alarmında FR-03'ün 20 dk sınırıyla karşılaştırılan süredir.

| İstasyon | Rol | Arazi | Uzaklık / yol | Yürüme / T_ε | Görevler |
|---|---|---|---|---|---|
| ST-H Habitat önü | altyapı | düz, 4,9° | 37 m / 37 m | 1,4 / 1,9 dk | B7 çevre istasyonu, drone koridor keşfi |
| ST-E1 Doğu çukuru (T10) | kontrol | çukur, 4,9° | 374 m / 609 m | 20 / 27 dk | B10 not, el tipi XRF, numune tüpü, kap |
| ST-E2 Kuzeydoğu sırtı (T01) | kontrol | sırt, 10,5° | 724 m / 1081 m | 39 / 52 dk | B3 multispektral, B2 rover LIBS (otonom hedef) |
| ST-W1 Batı sırtı (T05) | test | sırt, 8,6° | 628 m / 674 m | 25 / 33 dk | B3, B1 rover APXS, B10 not |
| ST-W2 Kuzeybatı çukuru (T08) | test | çukur, 8,4° | 1117 m / 1341 m | 68 / 90 dk | B5 sondaj + FDIR, B1 APXS, numune tüpü, kap |
| ST-W3 Uzak batı (T09) | test, yalnız robot | çukur, 7,9° | 1339 m / 1903 m | 87 / 116 dk | B4 DAN nötron taraması |
| ST-LAB Laboratuvar (H05) | altyapı | habitat içi | 15 m | 0,5 dk | pH, iletkenlik ve bileşim analizi |

Yalnız ST-H, SEP alarmında 20 dakikalık güvenli bölgenin içindedir. Diğer bütün istasyonlar dışındadır. Bu kasıtlı: çizgi oyuncuya bilimin bedelini gösterir. Alarm geldiğinde uzak istasyondaki mürettebat için cevap sığınağa koşmak değil, planı baştan buna göre kurmaktır. Sonraki adım basınçlı roverın (pr_1) karşılamasıdır (proje.md §7.7).

## Görev kartları

Uç noktalar diğer ajanın `redline_science` düğümündendir ([SCIENCE_REHEARSAL](SCIENCE_REHEARSAL.md)). "Animasyon" sütunu, Unreal'da oynanacak sunum içindir; ölçümün sonucu her zaman ROS ürününden gelir.

| Görev | Kim | 3D model | Animasyon önerisi | ROS | Veri durumu |
|---|---|---|---|---|---|
| B1 APXS (kol) | rover_1 | `tool_apxs` | Kol başlığı kayaya iner, temas, sayım ilerlemesi; standoff göstergesi | `ContactScience` `/rover_1/contact_science` | Hata **DERIVED** (APXS arşivinden, D018); bileşim SCENARIO |
| B1 el tipi XRF (B10) | EV1 | `tool_apxs` | Astronot aleti yüzeye tutar, basılı tut | `ContactScience`, `instrument=EV1_XRF` | Aynı model; standoff'a duyarlı |
| B2 LIBS + AEGIS | rover_1 | `tool_libs` | Direk döner, 1×5 lazer kıvılcımı; hedef boşsa rover seçer | `RemoteLibs` `/rover_1/remote_libs` | SCENARIO; ChemCam RDR yok; menzil ≤ 7 m [?] |
| B3 Multispektral | EV1 | `tool_multispectral` | Filtre çarkı döner, panorama | `MultispectralImage` | SCENARIO; splib07 yok |
| B4 DAN | rover_1 | `tool_neutron` | Rover durur, sayım; harita hücre hücre dolar | `NeutronSurvey` `/rover_1/neutron_survey` | SCENARIO; DAN RDR yok; GP ve σ tablete |
| B5 Sondaj + FDIR | rover_1 | `tool_drill` (ayrı uç) | Uç döner ve iner; tork göstergesi; sıkışmada geri çekme ve darbeli moda geçiş; kamera titrer | `Drill` `/rover_1/drill` | SCENARIO sertlik; 2016 besleme arızası tarih notu [?] |
| B6 Numune toplama | EV1 | `sample_tube` | Kepçe, tüpe doldurma, kapak | `CollectSample` `/redline/science/collect_sample` | SCENARIO; köken bir kez yazılır |
| B6 Önbellek | EV1 | `sample_case` | Tüp kutuya kilitlenir | `CacheSample` `/redline/science/cache_sample` | SCENARIO |
| B7 Çevre istasyonu | EV1 | `science_station` | İstasyonu taşı, dik, anten açılır | `DeployStation` `/redline/science/deploy_station` | Doz **ARCHIVE** (RAD sol 4190); hava için REMS yok |
| B10 Saha notu | EV1 | `station_marker` | Fotoğraf, not, bayrak dikme | `/crew/EV1/science_note` | SCENARIO; arka oda ışık gecikmesiyle cevap verir |
| Lab: pH ve bileşim | EV1 | `lab_bench` | Kap kabulü, hazırlık, ölçüm ilerlemesi | `lab_analysis` | SCENARIO; Phoenix WCL (pH 7,7 ± 0,3, Kounaves vd. 2010) yalnız prosedür referansı, Gale sonucu değil |
| Drone koridor keşfi | scout_1 | `scout_1` | Kalkış, koridor taraması, iniş | `ExecuteScout` | SIMULATED; S4 kabulü geçti |

pH haritaya sürekli bir alan olarak boyanmaz. Sonuç numunenin özelliğidir ve numunenin alındığı noktada gösterilir (araştırma notu `SAHA_VE_BILIM_ISTASYONU.md` §4–5).

## Tablet: uzaktan haritalama

`scripts/build_tablet_atlas.py` çıktıları `data/engines/BXW/tablet-atlas-v1/` altında. Her katman 3×3 km'lik harita çerçevesini kapsayan 2048×2048 piksellik, kuzeyi yukarıda bir PNG'dir (1,465 m/piksel). Piksel karşılığı: `sütun = (x + 1500) / 1,465`, `satır = (1500 − y) / 1,465`.

| Katman | İçerik | Durum |
|---|---|---|
| `imagery.png` | HiRISE 78 karelik renkli mozaik (Parker ve Calef). Gri şerit, sağlayıcının renksiz HiRISE şeridi. | DERIVED |
| `hillshade.png` | 1 m HiRISE DTM'den kabartma | DERIVED |
| `slope_class.png` | Yürünebilir < 15°, dikkat 15–25°, yasak ≥ 25° veya eve yol yok | DERIVED, sınırlar SCENARIO |
| `science_units.png` | TPI sırt (turuncu) / çukur (mavi), |TPI| ≥ 1 m. Bileşim değildir. | DERIVED |
| `return_time.png` | EVA başında habitata riskli dönüş süresi. 10/30/45/60 dk konturları, 20 dk SEP sınırı kalın kırmızı. | DERIVED |
| `stations.png` | İstasyon pinleri: kontrol mavi, test turuncu, altyapı beyaz | SCENARIO |

`manifest.json`, katmanları, hash'leri, bilim sorusunu, görev amacını (TR/EN) ve her istasyonun konumunu, yüksekliğini, mesafesini, dönüş süresini ve görev kartlarını tek dosyada verir. Önizlemeler: [güvenlik](verification/TABLET_ATLAS_PREVIEW_safety.png), [bilim](verification/TABLET_ATLAS_PREVIEW_science.png).

Canlı kırmızı çizgi, drone kanıtı, DAN alanı ve ürün noktaları bu statik katmanların üstüne ROS'tan çizilir. Statik `return_time` yalnız EVA başını gösterir.

## Hızlı yolculuk kuralı (öneri)

Kullanıcı uzak istasyonlara yürüyüş animasyonuyla "ışınlanmayı" önerdi. Bu yalnız sunum olabilir; payın dürüst kalması için bedel ROS'ta ödenmeli:
- Yolculuk ROS'tan istenir. Yol `leg_path`, süre yürüyüş modelidir.
- Görev saati (PET) ve sarf o süre kadar ilerler; zaman hızlandırması yalnız bu yürüyüş boyunca olur ve bir DecisionRecord'a yazılır.
- Alarm gelirse yolculuk durur.

Bu kural mission clock'a dokunduğu için uygulanmadan önce ayrı bir D kaydı gerekir.

## Mars yüzeyi

Unreal'daki mevcut yüzeyde (`surface-v1`) yalnız merkezdeki 1×1 km 1 m çözünürlükte; geri kalanı 4 m. Batı istasyonlarının hepsi 4 m bölgede kalıyordu. `surface-v2-1m`, aynı dışa aktarıcıyla 1 m bölgeyi 2,75×2,75 km'ye genişletir (11×11 karo, 250 m). Bütün istasyonlar bu bölgenin içinde. Unreal'a alınması diğer ajanın içe aktarma betiğinde v1 yerine v2 yolunu vermeyi gerektirir.

## Eksik 3D modeller (Tripo promptları, üretilmedi)

Bu oturumda `TRIPO_API_KEY` tanımlı değildi; kalan bakiye kayıtta 380 kredi. Mevcut modeller (APXS, LIBS, matkap, nötron, multispektral kamera, numune tüpü/kutusu, çevre istasyonu, işaret, laboratuvar tezgâhı) görevleri karşılıyor. Eksik olan iki model:

| Varlık kimliği | Prompt (EN, `tools/tripo_generate.py <id> "<prompt>"`) | Kullanım |
|---|---|---|
| `field_tablet` | "Rugged handheld field tablet for a Mars EVA astronaut, thick protective frame, large matte screen, side grips with large buttons for gloved hands, wrist strap, no logos, no text, realistic product model" | Uzaktan haritalama atlası ve görev kartları bu cihazda görünür |
| `wetchem_analyzer` | "Compact laboratory wet-chemistry soil analyzer for a Mars habitat lab: sealed sample cell with a hinged lid, pH and conductivity electrode ports, small reagent cartridges, status display, metal and white plastic, no logos, no text, realistic scientific instrument" | Laboratuvarda pH ve iletkenlik analizi |

Üretim sonrası ölçek, LOD ve kaynak kaydı mevcut paket hattıyla (`assets/production/`) yapılmalı.

## "Nasıl çalışır" anlatım videoları

`assets/production/explainer_videos.py` (Blender 5.2, EEVEE) her bilim görevi için kısa bir anlatım videosu üretir. Videolar projenin kendi 3D paketleriyle hazırlanır ve Unreal içeriğine dokunmaz.

```
blender --background --python assets/production/explainer_videos.py -- <görev> [--preview] [--still <saniye>]
```

Çıktılar `assets/explainers/<görev>/` altında:
- `<görev>.mp4` (1920×1080, 30 fps, H.264) ve `poster.png`,
- `captions_tr.srt`, `captions_en.srt`,
- `explainer.json`: bölümler, kullanılan varlıklar ve durum notu.

| Görev | Süre | Anlattığı | Ekrandaki sayılar |
|---|---|---|---|
| `drill` (B5) | 25 s | İniş, dönme, besleme, toz; tork sınırında sıkışma → geri çekilme → darbeli mod → 5 cm → numune | SCENARIO sertlik/tork hikâyesi; ölçüm değil |
| `apxs` (B1) | 24 s | Cm-244 uyarması, elementlerin X ışını cevabı, sayım; temas iyileşince hata küçülür | ± değerleri gerçek APXS arşivi modelinden (D018) hesaplanır; bileşim SCENARIO |
| `libs` (B2) | 24 s | AEGIS benzeri aday seçimi, lazer, plazma, 5 noktalık tarama, spektrum çizgileri | Çizgi dalga boyları NIST değerleri. Kızılötesi lazer görünmez, burada çizildi; bileşim yok |

Her videonun altında kalıcı bir durum etiketi var ("SİMÜLASYON", veri kaynağı ve proje.md maddesi). Unreal'da oynatmak için Media Player, File Media Source ve Media Texture yeterli. Videolar görev başında ya da tablette oynatılabilir. Altyazılar ayrı SRT dosyalarında olduğu için dil seçilebilir.
