# REDLINE × "Martian Map": NASA gezegen veri bilimcisi merceği

14 Kasım 2026 · Stage 1 yanıtı (opus) · Mercek: PDS/USGS/MRO/MSL ürünleri, gerçek ölçüm ve katmanlar arası veri akışı

**Yöntem.** Resmî challenge sayfası bu oturumda açılamadı (curl: `SEC_E_UNTRUSTED_ROOT`, WebFetch: "unable to get local issuer certificate"). Metni ve Resources listesini yerel organizatör kopyasından okudum: <https://hackathlone.com/challenges/interplanetary-survival-guide-martian-map>. Aşağıdaki sayıların çoğunu canlı arşivlere salt-okunur sorgularla kontrol ettim. Dosyaları diske indirmedim, bellekte okudum. Sorgulanan kaynaklar: PDS PPI (RAD), JPL PDS (PLACES), USGS Astrogeology STAC, Mars Trek arama/WMTS servisi, USGS SIM 3292 ArcGIS feature service, mars.nasa.gov raw-images/REMS/MMGIS JSON'ları, Grotzinger+2014 ve Dehouck+2017 metinleri. Doğrulayamadıklarımı §4'te listeledim.

---

## 0. Tez

Yellowknife Bay (YKB) rastgele seçilmiş bir saha değil. Burası NASA'nın 2012'de **yörünge katmanlarıyla (HiRISE morfolojisi + termal atalet) hedef seçtiği ve yerde doğruladığı** yer. Ayrıca Curiosity RAD, 2013 Nisan'ında **tam bu noktada, güneş kavuşumu sırasında** gerçek bir SEP ölçtü. Dolayısıyla REDLINE'ın iki en dramatik parçası, yani "önce/sonra" deneyi ve "SEP krizi", simülasyon olmak zorunda değil. İkisi de gerçek arşivle yeniden oynatılabilir. Simülasyonu, arşivin bittiği yere bırakmak gerekir: yeni robot gözlemi, yeni rota ve ileri saha. REDLINE'ı jüri gözünde güçlendirecek en büyük kaldıraç bu ayrım.

---

## 1. Challenge'ın gerçek istekleri ve mevcut fikrin karşılaması

Alıntılar yerel organizatör kopyasından alındı ve kısa tutuldu. Değerlendirme ölçeği: **İyi**, **Kısmen**, **Zayıf**, **Yok**.

| # | İstek (alıntı) | Bölüm | REDLINE bugün | Neden |
|---|---|---|---|---|
| C1 | "create a layered, integrated view of a location or route on the Martian surface" ve "pulls together data from multiple NASA science missions" | Summary | Kısmen | MRO ve MSL var, ancak katalogdaki D01–D16'nın çoğu "aday" durumda. Tek üründe birden fazla görev kökeni bulunması (Gale DEM: HiRISE/CTX/HRSC/MOLA) bağımsız katman kullanımıyla aynı şey değil. |
| C2 | "help a human explorer plan and carry out a successful Marswalk while conducting new and exciting science" | Summary | Kısmen | Plan ve prova güçlü. Ancak YKB'de **yeni** bir bilim sorusu tanımlı değil; Sheepbed zaten yorumlanmış. |
| C3 | "updates on current conditions" | Summary | Zayıf | REMS ve RAD "aday" durumda. Veri yaşı gösterimi tasarlanmış ama besleyen bir kaynak yok. |
| C4 | "create a map, tool, or interface a Mars astronaut could use during a surface exploration mission" | Objectives | İyi | Unreal provası, tablet ve HUD bu isteği karşılıyor. Risk: robot simülasyonunun haritayı gölgelemesi. |
| C5 | "identifying some scientific goals for your mission and the location" ve "boxwork formations" örneği | Objectives | Kısmen | Saha seçildi, bilim hedefi eski. Challenge'ın kendi örneği olan boxwork ile bağ yok. |
| C6 | Belgeli saha ya da "an area that hasn't been studied as closely" | Objectives | İyi | YKB çok iyi belgelenmiş bir saha. |
| C7 | "You may consider including at least three kinds of data": optical, thermal, spectral, topographic, geophysical, atmospheric, radiation, chemical | Objectives | Kısmen | Kâğıt üzerinde beş tür var. Uygulamada termal ve spektral katman yok, radyasyon ise sentetik. |
| C8 | "NASA's first priority is always astronaut safety", "you might include space weather data", "avoiding significant obstacles such as large rock formations", spacesuit "Consider how this might impact their mobility", "possibly carrying scientific equipment" | Objectives | Kavram iyi, veri zayıf | REDLINE çizgisi tam bu isteğe hizmet ediyor. Ama SEP, engeller ve eğim kısıtı şu an varsayıma dayalı. |
| C9 | "display used inside the crew's spacecraft or habitat", "tablet application", "heads-up-display (HUD)" | Considerations | İyi | Unreal üç biçimi de gösterebilir. |
| C10 | "a static snapshot, an interactive digital product, or a tool or system that generates maps" | Considerations | Kısmen | Manifest fikri bu isteğe denk düşüyor ama henüz kanıtlanmadı. |
| C11 | "Look at how NASA missions to destinations other than Mars—Earth, the Moon, other planets" | Considerations | Yok | Fikirde bu bağ hiç kurulmamış. |
| C12 | Geçmiş dönem, "predicted data and conditions for a future time frame, or no specified time frame at all" | Considerations | Zayıf | Senaryonun zamanı (hangi sol, hangi tarih) tanımlı değil. |
| C13 | "Try looking at imagery taken by NASA's Mars surface missions" | Considerations | Zayıf | Navcam yalnız aday olarak geçiyor. |
| C14 | "might use rovers or other robotic systems to help transport the crew and their tools", "the astronauts might work in pairs" | Considerations | Kısmen | Robotlar keşif yapıyor, ancak taşıma ya da hareketli sığınak rolü yok. Çift astronot da yok. |
| C15 | Mars Trek ve USGS PGM "built for regional and global views rather than the hyperlocalized areas astronauts will target" | Background | Kısmen | Fikrin özü bu boşluk, ama ekranda sayıyla kanıtlanmıyor. |
| C16 | **Resources (5 madde):** JPL Mars Trek; USGS-NASA Planetary Geologic Mapping Program (sayfada "Non-NASA site"); Curiosity's Proposed Path up Mount Sharp; NASA Worldview; Mars Perseverance Raw Images | Resources | **Yok** | Kataloğun hiçbir satırı bu beş kaynağı işlevsel olarak kullanmıyor. **Bu, en büyük uyum açığı.** |

