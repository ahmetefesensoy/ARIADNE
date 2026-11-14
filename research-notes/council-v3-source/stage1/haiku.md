# Stage 1 - Haiku 5.5 (red-team, şeytanın avukatı)

Tarih: 2026-11-14. Yalnız okuma yapıldı; proje dosyası değiştirilmedi.

## 0. Kaynak durumu (önce bunu oku)

- **Resmî challenge sayfası açılamadı.** `spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/` bu oturumda `unable to get local issuer certificate` (SSL) hatası verdi; brief'in belirttiği 502 ile aynı aile sorun. Aşağıdaki challenge maddeleri **yerel organizatör kopyasından** (`hackathlone.com/challenges/interplanetary-survival-guide-martian-map`) gelir. Resmî metin nihai kaynaktır ve sayfanın kendisi "the final word" diyor.
- **Yerel kopya iki farklı okumada çelişti.** İlk WebFetch "at least three kinds of data" ifadesini zorunlu madde gibi sundu; ikinci WebFetch aynı maddeyi "may consider / önerilen" olarak sundu. Bu fark **doğrulanmadı**. Jüri kriteri açısından önemli: Zorunlu mu, öneri mi? Resmî sayfadan teyit edilmeli.
- **2026 jüri kriterleri doğrulanamadı.** Bir web araması, proje teslim rehberinde beş kriter bulduğunu bildirdi (Impact, Creativity, Validity, Relevance, Presentation) ve bunun 2025 rubriğinden taşındığını varsaydı. Bu bir üçüncü taraf özetine ve bir arama snippet'ine dayanıyor; **doğrulanmış değil**. Challenge sayfasında jüri kriteri yok; yerel kopya "How the winners are picked" bağlantısını gösteriyor, içeriği açılamadı.
- Proje içi kaynaklar okundu: `KAYNAK_VE_VARLIK_KATALOGU.md`, `research-notes/Gale_PLACES_AOI_KONTROLU.md`, `research-notes/SAHA_VE_BILIM_ISTASYONU.md`, `research-notes/SPACE_APPS_MAPPING_JURI_INCELEMESI.md`, `research-notes/HIRISE_YELLOWKNIFE_METADATA_KONTROLU.json`, `research-notes/SAHA_OLCUM_METADATA_KONTROLU.json`. Eski araştırma (`önceki deneme/docs/REDLINE_RESEARCH.md`) boxwork / Mount Sharp sahasını kullanıyordu; mevcut fikir Yellowknife Bay'e kaydı. Bu geçiş bilinçli bir karar mı, yoksa dokümanlar arasında kopukluk mu, belirsiz.

## 1. Challenge'ın gerçek istekleri ve mevcut fikrin karşılama durumu

Kaynak: yerel challenge kopyası (resmî sayfa açılamadı). Durumlar: **İyi** = fikirde açıkça var ve veri zinciri belgeli; **Zayıf** = var ama kanıtsız veya yalnız tanımda; **Yok** = fikirde karşılığı yok.

