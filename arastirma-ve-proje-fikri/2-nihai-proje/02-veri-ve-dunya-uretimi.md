# 02 · Veri yığını ve dünya üretimi

> REDLINE v3 nihai proje · Kılavuz bölümleri: §3, §16 · [← 01](01-challenge-ve-sahalar.md) · [← Nihai proje](README.md) · [03 →](03-cekirdek-modeller-ve-teori.md)
>
> Etiketler: **[D]** birincil kaynaktan doğrulandı · **[K]** önceki araştırma kaydı · **[?]** doğrulanmadı.

## 3. Veri yığını

### 3.1 Katmanlar ve karar rolleri

| Tür | Ürün | Erişim | Statü | Karar rolü |
|---|---|---|---|---|
| Topografya | Trek `Gale_DEM_SMG_1m` (lon 137,12–137,73, lat −4,93…−4,25; iki sahayı da kapsar) [D, stage 2] | Mars Trek | ölçümden türetilmiş | eğim, viewshed, rota |
| Topografya σ | HiRISE DTM'ler: `DTEEC_010573_1755_010639_1755_U01` [D] + iki YKB DTM'i, iki boxwork DTM'i [K] | USGS STAC `mro_hirise_socet_dtms` (COG, Float32, CC0 [K]) | türetilmiş | DTM'ler arası ampirik uyuşmazlık |
| Topografya σ | CTX DTM `intersection_error` | STAC `mro_ctx_controlled_usgs_dtms` [K] | türetilmiş | stereo hata katmanı |
| Optik | HiRISE ortho 0,25 m; HiRISE zaman serisi (ESP_030313, ESP_032436 rover'ı yörüngeden gösterir [K]) | USGS / PDS | ölçüm | morfoloji, tespit sınırı |
| Termal | THEMIS TI 100 m (doğruluk ~%20 [K]) | USGS Astropedia, Trek | türetilmiş | kum / pekişmiş kayaç önseli |
| Spektral | CRISM MTRDR (gözlem ID'si [?]) | PDS Geosciences / ODE | türetilmiş | mineral önseli; "tespit yok ≠ yok" |
| Jeoloji | USGS SIM 3292 (YKB = AHi, tek poligon 87.031 km²; boxwork = Htu) [K] | USGS ArcGIS | yorum | ölçek merdiveni |
| Kimya | APXS supplement `ds01_2020je006536rr.csv`; CheMin RDR (John Klein "preliminary", kil 22±11) [K] | PDS Geosciences | ölçüm | istasyon kartı ve hata çubukları |
| Radyasyon | MSL RAD RDR `MSL-M-RAD-3-RDR-V1.0` [D] | PDS PPI | ölçüm | SEP alarmı |
| Atmosfer | REMS `MSL-M-REMS-5-MODRDR` | PDS Atmospheres | ölçüm | Go/No-Go penceresi, drone hava yoğunluğu |
| Yer gerçeği | PLACES `localized_interp.csv` (YKB'de 385 poz, tilt 0,08–17° [K]); Navcam/Mastcam RDR (CAHV) | JPL PDS, PDS Imaging, Analyst's Notebook | ölçüm | eğim RMSE, POV, alt-metre engel |
| Rota | MMGIS `MSL_waypoints.json` (1.389 nokta, son sol 5073 [D]); PIA23179 "Proposed Path" [K] | mars.nasa.gov | operasyonel | planlanan ve gerçekleşen rota sapması |
| Geometri | NAIF SPICE | NAIF | araç | güneş açısı, ışık süresi |
| Simüle | Gazebo rover/drone sensörleri | — | simüle | yeni deltalar (farklı renk) |

### 3.2 Gerçek olaylar (krizin çekirdeği)

**Sol 4190 — 20 Mayıs 2024 SEP (ana kriz)** [D]
- Dosya: `DATA/SOL_04134_04257/RAD_RDR_2024_140_18_30_4190_V00.TXT`
- E (doku eşdeğeri) dedektörü doz hızı yaklaşık 5,6'dan 351'e çıkar, yani kabaca 60 kat. Yükseliş 10 → 85 → 214 → 316 adımlarıyla olur.
- 93 doz bloğu var; kadans olay öncesi ~17 dk, olay sırasında ~9 dk. Bu, "uyarı süresi" gösterimi için yeterli.
- Arka plan ≈ 5,6 iken %25 alarmı ilk kez 20 Mayıs 2024 **05:21:50 UTC**'de tetiklenir (9,97). Tepe 351,4 **06:15:19 UTC**'de gelir. Gerçek uyarı penceresi ≈ **53 dakika** [D]. Löwe+2025'in "≥30 dk" bulgusuyla tutarlıdır. T_SEP,max = 20 dk varsayımı bu gerçek pencereyle sınanır.
- Rover o sol lat −4,7855, lon 137,409'daydı; boxwork kampanyası başlangıcına yaklaşık 1,5 km.
- NASA'nın verdiği toplam ~8.100 µGy değeri [K]. MAVEN'in aynı olayı gözlemi [?]. MAVEN 2025'te kaybedildi [K]; bu nedenle günümüz senaryosunda röle TGO/MRO/Odyssey olur.

**Sol 242 — 11 Nisan 2013, John Klein (destek sahnesi)** [D]
- B dedektörü: sol 241 ortalaması 9,163 (n=24), %25 eşik 11,454. Sol 242 zirvesi 12,13 (+%32,4).
- E dedektörü zirvesi +%24,1, yani eşiğin altında.
- 18 blok, kadans yaklaşık 1 saat.
- Bağlam: güneş kavuşumu. Dünya'dan komut gidemiyordu; tek uyarı yerel dozimetreydi. "Neden yerel otonom alarm?" sorusunun gerçek cevabı bu.
- Alarm kuralı: Löwe+2025 (arXiv 2502.02469): doz hızı ≥%25 artınca alarm, ≥30 dk uyarı [K, stage 2'de iki üye doğruladı].

**Dürüst çerçeve.** Çizgiyi daraltan doz değil, uçuş kuralıdır: "uyarı süresi ≥ sığınağa varış süresi". RAD soğurulmuş doz (Gy) ölçer, insan etkin dozu (Sv) değil. Ekranda bu yazar. Kariyer limitiyle kıyaslama yalnız açık uyarıyla yapılır (NASA 600 mSv [?]).

### 3.3 Challenge Resources: beşi de işlevsel

| Kaynak | İşlev |
|---|---|
| JPL Mars Trek | DEM, CTX, THEMIS altlıkları; WMTS; katman arama servisi |
| USGS-NASA PGM (sayfada "Non-NASA site") | SIM 3292 birim bağlamı, ölçek merdiveninin ilk basamağı |
| Curiosity's Proposed Path (rota görselleştirme örneği [D, stage 2]) | Rota haritasının tasarım dili + planlanan/gerçekleşen sapma |
| NASA Worldview (yalnız Dünya) | Swipe ve zaman çizelgesi etkileşimi ödünç alınır; isteğe bağlı Dünya analog paneli |
| Perseverance Raw Images | Jezero POV; API alanları `camera_model_component_list`, `mastAz/El` (CAHV) [K] |

### 3.4 Veri disiplini (AGENTS.md ile uyumlu)
- CRS her üründe metadata'dan okunur. Gale eqc R=3.396.190 m, lon_0=0. SIM 3292 Robinson / Mars 2000. Jezero CTX R=3.396.160 [K]. Bounding-box örtüşmesi hizalama kanıtı değildir.
- Numune kökeni ≠ analiz konumu. APXS tablosundaki koordinat rover gövdesinin pozu; John Klein satırı PLACES pozuyla 2 mm içinde eşleşiyor [K]. Haritada iki simge olur: "analiz sırasında rover burada" ve "numune burada".
- Dört statü: arşiv / türetilmiş / simüle / senaryo. Her hücrede ve her kartta görünür.
- Büyük ürünler (Trek DEM 5,78 GB) tam indirilmez. COG/VRT ile pencere okuması yapılır, kırpım provenance'a hash ile yazılır.

---

## 16. Dünya üretimi: kod ve veri setleri

### 16.1 Hat adımları (`redline_data`)

| Adım | Betik (öneri) | Girdi | Çıktı |
|---|---|---|---|
| 1. Katalog | `catalog.py` | ürün listesi (YAML) | ürün ID, URL, sürüm, lisans, hash |
| 2. Pencere okuma | `fetch_window.py` | COG/VRT, AOI poligonu | yerel GeoTIFF'ler (tam indirme yok) |
| 3. CRS kontrolü | `crs_check.py` | ürün etiketi/WKT | rapor: küre, lon_0, datum, nodata; uyumsuzlukta dur |
| 4. Yerel çerçeve | `to_local_enu.py` | eqc rasterlar, saha orijini | ENU ızgara (m), orijin manifestte |
| 5. Türetimler | `derive.py` | DEM, DTM'ler | çok tabanlı eğim (2–5 m), pürüzlülük, σ, viewshed |
| 6. Ufuk küpü | `horizon_cube.py` | DEM | her hücre ve azimut için ufuk yüksekliği; gölge, gökyüzü faktörü ve ufuk eşleştirme bunu kullanır |
| 7. Kaya önseli | `rocks.py` | HiRISE ortho, güneş geometrisi | gölge tabanlı kaya tespiti + Golombek–Rapp uydurması (§18 M2) |
| 8. Senaryo dünyası | `scenario_world.py` | kaya dağılımı, tohum | **gizli gerçek** kayalar (senaryo etiketli), Gazebo + Unreal manifesti |
| 9. Motor paketleri | `export_engines.py` | ENU ızgara, ortho | Gazebo mesh/heightmap + SDF, Unreal 16 bit heightmap + doku + Z ölçeği |
| 10. Ortam | `env_pack.py` | RAD, REMS, SPICE | sol bazlı zaman serileri, güneş az/el tablosu, ışık süresi |
| 11. STAC | `write_stac.py` | hepsi | STAC Collection/Item, statü ve hash |
| 12. QA | `qa_report.py` | hepsi | 3 nokta yükseklik testi, nodata oranı, CRS raporu, görsel kontrol PNG'leri |

Kütüphaneler: GDAL, rasterio, pyproj, numpy/scipy, pystac, SpiceyPy, pvl/pds4_tools. Ayrıca THEMIS `.cub` için ISIS3 veya GDAL ISIS3 sürücüsü.

### 16.2 Bilinen harita ile gizli gerçek ayrımı
- **Gizli gerçek:** dünya dosyasındaki bütün kayalar ve engeller. Gazebo ve Unreal'da ikisinde de aynı konumda durur.
- **Bilinen harita:** yalnız yörünge ürünleri ve sensörle gözlenen parçalar. Planlayıcı ve astronot ekranı yalnız bunu görür.
- Tespit sınırı altı kayalar Golombek–Rapp dağılımından tohumla üretilir ve "senaryo" etiketi taşır. Mars'ta o konumda gerçek kaya olduğu iddia edilmez.
- Dekor kayalar (yalnız görsel) ile navigasyonu etkileyen kayalar ayrı listelerde tutulur.

### 16.3 Gökyüzü, ışık, atmosfer
- Güneş yönü SPICE'tan gelir; Unreal Directional Light ROS'tan gelen az/el ile sürülür. Cesium kullanılırsa onun Dünya güneş bileşeni Mars için kullanılmaz [K].
- SkyAtmosphere Mars renklerine ayarlanır: gündüz karamel, gün batımında mavimsi.
- Toz ve opaklık (tau) seçilen sol için ayarlanır. İsteğe bağlı olarak NASA Ames MGCM çıktısı AmesCAP ile kullanılır [K].
- Gölge takvimi ufuk küpünden çıkar. Güneş 15°'nin altındayken HUD "düşük güneş" uyarısı verir.

### 16.4 Veri setleri özeti
§3.1'deki katmanlar artı şunlar:
- **AI4Mars:** Navcam arazi sınıflandırma etiketleri; rover algısı eğitimi ve karşılaştırması için isteğe bağlı.
- **Mars 2020 Sample Dossier:** Jezero numune kaydı tasarımı için referans.
- **Phoenix WCL:** laboratuvar pH prosedürü için referans; Gale ölçümü değildir.
- **NASA Sounds of Mars:** ambiyans referansı.