**Jüri ölçütleri.** Space Apps project submission guide değerlendirmenin beş ölçütle yapıldığını söylüyor: Impact, Creativity, Validity, Relevance, Presentation (<https://www.spaceappschallenge.org/resources/project-submission-guide/>). Bir takvim kaydına göre 2026 Judging & Awards Guide 13 Kasım 2026'da yayımlandı, ancak metnini okuyamadım. Aşağıdaki eşleştirmeler bu beş ölçüte göre yapıldı.

---

## 2. En değerli eklentiler (öncelik sırasıyla)

### E1. SEP krizini gerçek RAD ölçümüyle oynat: sol 242, John Klein, Yellowknife Bay

**Ne.** Demo krizini (fikir 8) kurgusal bir SEP yerine Curiosity RAD'ın aynı sahada ölçtüğü gerçek olay tetikler. Akış şöyle:

1. RAD RDR'den sol 241–243 doz hızı okunur.
2. Önceki solün ortalamasından arka plan hesaplanır.
3. Löwe ve ark. (2025) kuralı uygulanır: doz hızı arka planı en az %25 aşınca alarm verilir.
4. REDLINE çizgisi, "sığınağa varış süresi ≤ uyarı süresi" isokronuna daralır.

**Doğruladığım ölçüm değerleri.** Değerler PDS PPI'daki ASCII dosyadan okundu.

- **B dedektörü.** Sol 241 ortalaması 9,163 (24 blok), dolayısıyla eşik 11,454. Sol 242 serisi: 9,28 → 8,90 → 9,54 → 10,73 → **12,13** → 11,55 → 11,07 → … → 9,27. Zirve arka planın %32,4 üstünde ve **4. ile 5. bloklar eşiği aşıyor**.
- **E dedektörü (doku eşdeğeri plastik).** Zirve %24,1'de kalıyor, eşiği aşmıyor. Yani "hangi dedektör, hangi eşik" sorusu ekranda gösterilmeye değer, gerçek bir parametre.
- **Hassler ve ark. (2014, Science 343).** "one hard SEP event on sol 242", "~30% over the GCR dose rate", olay dozu "50 μGy". Ortalama GCR doz hızı 0,210 ± 0,040 mGy/gün. Doz hızı atmosfer basıncıyla ters ilişkili ("anticorrelation"). B arka planı ×24 yaklaşık 220 µGy/gün ediyor ve bu değerle tutarlı.
- **Bağlam.** İlk güneş kavuşumu sol 236'da başladı ve Curiosity John Klein'da park halindeydi. PLACES'ta sol 236–270 arasında hiç rover pozu yok; sürüş olmadığıyla tutarlı. Bu dönemde Dünya'dan komut gitmiyordu. Bu, fikir 7'deki yerel otonom alarm için gerçek bir gerekçe.
- **Löwe ve ark. (2025, arXiv 2502.02469).** Eşik "at least 25%", uyarı süresi "at least 30 minutes", yanlış alarm "near-zero". Yüzeyde 16 SEP olayı inceleniyor.
- **Aynı gün REMS (mars.nasa.gov JSON).** Sol 242 / 2013-04-11: hava −70/−7 °C, 881 Pa, zemin −72/+6 °C, UV "Very_High".

**Dürüstlük çerçevesi.** Bu olay insan için düşük doz düzeyinde. Bu yüzden iki çizgi gösterilmeli. Birincisi, **gerçek olayın protokolü tetiklediği** çizgi. İkincisi, ayrı renkte ve "karşı-olgusal ×k" etiketiyle, doz bütçesini zorlayan senaryo çizgisi.

**Veri.**

- PDS PPI `MSL-M-RAD-3-RDR-V1.0`, `DATA/SOL_00180_00269/RAD_RDR_2013_101_07_02_0242_V00.TXT` (ASCII + PDS3 LBL). Kullanılan bloklar: `DOSIMETRY_TOTAL_DOSE_B` ve `_E`. RDR SIS birimi tutarsız yazıyor; µGy/h olarak okunduğunda değerler Hassler ile uyuşuyor.
- REMS için arşiv kaynağı PDS Atmospheres `MSL-M-REMS-5-MODRDR` ailesi. mars.nasa.gov `rss/api/?feed=weather&category=msl` JSON'u halka yönelik bir özet, arşiv ürünü değil.
- **Statü:** gerçek ölçüm.

**Hizmet ettiği maddeler.** C8 (space weather), C3, C12 (geçmiş zaman dilimi), C14 ve fikir 7. Jüri ölçütleri: **Validity** (aynı yer, aynı zaman, gerçek ölçüm), **Impact** ("Dünya kör, yerel dozimetre uyarır" tezi), **Presentation**.

**Jüride.** Kriz anında ekranın altında gerçek RAD eğrisi akar. Eşik çizgisi görünür, "blok 5: +%32 → ALARM" yazar ve REDLINE çizgisi daralır. Köşede "PDS PPI · sol 242 · ölçüm" rozeti, yanında ayrı renkte karşı-olgusal senaryo durur.

### E2. "Yörünge ne dedi, yer ne buldu": YKB'de geriye dönük doğrulama

Bu, önce/sonra deneyinin gerçek veri ayağı.

**Ne.** 2012 kararı yeniden üretilir. REDLINE yalnız yörünge katmanlarıyla (HiRISE ortho/DTM, THEMIS termal atalet, CRISM) bir hedef ve rota önerir. Öneri, Curiosity'nin gerçekte gittiği yer (PLACES) ve bulduğu şeylerle (APXS/CheMin) karşılaştırılır.

**Kanıt (Grotzinger ve ark. 2014, Science 343, 1242777).**

- Ekip inişten sonra "drive in the opposite direction of the Mt. Sharp entry point to sample stratified rocks of relatively high thermal inertia exposed at Yellowknife Bay" kararı verdi.
- Ekip haritası "six units … distinguished based on variations in thermal inertia" içeriyor ve "constructed based largely on HiRISE image data".
- Makale ayrıca şunu söylüyor: "One of these terrains (BF) very closely coincides with higher values of thermal inertia".

Bu, challenge'ın istediği "katmanlı haritayla hedef seçimi"nin NASA'daki gerçek örneği ve tam REDLINE sahasında.

**Kaçırılan bilgi (en değerli ders).** Dehouck ve ark. (EGU2017-14867) şunu yazıyor: "due to dust cover, this location lacks any signature of clay minerals in orbital VNIR observations". Oysa CheMin yaklaşık %20 smektit buldu. John Klein CheMin label'ı ön analizde kili "~22 +/- 11 weight%", amorf malzemeyi "~28 +/- 15 weight%" olarak veriyor.

**Çıktı.** Katman bazında bir isabet/kaçırma karnesi:

| Katman | Sonuç |
|---|---|
| Termal atalet → pekişmiş kayaç | isabet |
| HiRISE → kırıklı, açık tonlu katman | isabet |
| CRISM → kil | kaçırma (toz örtüsü) |
| DTM eğimi → rover ölçümü | E4'te nicel olarak |

**Veri.**

- THEMIS `THEMIS_TI_Mosaic_Quant_30S120E_100mpp.cub`: USGS Astropedia S3, ISIS3, 32 bit, 100 m. Fergason ve ark. 2012'ye göre doğruluk ~%20, hassasiyet %10–15. Statü: ölçümden türetilmiş.
- HiRISE `PSP_010573_1755_RED` v2.0: 0,25 m, 2008-10-28, JP2 + PDS3 LBL. Statü: ölçüm.
- CRISM: nicel analiz için PDS Geosciences ve ODE üzerinden MTRDR (tekil gözlem ID'sini doğrulamadım). Trek'teki `frt_07_br*_mtr3_ll` browse mozaikleri yalnız nitel katman olarak kullanılmalı.
- APXS supplement CSV ve CheMin RDR CSV'leri. Statü: ölçüm veya ölçümden türetilmiş.

**Hizmet ettiği maddeler.** C5, C7 (termal ve spektral katmanlar gerçekten devreye girer), C15. Jüri ölçütleri: **Validity**, **Creativity** (aracını tarihî bir NASA kararıyla sınayan takım az bulunur).

**Jüride.** Bölünmüş ekran. Solda "sol 0: yalnız yörünge" önerisi, sağda Curiosity'nin gerçek izi ve bulguları, altta karne. Ana mesaj: "Haritamız kili göremezdi ve bunu biliyordu."

### E3. Resources listesindeki beş kaynağın her birine somut işlev

Bu madde doğrudan **Relevance** ölçütünü taşıyor.

| Kaynak | REDLINE'daki işlevi | Doğruladığım ürün/erişim |
|---|---|---|
| **Mars Trek** | "Ölçek merdiveni"nin ilk basamakları, tablet altlığı, manifestin otomatik doldurulması, insanlı keşif bölgesi bağlamı | `Gale_DEM_SMG_1m` ("MRO HiRISE, Gale Crater DEM", 5,78 GB). Kapsamı lon 137,12–137,73, lat −4,93…−4,25; **YKB'yi ve boxwork'ü birlikte kapsıyor.** Ayrıca `Gale_CTX_BlockAdj_dd`, `curiosity_hirise_mosaic`, `curiosity_ctx_mosaic`, `EZMars` ("Exploration Zones (NASA EMC)"), THEMIS Day/Night controlled 100 m. WMTS: `trek.nasa.gov/tiles/Mars/EQ/<katman>/1.0.0/WMTSCapabilities.xml` (iki katman için HTTP 200). Arama: `trek.nasa.gov/mars/TrekServices/ws/index/eq/searchItems?key=Gale`. Statü: ölçüm ve türetilmiş. |
| **USGS PGM** | Bölgesel birim bağlamı ve "boşluğun sayısı" | SIM 3292 (Tanaka ve ark. 2014, 1:20M) feature service sorgusu: YKB **`AHi`** birimine düşüyor ("Amazonian and Hesperian impact unit"), **tek poligon 87.031 km²**. Boxwork **`Htu`** birimine düşüyor (4.455 km²), açıklamasında "Includes hydrated sulfate spectral signatures". Gale için ayrı bir PGM SIM bulamadım. REDLINE'ın EVA ölçekli eskiz haritası, PGM'in sembol ve kontak kesinliği uzlaşımlarını (kesin / yaklaşık / çıkarım) kullanarak bu boşluğu doldurmalı. Jezero için SIM 3464 (Sun & Stack 2020, 1:75.000, CTX 6 m tabanlı): `services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/Jezero_FeatureServiceFromPro/FeatureServer`. Statü: yorumlanmış/türetilmiş. |
| **Curiosity's Proposed Path** | (a) Açıklamalı rota ve flyover tasarım dili; (b) planlanan ve gerçekleşen rotanın karşılaştırması | PIA23179, 15 Mayıs 2019, HiRISE, CRISM, CTX ve HRSC'den üretilmiş. Gerçekleşen rota: MMGIS `mmgis-maps/MSL/Layers/json/MSL_waypoints.json`, 1.389 nokta, son kayıt sol 5073. 2019 planı GCP'lerle georeferanslanır (statü: türetilmiş), MMGIS rotası ise operasyonel konum verisi. Sapma metriği şunu gösterir: NASA planları da "canlı harita" ile güncelleniyor. |
| **Worldview** | Mars'ta bir Worldview yok. REDLINE onun **A/B karşılaştırma (swipe/opacity/spy)** ve zaman çizelgesi etkileşimini ödünç alır. | (a) Yalnız-yörünge haritası ile yörünge+robot haritasının karşılaştırması. (b) HiRISE zaman serisi: USGS STAC'ta YKB üzerinde 40 HiRISE gözlemi var (2008→2025). Örnekler: `ESP_029957_1755` (2012-12-16), `ESP_030313_1755` (2013-01-13), `ESP_032436_1755` (2013-06-27, HiRISE'ın "Curiosity Rover in Yellowknife Bay" görüntüsü). Bunlarla yörüngeden rover ve izleri görülebilir. (c) İsteğe bağlı: GIBS WMTS üzerinden bir Dünya analog sahası (C11). |
| **Perseverance Raw Images** | İkinci saha (Jezero) manifest testi, "veri yaşı" gösterimi, görüntünün yere izdüşümü | API: `mars.nasa.gov/rss/api/?feed=raw_images&category=mars2020&feedtype=json`. Alanlar: `sol`, `site`, `drive`, `attitude`, `camera.camera_model_type: CAHV`, `camera_model_component_list`, `mastAz/mastEl`, `date_taken_utc/mars`. En son kayıt sol 2031 (2026-11-06). CAHV modeli, MMGIS M20 poz verisiyle (708 nokta, son sol 2022) birleşince görüntü ayak izi DEM'e izdüşürülebilir ve "yerden görülmüş hücre" katmanı elde edilir. Statü: ölçüm (ham/browse; kalibre değil). |

**Jüride.** Tek bir "ölçek merdiveni" animasyonu: SIM 3292 poligonu (87.031 km²) → Trek CTX → Trek HiRISE DEM (1 m) → robotla güncellenen REDLINE hücresi. Ana mesaj: "Mars Trek ve USGS haritalarının durduğu yerden başlıyoruz." Bu, Background'daki C15 boşluğunu sayıyla gösterir.

### E4. Güven katmanını ölçülebilir yap: belirsizlik veriden gelsin, elle verilmesin

**Ne.** Her hücrenin "güven" değeri ürünlerin kendi hata bilgisinden ve bağımsız ölçümlerden hesaplanır. Kaynaklar şunlar:

- **Üç bağımsız HiRISE DTM YKB'yi kapsıyor:** `DTEEC_010573_1755_010639_1755_U01`, `DTEEC_018854_1755_018920_1755_U01`, `DTEEC_023957_1755_024023_1755_U01`. Kaynak USGS STAC `mro_hirise_socet_dtms` (`stac.astrogeology.usgs.gov/api`). Biçim: COG, **Float32**, CC0. CRS: "Mars (2015) – Sphere / Ocentric / Equirectangular, clon = 0", R = 3.396.190 m, nodata −3,4e38. DTM'ler arasındaki yükseklik ve eğim farkı, **ampirik dikey belirsizlik ve eğim belirsizliği haritası** verir.
- **CTX controlled DTM'ler** (`mro_ctx_controlled_usgs_dtms`, 20 m). Her item bir `intersection_error` varlığı taşıyor; bu, ürünün kendi stereo kesişim hatası.
- **Rover ölçümüyle doğrulama.** PLACES `localized_interp.csv` (v42) satırlarında `roll/pitch/yaw` var. YKB kampanyası (sol 120–299) için 385 ROVER pozu, 22 sol, site 5–6. Eğim (tilt) 0,08–17,06°, ortalama 4,8°. DTM'den rover ayak izi ölçeğinde (~3 m) türetilen eğim bununla karşılaştırılır. Sonuç, eğim katmanının gerçek hata dağılımı (RMSE) olur ve giysi eğim kısıtının marjı buna göre ayarlanır.
- **Diğer hata kaynakları.** THEMIS termal ataleti için ±%20 doğruluk. APXS CSV'de her oksit için `_error` sütunu, CheMin RDR'de 2σ hata sütunu var. Numune kartlarında hata çubuğu bunlardan çizilir.
- **Tespit sınırı.** HiRISE 0,25 m/piksel. "En az ~3 piksel" kuralıyla yaklaşık 0,75–1 m altındaki kayalar yörüngeden görünmez. Bu bir kural, ürün özelliği değil. Sonuç: hücre "tehlikeli boyutta kaya: bilinmiyor" diye boyanır. Robot keşfinin değeri tam olarak burada ortaya çıkar.

**Hücre şeması.** `value, unit, product_id (PDS LIDVID / STAC id), GSD, acq_time, processing_level (raw/calibrated/derived), σ ve kaynağı, state ∈ {tespit var | tespit yok (duyarlılık sınırlı) | gözlenmedi}, provenance ∈ {arşiv | türetilmiş | simüle | senaryo}`.

**Veri QA dersi.** Bu DTM'nin `provenance.txt` dosyası COG dönüşümünü `-ot UInt16` ile yapıldığını yazıyor. Oysa dosya başlığı SampleFormat = 3 (Float32) diyor. Ders: metadata metnine değil, dosyanın kendisine güvenmek. Bu, bir "veri QA" ekranında gösterilebilir.

**Hizmet ettiği maddeler.** C8 (engeller ve eğim), C7, C15. Jüri ölçütü: **Validity**.

**Jüride.** Hücreye tıklanınca şöyle bir kart açılır: "eğim 11,2° ± σ (3 DTM farkı) · rover tilt'ine göre RMSE … · kaynak DTEEC_… · tespit sınırı ~0,75 m · durum: kaya bilinmiyor". Buradaki sayılar örnek; hesaplanmadı.

### E5. Robot deltalarını Curiosity'nin gerçek ölçümlerine çapala ve numune geometrisini doğru kur

**Ne.** "Rover doğrular" adımında önce Curiosity'nin gerçekten ölçtükleri gösterilir:

- PLACES pozları;
- Navcam, Mastcam ve MAHLI görüntüleri;
- ChemCam LIBS, APXS, CheMin ve DAN ölçümleri. DAN, Roscosmos'un cihazıdır; etikette bu belirtilmeli.

PDS Geosciences'ta MSL Release 42 (3 Ağustos 2026) DAN ve ChemCam RDR'lerini sol 4843'e kadar içeriyor. Simüle edilen Gazebo rover'ı ve drone yalnız **yeni** deltaları ekler ve bunlar farklı renk ile etiket taşır.

**Kritik veri semantiği bulgusu (doğruladım).**

- APXS supplement'taki **John Klein satırının lat/lon/elev değeri, PLACES'taki rover pozuyla 2 mm içinde aynı** (site 6, drive 0, sol 166). **Cumberland satırı** da site 6, drive 74–82 (sol 274) rover pozuyla aynı.
- Easting değeri tam olarak boylam(rad) × 3.396.190 m.
- Yani tablodaki koordinat **rover gövdesinin konumu**, ne hedefin ne de deliğin konumu. NASA iki deliği yaklaşık 2,75 m ayrı veriyor, tablo ise yaklaşık 1 m fark gösteriyor.
- Hedef konumu, cihaz hedef XYZ'si (site frame) ile rover pozu birleştirilerek hesaplanmalı (Analyst's Notebook ve ürün label'ları). Haritada iki ayrı simge olmalı: "analiz sırasında rover burada", "numune burada".

Bu, AGENTS.md'deki "sample origin ≠ analysis location" ilkesinin canlı ve doğrulanmış bir örneği.

**Yörüngenin robotu görmesi.** `ESP_030313_1755` ve `ESP_032436_1755` görüntüleri, yörünge ile yer arasında konum çapraz kontrolü sağlar. "Drone tarar, rover doğrular" zincirinin tarihî ve gerçek bir karşılığı.

**Hizmet ettiği maddeler.** C1 (MRO, Odyssey ve MSL birlikte), C13. Jüri ölçütleri: **Validity**, **Creativity**.

### E6. "Yeni bilim" için ileri saha: boxwork-Batı

Boxwork challenge'ın kendi örneği. YKB bu kurguda kalibrasyon sahası olarak kalır.

**Ne.** YKB, haritanın karnesini çıkardığı **doğrulama sahası** olur. **Boxwork-Batı** ise insanın katkı sağladığı **ileri EVA sahası** olur.

**Kampanyanın konumu** (MMGIS MSL waypoint'leri):

- Sol 4534–4805.
- Enlem −4,798…−4,809, boylam 137,379–137,386.
- Yükseklik −3.658…−3.605 m, yani YKB'nin yaklaşık 900 m üstü.

**NASA'nın bulguları.** Sırtlar 10–20 km uzanıyor. Sırtlarda kil, çukurlarda karbonat bulundu. Bölge sülfatlı bir birim içinde ve rover alandan yaklaşık Mart 2026'da ayrıldı.

**Veri hazır mı? Büyük ölçüde evet:**

- PDS Release 42: DAN ve ChemCam sol 4843'e kadar.
- RAD RDR dizinleri `SOL_04710_04843`'e kadar.
- Trek `Gale_DEM_SMG_1m` bu alanı kapsıyor.
- STAC'ta iki HiRISE DTM var: `DTEEC_019698_1750_019988_1750_U01` ve `DTEEC_009149_1750_009294_1750_U01`.
- STAC'ta 52 HiRISE gözlemi var; en sonuncusu `ESP_087149_1750` (2025-02-28).
- SIM 3292'de birim `Htu`.
- Boxwork için APXS ve CheMin sürümlerini doğrulamadım.

**Bilim sorusu.** Doğu kenarında görülen sırt/çukur mineraloji farkı batıda da geçerli mi? Eşleştirilmiş sırt–çukur istasyonlarıyla sınanır. Robotun aylar süren örneklemesini insan birkaç EVA'da yapabilir. Bu, Background'daki "human explorers are able to conduct science … that robotic systems cannot" vurgusunun somut karşılığı.

**Manifest testi.** Aynı gezegen, aynı CRS ve aynı Trek DEM kullanılıyor. Böylece manifest için "ikinci saha" testi hiçbir dönüşüm riski olmadan yapılır.

**Hizmet ettiği maddeler.** C2, C5, C6. Jüri ölçütleri: **Relevance**, **Impact**, **Creativity**.

**Jüride.** "YKB'deki karnemiz bu. Aynı katman yığınıyla boxwork-Batı EVA'sını öneriyoruz. Belirsizliğin en yüksek olduğu hücre burası, robotu oraya gönderiyoruz."

### E7. Varış önizlemesi: aynı pozdan gerçek yüzey görüntüsü ve Unreal render

**Ne.** Her bilim durağında astronota "varınca ne göreceği" gerçek Navcam/Mastcam görüntüsüyle gösterilir. Unreal'da aynı kamera pozundan bir render alınır ve yan yana konur. Poz, CAHV/CAHVORE kamera modeli ile PLACES pozundan gelir. Fark görüntüsü iki şey sağlar:

- DTM'den kurulan arazinin görsel doğrulaması;
- DEM'de görünmeyen alt-metre kayaların gösterimi (E4'teki tespit sınırını görünür kılar).

**Veri.** MSL Navcam RDR (PDS Imaging; kamera modeli label'da) ve Analyst's Notebook. Jezero için raw API'deki `camera_model_component_list`. Statü: gerçek ölçüm.

**Hizmet ettiği maddeler.** C13 (doğrudan), C4. Jüri ölçütleri: **Presentation**, **Validity**.

### E8. Manifesti gerçek ikinci saha ve eksik katman beyanıyla kanıtla (Jezero; isteğe bağlı Ay)

**Manifest biçimi.** Manifest bir STAC Item/Collection olarak tutulur ve USGS Astrogeology STAC ile aynı `proj:wkt2`/`proj:projjson` alanlarını kullanır. REDLINE kendi deltalarını da STAC Item olarak yazar. Böylece canlı harita standart bir katalog olarak yayımlanabilir.

**Jezero katmanları (Trek'te doğrulandı):**

- `JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first_dd`
- `JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40`
- `JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0`
- `Perseverance_Traverse_Path`. Kapsam kutusu eski görünüyor; güncel konum için MMGIS M20 kullanılmalı.

Bunlara SIM 3464 feature service ve Perseverance raw images eklenir.

**Eksik katman beyanı.** Perseverance'ta RAD benzeri bir iyonlaştırıcı radyasyon dozimetresi yok. Jezero'da radyasyon katmanı bu yüzden "ölçüm yok; Gale RAD'dan taşınmış/model" rozetiyle gösterilmeli. Atmosfer için MEDA kullanılır (`urn:nasa:pds:mars2020_meda:data_calibrated_env`). Bu, "harita neyi bilmediğini bilir" ilkesinin sahalar arası sürümü.

**CRS.** Yerel araştırma notuna göre Jezero CTX metadata'sında küre yarıçapı 3.396.160 m, Gale ürünlerinde 3.396.190 m. SIM 3292 servisi ise Robinson izdüşümünde, Mars 2000 küresi üzerinde. Manifest bu yüzden CRS'i **ürün başına** taşımalı.

**İsteğe bağlı (C11).** Aynı Trek altyapısının bir Moon Trek karşılığı var (servis yolunu doğrulamadım). Ay'ı yüklemek "NASA başka hedefleri nasıl haritalıyor" sorusuna somut bir cevap olur.

**Hizmet ettiği maddeler.** C10, C11, C16. Jüri ölçütleri: **Impact**, **Creativity**.

### E9. "Güncel durum" paneli ve veri yaşı

**Ne.** Summary'deki "updates on current conditions" isteğine doğrudan cevap. Panel, her kaynağın en son kaydını yaşıyla birlikte gösterir. Bu oturumda gördüğüm son kayıtlar:

| Kaynak | Son kayıt |
|---|---|
| MSL MMGIS konumu | sol 5073 |
| REMS günlük özeti | sol 4995, 2026-08-25 |
| Perseverance son görüntüsü | sol 2031, 2026-11-06 |
| PDS arşiv sınırı | MSL Release 42, sol 4843 |

Kullanıcı panelde "operasyonel/halka yönelik akış" ile "arşivlenmiş PDS ürünü" ayrımını görür. 2013 senaryosu oynatılırken panel aynı alanları sol 242 değerleriyle doldurur (E1).

**Hizmet ettiği maddeler.** C3, C12. Jüri ölçütleri: **Relevance**, **Presentation**.

### E10. REDLINE çizgisini iki astronot ve hareketli rover sığınağıyla hesapla

**Ne.** Challenge'ın "transport the crew and their tools" ve "work in pairs" önerilerine karşılık gelir.

- Çizgi = min(EV1 dönüş payı, EV2 dönüş payı).
- Rover hareketli bir sığınak olduğu için isokron, rover'ın rotasıyla birlikte değişir.
- DEM görüş hattı (viewshed) ile rover ve telsiz görünürlüğü katmanı üretilir; bu katman gerçek DEM'den türetilir.
- Giysi parametreleri senaryo varsayımıdır ve öyle etiketlenir. Eğim ve mesafe gerçek DEM'den gelir.

**Hizmet ettiği maddeler.** C14, C8. Jüri ölçütleri: **Relevance**, **Impact**.

### Katmanlar birbirini nasıl besler

```
[Yörünge önseli: ölçüm/türetilmiş]
 HiRISE RDR 0,25 m ───────────────┐
 HiRISE DTM ×3 (1 m) ─┬─► eğim, pürüzlülük, viewshed, ampirik σ ─┐
 CTX DTM + intersection_error ┘                                   │
 THEMIS TI 100 m (±%20) ─► pekişmiş kayaç / kum önseli ───────────┼─► geçilebilirlik + bilim önseli
 CRISM MTRDR ─► mineral önseli {tespit | tespit yok* | gözlenmedi}┘     (türetilmiş)
 SIM 3292 / SIM 3464 ─► bölgesel birim bağlamı                            │
                                                                         ▼
[Ortam: ölçülmüş zaman serisi]                         REDLINE planı: rota, duraklar, dönüş isokronu
 RAD RDR doz hızı ─► SEP alarmı (≥ +%25) ──┐                             │
 REMS basınç/T/UV ─► kolon ve termal ──────┴─► zaman kısıtı ──────────────┤
                                                                         ▼
[Yer gerçeği: ölçüm]                                     DELTA kayıtları (arşiv | simüle | senaryo)
 PLACES poz + tilt ─► eğim RMSE ─► σ güncellemesi                         │
 Navcam/Mastcam (CAHV) ─► görülmüş hücre, alt-metre engel                 │
 APXS/CheMin/ChemCam/DAN ─► numune kartı (köken ≠ analiz konumu)          │
[Simüle: etiketli]                                                        ▼
 Gazebo rover/drone sensörleri ─► yeni gözlem ─────► posterior harita ─► plan güncellemesi
 (*) tespit yok = duyarlılık sınırlı; örnek: YKB'de toz yüzünden CRISM kili göremedi
```

---

## 3. Değiştirilmesi veya yeniden çerçevelenmesi gerekenler

1. **"Önce/sonra deneyi" iki katmanlı kanıta dönüşmeli.** Birincil kanıt, YKB'deki gerçek retrospektif karşılaştırma olmalı (E2). Monte Carlo yalnız bir duyarlılık analizi olarak kalmalı ve sonuçları "simüle dünyalarda" etiketiyle sunulmalı. Simüle dünyalardan çıkan "%X daha güvenli" gibi bir sonuç, NASA verisinin katkısı gibi gösterilmemeli. "Rotadaki bilinmeyen oranı" ve "eğim σ" gibi metrikler gerçek ürünlerden hesaplanabilir; bunlar öne çıkmalı.

2. **SEP krizi "dramatik ölüm tehdidi" olarak değil, "protokolü tetikleyen gerçek olay" olarak anlatılmalı.** Sol 242 olayı yüzeyde ~%30'luk bir artış ve ~50 µGy'lik olay dozu demek. REDLINE çizgisi dozun kendisi yüzünden değil, "uyarı süresi ≥ sığınağa varış süresi" kuralı yüzünden daralır. Bu çerçeve Löwe ve ark. (2025) ile tutarlı. Daha ağır bir olay gösterilecekse ayrı ve ölçekli bir karşı-olgusal çizgi kullanılmalı.

3. **"Rover beklenmedik kaya bulur" yerine "rover, yörüngenin tespit sınırının altını çözer" denmeli.** 0,75–1 m altındaki kaya bir sürpriz değil, öngörülebilir bir bilinmezlik. Güven katmanı bu alanları baştan "gözlenmedi / tespit sınırı altı" diye boyamalı. Robotun değeri, bu hücrelerin kaç tanesini çözdüğüyle ölçülür. Rota değişikliği kanıta bağlı olmalı; her bulgu rotayı değiştirmez.

4. **Güven katmanı üç durumlu bir semantik kullanmalı ve iki ayrımı korumalı.** Durumlar: tespit var / tespit yok (duyarlılık sınırlı) / gözlenmedi. Korunacak iki ayrım:
   - **Statü:** arşiv / türetilmiş / simüle / senaryo.
   - **Konum anlamı:** "ölçüm sırasında rover burada" ile "numune burada" farklı şeylerdir. APXS koordinatının rover pozu çıkması bunun canlı kanıtı (E5).

5. **"Gezegenden bağımsız manifest" yerine "gövde-açık manifest" denmeli.** CRS ürün başına beyan edilmeli: STAC eqc / R 3.396.190, SIM 3292 Robinson / Mars 2000 küresi, Jezero CTX 3.396.160. Eksik ölçüm türleri de beyan edilmeli (Jezero'da RAD yok). Ek olarak eski beş görev (vana/kaçak, eğitim/sınav dahil) jüri anlatısında harita çekirdeğine bağlanmalı. Her görev için iki soru net cevaplanmalı: hangi katmanı okuyor, hangi deltayı yazıyor? Bu bağ gösterilemiyorsa o görev sunumda ikincil kalmalı. Bu bir kapsam kesme önerisi değil, sunumdaki sıralamayla ilgili.

---

## 4. Doğrulayamadığım iddialar

- **Resmî challenge sayfası** açılamadı (SSL "untrusted root"). Yerel kopya ile resmî metin arasında fark olabilir; nihai kaynak resmî sayfadır.
- **2026 Judging & Awards Guide metni.** Beş ölçütün adı submission guide'dan geliyor; ağırlıklar ve tanımlar okunmadı.
- **Sol 242 SEP'inin kaynağı.** 11 Nisan 2013'teki M6.5 parlama/CME ile ilişkisini ve DONKI kaydını doğrulayamadım; `kauai.ccmc.gsfc.nasa.gov` bağlantısı zaman aşımına uğradı. Hassler makalesinde de tarih farkı var: bir yerde "12 to 13 April", başka yerde "11 to 12 April" yazıyor.
- **RAD ayrıntıları.** Blokların UTC zamanlarını çıkarmadım. Sol 242'de neden 24 yerine 18 blok olduğunu bilmiyorum. Birimin µGy/h olduğu yalnız Hassler ile tutarlılıktan çıkarıldı; SIS bu konuda tutarsız yazıyor.
- **Kavuşum sırasında rover'ın tam yeri.** "John Klein'da park" bilgisi ikincil kaynaklardan (blog, Planetary Society, Space.com) geliyor. PLACES'ta sol 236–270 arasında satır yok.
- **CRISM.** YKB ve boxwork için tekil MTRDR gözlem kimliklerini doğrulamadım. Trek'teki `frt_07_*` browse mozaiklerinin YKB'yi kapsayıp kapsamadığını da kontrol etmedim.
- **Trek `Gale_DEM_SMG_1m`.** USGS'in "MSL Gale Merged DEM 1m v3" ürünüyle aynı olup olmadığını bilmiyorum.
- **İnsanlı keşif bölgeleri.** YKB veya boxwork'ün önerilmiş bir insanlı Exploration Zone içinde olup olmadığını `EZMars` katmanında sorgulamadım.
- **Boxwork için APXS ve CheMin.** Release 42 notu DAN ve ChemCam için doğrulandı; APXS ve CheMin için kontrol etmedim.
- **MOLA PEDR.** ODE REST sorgusu parametre hatası verdi. DEM'i lazer atımlarıyla bağımsız kontrol etmenin yolu açık kaldı.
- **Ingenuity görüntüleri** raw-images API'sinde kamera filtresiyle bulunamadı. Drone rolü için Ingenuity'nin keşif uçuşlarını ve görüntü erişimini ayrıca doğrulamak gerekiyor.
- **MMGIS konumları** PDS arşivi değil, operasyonel ve halka yönelik ürünler. Doğrulukları ve semantikleri belgelenmiş değil; PLACES ile çapraz kontrol önerilir.
- **ESP_087149_1750.** NASA'nın "Curiosity'yi boxwork yakınında gösteren 28 Şubat 2025 HiRISE görüntüsü" olduğu yalnız tarih eşleşmesine dayanıyor.
- **Tespit sınırı.** "HiRISE ile ~0,75–1 m altı kaya görülmez" bir kural, ürün spesifikasyonu değil.
- **Moon Trek'in aynı servis yoluyla çalışması** doğrulanmadı.
- **Yerel notlardan alınıp bu turda doğrulanmayanlar:** Jezero CTX 3.396.160 m yarıçapı, Mayıs 2024 RAD olayının 8.100 µGy değeri, giysi metabolik sayıları (EWT, Norcross).
- **Perseverance arşiv sayısı.** Raw-images API `total_results` = 579.518 veriyor; challenge "one million images" diyor. Sayım yöntemi farklı olabilir.

**Bu oturumda çalıştırılanlar.** Yalnız salt-okunur HTTP sorguları ve bellekte ayrıştırma yapıldı. Proje dosyalarında değişiklik yapılmadı ve hiçbir raster indirilmedi. DTM'den eğim RMSE'si veya DTM–DTM farkı **hesaplanmadı** (GDAL/numpy kurulu değil); E4'teki sayılar yöntem önerisidir.