| # | Challenge isteği (özet, kaynak: yerel kopya) | Mevcut fikir | Durum | Neden |
|---|---|---|---|---|
| R1 | "a map, tool, or interface a Mars astronaut could use during a surface exploration mission", NASA verisiyle | Canlı harita + Unreal habitat/prova | **Zayıf** | Harita var ama ana kullanım "prova/oyun" olarak çerçevelenmiş; astronotun gerçekten kullanacağı bir çıktı (EVA kartı, rota görünümü) tanımlı değil. |
| R2 | Bilim hedefleri ve konumun belirlenmesi (örnek: Mount Sharp boxwork) | Yellowknife Bay, John Klein / Cumberland | **Zayıf** | Hedef var, ama "Yellowknife" için yerel veri AOI'si (2x2 km Gale AOI) bu hedeften yaklaşık 13 km uzakta (bkz. §4-K1). Yani hedef ile veri aynı yerde değil. |
| R3 | En az üç veri türü ("optical, thermal, spectral, topographic, geophysical, atmospheric, radiation, chemical") | Topo DEM, LRGB/HiRISE optik, APXS/CheMin kimya, REMS atmosfer, RAD radyasyon, THEMIS termal (aday) | **Zayıf** (kâğıt üstünde İyi) | Kataloglu ama yalnız DEM ve LRGB "Yerel" durumda; diğerleri "Aday" veya "Referans". Jüri için bir gösterimde gerçekten birleşmiş katman sayısı şu an 2 (aşağıdaki kodlarla). |
| R4 | Güvenlik: "NASA's first priority is always astronaut safety"; uzay havası / radyasyon | RAD, SEP uyarısı, "dönüş sınırı", O₂/süre bütçesi | **Zayıf** | Radyasyon kaydı var; "SEP uyarısı" ürünü ve O₂/süre/giysi modelleri NASA verisi değil, varsayım. Güvenlik garantisi iddiası kurulamaz (kendi kataloğu da bunu söylüyor). |
| R5 | Rota haritası: hedeflere giden yol, büyük kaya oluşumlarından kaçınma | Yol/rota, path planning | **Zayıf** | Rota fikri var; "kaçınılacak engel" verisi (yerel 4 m DEM engel çözmez, kataloğun kendi notu) ve NASA'nın kendi önerdiği rota (Curiosity Mount Sharp yolu) kullanılmıyor. |
| R6 | İnsan mobilitesi: giysi ve taşınan ekipman etkisi | Giysi eğim kısıtı | **Zayıf** | Parametre varsayım; kaynağı yok. |
| R7 (opsiyonel) | Format: habitat ekranı, tablet, HUD, ya da üretici araç | Unreal habitat, tablet | **İyi** | Açık. |
| R8 (opsiyonel) | Zaman çerçevesi: geçmiş veri, tahmin, sabit veri | Yörünge + rover kronolojisi | **Zayıf** | Zaman serisi (PLACES, REMS) fikirde var ama "hangi zamanın kararı" tanımlı değil. |
| R9 (opsiyonel) | POV önizleme: yüzey görüntüleri | Yok (Navcam aday olarak katalogda) | **Yok** | Perseverance/Navcam fotoğraflarıyla hedef önizlemesi fikirde yok. |
| R10 (opsiyonel) | Lojistik: rover ile yük taşıma, çiftler | Rover yardımı (keşif/yük) | **Zayıf** | Robot yardımı var, ama challenge karşılığı ("insan iş yükü") net bağlanmamış. |
| Res1 | Resources: JPL Mars Trek (trek.nasa.gov) | Fikirde yok; katalogda yok | **Yok** | Challenge'ın ilk kaynağı. Önceki araştırmada D-19 olarak geçiyor, mevcut kataloğa girmemiş. |
| Res2 | Resources: USGS-NASA Planetary Geologic Mapping (ArcGIS) | Fikirde yok | **Yok** | Gale jeoloji haritası katkısı (birim/sınır) kullanılmıyor. Not: link non-NASA; veri kullanım koşulları ayrı. |
| Res3 | Resources: Curiosity proposed path up Mount Sharp (science.nasa.gov) | Fikirde yok | **Yok** | Challenge'ın kendi örnek rota kaynağı; kullanılmıyor. |
| Res4 | Resources: NASA Worldview | Fikirde yok | **Yok** | Dünya odaklı bir arayüz; Mars'ta kullanım kapsamı bu incelemede doğrulanmadı. |
| Res5 | Resources: Mars Perseverance Raw Images Gallery | Fikirde yok | **Yok** | Jezero yüzeyi; Gale sahası için doğrudan kullanılamaz, POV önizleme için yalnız Gale'den Navcam ile eşleşebilir. |

Özet: Challenge'ın 5 resource linkinden **0 tanesi** mevcut kataloğa doğrudan girmiş değil (Mars Trek yalnız eski araştırmada geçiyor). Proje kendi kataloğunda da "Güncel challenge Resources listesinden en az bir NASA kaynağının gerçekten kullanıldığının teslim öncesi kontrolü ayrıca yapılır" diyor; bu kontrol şimdiden kritik.

## 2. En değerli 8 geliştirme (öncelik sırasıyla)

Her madde: ne / neden (challenge + jüri) / veri (ürün, erişim, gerçek mi) / jüride nasıl görünür. Kritik not: Veri erişim yolları resmî PDS/USGS/JPL adresleri olarak kendi kataloğundan alındı; **ürün ID'lerinin tekil seçimi ve erişilebilirliği bu turda açılıp doğrulanmadı** (bkz. §5).

**G1. Tek ve tutarlı saha: AOI'yi hedefin etrafına taşı.**
- Ne: Yerel 2x2 km AOI (Gale kırpımı) ile John Klein/Cumberland hedefleri arasındaki ~13 km farkı kapat. Ya AOI'yi John Klein etrafına yeniden kur (DEM ve LRGB kırpımı), ya da hedefi mevcut AOI'deki bir PLACES noktasına çevir.
- Neden: R1, R2, R3 (challenge "location to explore" + "layered view of a location"). Jüri "hangi yerde?" sorusunu ilk dakikada sorar.
- Veri: Gale DEM 1 m (USGS Astrogeology, `MSL_Gale_DEM_Mosaic_1m_v3`); HiRISE PSP_010573_1755_RED v2.0 (MRO, PDS, label sınırları JSON'da kayıtlı). Gerçek ölçüm/türetilmiş karışımı — provenance'ta ayrılır.
- Jüride: Harita açıldığında hedef işaretli, DEM+ortho aynı koordinatta görünür. Mevcut "Yellowknife" iddiası kapanır.

**G2. Rota: gerçek rover izini ve NASA'nın kendi yolunu kullan.**
- Ne: Astronot rotası, NASA'nın yayınladığı Curiosity yolu ve MSL rover konum kayıtlarından çizilmiş gerçek izle karşılaştırılır. Rota seçenekleri (en az iki koridor) gösterilir.
- Neden: R5 (birebir challenge örneği "route map ... avoiding major obstacles"). Jüri "NASA'nın kendi yolunu gördünüz mü?" sorusunu sorar.
- Veri: (a) Curiosity proposed path (science.nasa.gov resource) — planlanmış yol, gerçek ölçüm değil; (b) MSL PLACES `localized_interp.csv` (PDS, JPL, `planetarydata.jpl.nasa.gov/img/data/msl/msl_places/`) — gerçek rover konum/yerelleştirme, 49.315 satır. Gerçek ölçüm.
- Jüride: "Bu iz NASA'nın gerçek rover izi; astronotun koridoru onun yanında." Güçlü ve doğrulanabilir.

**G3. Challenge resource'larını bilimsel katman olarak bağla (Mars Trek, USGS geoloji, Worldview).**
- Ne: Mars Trek WMTS katmanı çapraz kontrol; USGS-NASA geoloji haritası birim sınırı katmanı; Worldview (Mars kapsamı doğrulanırsa) yalnız bağlam.
- Neden: Res1–Res4 ve R3 (ek veri türü, yeni katman yerine çapraz kontrol). Jüri "resource listesini okudunuz mu?" sorusuna doğrudan cevap.
- Veri: Mars Trek (trek.nasa.gov, NASA, web servisi); USGS geoloji (astrogeology-usgs hub — non-NASA, veri koşulları ayrı). Gerçek/türetilmiş ayrımı kaydedilir.
- Jüride: "Yerel DEM'i Mars Trek ile çapraz kontrol ettik; sapma X m." Bu, sadece görsel değil doğrulama.

**G4. Radyasyon ve çevre zaman penceresi: MSL RAD dozu + REMS ortamı ile EVA zamanlaması.**
- Ne: EVA penceresi seçimini destekleyen iki gerçek ölçüm zaman serisi: günlük sıcaklık/basınç/UV (REMS) ve doz (RAD). "Güvenlik" paneli bunlardan beslenir; sayılar kaynağıyla çıkar.
- Neden: R4 (NASA: "first priority ... astronaut safety"; radyasyon ve "time frame" opsiyoneli). Jüri "güvenlik" iddiası için kanıt arar.
- Veri: MSL RAD RDR (PDS PPI, `MSL-M-RAD-3-RDR-V1.0`) — doz/ürün seviyesi, ham count değil; MSL REMS `MSL-M-REMS-5-MODRDR-V1.0` (PDS atmospheres). Gerçek ölçüm, ancak Gale'de tek nokta; tüm saha için geçerli değil. Uzay havası "SEP uyarısı" için gerçek bir Mars canlı akışı **yok** kabul edilmeli; yalnız geçmiş olay yeniden oynatımı (etiketli).
- Jüride: "Bu saat aralığında doz şu kadar, bu sol'de RAD ölçümü; bu bir senaryo" — çok olgun görünür.

**G5. Bilim durağı: gerçek APXS + CheMin ile hedef kartı.**
- Ne: John Klein ve Cumberland için kart: APXS hedef satırları (Sol 169 Wernecke_Brushed; Sol 276 CumberlandNew_RP), CheMin mineral bolluğu (John Klein ve Cumberland CSV'leri), HiRISE bağlamı. Astronotun "neyi, neden örnekleyeceği" bu kartta.
- Neden: R2 (bilim hedefleri ve konum) + challenge "do new science". Jüri "bilim mi yoksa oyun mu?" sorusuna cevap.
- Veri: APXS supplement `ds01_2020je006536rr.csv` (PDS); CheMin `CMA_414856883MIN01960060000CH12240P1` (John Klein, label "preliminary") ve `CMB_422579177MIN02830060082CH12350P1` (Cumberland). Gerçek ölçüm; çoğu "preliminary" veya "ön analiz".
- Jüride: Kart açıldığında kaynak, sol, hazırlık kodu ve "preliminary" işareti görünür. Güven sinyali.

**G6. Belirsizlik ve provenance katmanı (ekranda görünür).**
- Ne: Her hücrede kaynak ürün, çözünürlük (4 m ağ, 25 cm ortho, 100 m THEMIS), yaş, güven; "bilinmeyen" alan açık gri.
- Neden: "harita neyi bilmediğini bilir" (fikrin kendi ilkesi). Challenge "Validity" benzeri jüri kriterlerinin kalbi. (Kriterler doğrulanmadı; bkz. §5.)
- Veri: Proje içi kayıt (`TERRAIN_PROVENANCE.json`, hash'ler) + her ürünün PDS etiketi. Gerçek/türetilmiş/senaryo ayrımı.
- Jüride: Sunumda bir hücreye tıklamak kaynağı açar. Bu, "neyin gerçek olduğunu" en hızlı gösterir.

**G7. POV önizleme: Gale Navcam ile durak görüntüsü.**
- Ne: Her bilim durağında, o noktaya yakın gerçek Navcam görüntüsü (sol, kamera, poz ile) önizleme olarak. Challenge'ın "Imagery" opsiyoneli.
- Neden: R9 (opsiyonel ama görsel etki yüksek). Jüri "astronot ne görüyor?" sorusuna.
- Veri: MSL Navcam RDR (PDS, `MSL-M-NAVCAM-5-RDR-V1.0`); Analyst's Notebook (WUSTL) konum. Gerçek ölçüm. Perseverance Raw Images (Jezero) yalnız "başka bir yer" etiketiyle, karıştırmadan.
- Jüride: Gerçek bir Mars görüntüsü, astronot gözünden. Estetik ve doğruluk bir arada.

**G8. Rover/drone katkısını harita güncellemesine bağla (A/B değerlendirme).**
- Ne: İki koşu: (a) yalnız yörünge verisiyle plan, (b) yörünge + simüle rover gözlemi. Karar değişimi, bilinmeyen oranı, süre ve dönüş payı karşılaştırılır. Simüle değerler açıkça etiketli.
- Neden: "Robot yardımı challenge karşılığı net değil" (R10) ve "Validity". Jüri "robot neyi değiştirdi?" sorusunu cevaplar.
- Veri: Yörünge (G1–G3) gerçek; rover gözlemi simüle (Gazebo). Etiket zorunlu.
- Jüride: Tek bir sayı karşılaştırması ("bilinmeyen oranı %X'ten %Y'ye") güçlü, ama yalnız senaryo varsayımıyla ifade edilir; kesin güvence değil.

Opsiyonel kısa liste (vaktine göre): THEMIS gece/gündüz termal (R3; yalnız EVA zamanlaması karar değiştiriyorsa); ikinci saha (Jezero) manifest ile yüklenir (interplanetary kriteri; yalnız biri tam bitmişse).

## 3. Mevcut fikirde yeniden çerçevelenmesi gereken 5 şey

1. **"Survival" ile "EVA karar aracı" arasındaki boşluk.** Mevcut fikir hayatta kalma oyunu gibi okunuyor (O₂, süre, giysi). Challenge bir harita/araç istiyor. Teklif: "Bu hedefe gidilmeli mi, hangi koridor, nerede önce gözlem" sorularını cevaplayan bir karar aracı. Oyun/prova (Unreal) bu aracın arayüzü olsun, ana ürün olmasın.
2. **Robotlar "süs" değil, haritayı değiştiren gözlem olmalı.** Şu an rover/drone "demo krizi" ve "beş görev" gibi görünüyor; jüri "hangi harita kararı değişti?" diye soracak. Teklif: her robot görevi haritaya tek bir delta yazsın ve o delta bir karar değiştirsin (G8 ile).
3. **"Yellowknife Bay" iddiasını kapat ya da geri çek.** Yerel veri Yellowknife'da değil; ~13 km güneyde. Eski araştırma boxwork kullanıyordu; Mount Sharp challenge'ın kendi örneği. Teklif: ya G1 ile tek saha kur, ya da sunumda "hedef belgeli, veri henüz eşlenmedi" de. Yanlış yer iddiası jüride ilk ceza.
4. **"Güvenli rota" yerine "rota seçenekleri ve duyarlılık".** Kendi kataloğu zaten "kesin güvence yok" diyor. Teklif: kararı, varsayım değişince nasıl değiştiğini gösteren bir yüzeyle sun. Güvence iddiası = yanlış güven sinyali.
5. **"SEP uyarısı" ve "dönüş sınırı daralması" bir canlı Mars akışı gibi sunulmasın.** Gerçek bir Mars SEP akışı ve canlı NASA uyarı ürünü bu incelemede doğrulanmadı. Teklif: RAD'deki geçmiş bir olayı ("oynatım, senaryo") etiketli sunmak ve dönüş sınırının bu varsayıma bağlı olduğunu açıkça göstermek.

## 4. Veri iddialarının çürük olduğu yerler (red-team)

- **K1. Yellowknife ile yerel AOI aynı yerde değil.** Mevcut AOI (kayıtta) enlem -4,825…-4,791°, boylam 137,428…137,462°. John Klein APXS/HiRISE koordinatı (JSON'dan) enlem -4,5895°, boylam 137,449°. Enlem farkı ~0,22° ≈ 13 km (Mars yarıçapı 3396 km ile kaba hesap; bu tutarlı). Yani "Gale kraterinde Yellowknife Bay ... yerel DEM" cümlesi yanlış okunur. Kendi `Gale_PLACES_AOI_KONTROLU.md` de yalnız "AOI'de konum örneği yok" diyor; 13 km farkı yazmıyor.
- **K2. PLACES sorgusu yanlış sollarla yapılmış görünüyor.** `SAHA_OLCUM_METADATA_KONTROLU.json` filtresi `sol in [182,279,1223,1225]`. Aynı kayıt setinin APXS seçimi sol 169, 276 ve Gobabeb sol 1226, 1242 kullanıyor (`SAHA_VE_BILIM_ISTASYONU.md`). 182 ve 279 John Klein/Cumberland sürüşlerinde sondaj solları olarak bilinir (bu bilgi bu oturumda kaynakla doğrulanmadı; bilinen kayıt). Sorgu sol numaralarında tutarsız. "0 eşleşme" sonucu bu yüzden anlamsız olabilir. Düzeltilmeden jüride kullanılmamalı.
- **K3. "Dört sol için PLACES eşleşmesi yok" cümlesi kendi kaydıyla çelişiyor.** Yukarıdaki K2 yüzünden: sorgu edilen sollar ile belgeli APXS/Gobabeb sollar farklı. İki ayrı hata olabilir: yanlış sol, ya da PLACES'in "sol" tanımı APXS sol'una eşit değil.
- **K4. CheMin John Klein sonucu "ön" (preliminary).** Etiketi "preliminary analysis; additional analysis time ... updated mineral abundance table will be provided" diyor. Kil oranı %22 ± 11, amorf %28 ± 15 — belirsizlik çok büyük. Sunumda kesin mineral bileşimi gibi yazılırsa jüri (ve bilimci) yakalar.
- **K5. HiRISE PSP_010573_1755 bir ön-iniş görüntüsü (2008).** Label RATIONALE "possible MSL landing site" diyor; yani 2008 yörünge görüntüsü, Curiosity'nin 2012 iniş sonrası değil. Bağlam olarak uygun, ama "Curiosity'nin gördüğü sahne" gibi yazılamaz. Ayrıca numeric bbox kontrolü, Gobabeb'in bu üründe olmadığını gösteriyor (`numeric_bbox_contains: false`): yedek saha için bu ürün çalışmaz.
- **K6. Labeled "bbox" kontrolü hizalama değildir.** JSON'un kendi "interpretation" alanı bunu söylüyor: "Numeric bounding-box check only ... Does not establish exact target or drill-hole pose." Bunu "doğrulanmış eşleşme" diye sunmak yanlış.
- **K7. 4 m ağ ile "yürüyüş engeli" iddiası.** KAYNAK kataloğu yerel 4 m ağın ayak/teker engelini çözmediğini söylüyor. Ama ekranda "kaya engeli" ve "rota kaçınma" görseli, bu çözünürlükte yanlış güven verir.
- **K8. "Gerçek" ile "senaryo" karışması riski.** Kendi notları (örneğin pH) "Gale'deki pH sonucu simülasyon" diyor. Harita katmanında aynı görsel dil kullanılırsa jüri ayrımı kaçırır (fikrin kendi "güven katmanı" maddesiyle çelişir).
- **K9. RAD dozu ≠ insan dozu.** Kendi kataloğu "counts, doz ve insan maruziyeti farklı büyüklükler" diyor. Dönüşüm yapılırsa jüri "absorbe doz/etkin doz" farkını sorar.
- **K10. 20 Mayıs 2024 SEP olayı.** Eski araştırma bu olayı "karşı-olgusal senaryo" ve RAD'de 8.100 µGy ölçümü olarak yazıyor. Bu değer ve olayın zamanı bu incelemede **doğrulanmadı**; yeniden hesaplanmadan kullanılmamalı.

## 5. Doğrulayamadığın iddialar

- Resmî challenge sayfası: **açılamadı** (SSL). Challenge maddeleri yerel kopyadan; "at least three" zorunlu/öneri çelişkisi açık.
- 2026 jüri kriterleri: **doğrulanamadı**. 2025 rubriği ve üçüncü taraf özetleri var; bu fikirde kullanılan "Validity/Impact" yorumları bu varsayıma dayanıyor.
- Curiosity proposed path, Mars Trek, Worldview, Perseverance raw images, USGS geoloji linkleri: **açılmadı**; içerikleri ve Mars kapsamları (özellikle Worldview) doğrulanmadı.
- Ürün ID'leri (ör. MSL Navcam, MSL RAD, REMS, THEMIS, MOLA tile'ları): proje kataloğundan alındı; bu turda tekil ürün erişimi, sürüm ve coverage (Gale DEM'in John Klein enlemini kapsayıp kapsamadığı) **doğrulanmadı**.
- John Klein ve Cumberland sol numaraları (182, 279) bu oturumda kaynaktan doğrulanmadı; K2 hata iddiası buna dayanıyor.
- 13 km mesafe: proje notundaki AOI sınırı ve John Klein koordinatı ile kaba küresel hesap. AOI'yi TERRAIN_PROVENANCE.json'dan yeniden türetmedim.
- "SEP uyarısı" için NASA veya başka bir Mars akış kaynağı var mı: **bilinmiyor / doğrulanmadı**; bu iddiayı desteklemek için kanıt yok.
- Radyasyon/doz sayıları (8.100 µGy, 39 gün eşdeğeri) ve 2024 olayı: **doğrulanmadı**.
- Kendi yorumlarım (red-team): "jüri şunu sorar", "jüri kriteri şu" gibi ifadeler sezgisel; kriter bilgisi yalnız 2025 çerçevesinden. Jüri davranışı bu oturumda gözlenmedi.
