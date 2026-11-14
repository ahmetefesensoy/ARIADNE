# REDLINE v2 — EVA operasyon ve insan-robot ekip merceğinden inceleme

Mercek: EVA planlama / uçuş kuralları / insan-robot ekip çalışması. Etiketler: **[D]** bu oturumda kaynaktan doğruladım, **[H]** hafızadan/alan bilgisinden, bu oturumda doğrulamadım (§4'te toplu liste).

Kaynak erişim durumu: Resmî sayfa (`spaceappschallenge.org/2026/...`) bu oturumda da açılmadı (TLS sertifika hatası). Aşağıdaki challenge metni **yalnız yerel organizatör kopyasından** (hackathlone.com) okundu; araç tam metni değil kısa alıntı + özet döndürdü. Resmî metinle kelime kelime karşılaştırma yapılamadı.

---

## 1. Challenge'ın gerçek istekleri ve mevcut fikrin karşılama düzeyi

Kaynak: https://hackathlone.com/challenges/interplanetary-survival-guide-martian-map [D]

| # | İstek (metinden) | Niteliği | REDLINE şu an |
|---|---|---|---|
| 1 | Bir astronotun yüzey görevinde kullanabileceği "map, tool, or interface" | Çekirdek | **İyi** |
| 2 | Belirli bir Mars konumu/rotasının katmanlı görünümü; **birden çok NASA görevinin** verisi | Çekirdek | **Zayıf-orta**: fiilen MSL + (DEM içinde) MRO. Odyssey/MGS aday, karar rolü yok |
| 3 | "including at least three kinds of data" (optik, termal, spektral, topoğrafik, radyasyon, atmosfer, kimya örnekleri) | Çekirdek | Kâğıtta 6 tür; **gösterilmiş birleşim yok** |
| 4 | "You might start by identifying some scientific goals"; örnek: boxwork oluşumları | Çekirdek/öneri | **Orta**: Yellowknife güçlü ama bilim sorusu jüri cümlesi hâlinde değil; challenge'ın kendi örneği (boxwork) kullanılmıyor |
| 5 | "NASA's first priority is always astronaut safety"; "you might include space weather data" | Çekirdek | **Kavram iyi, veri zayıf**: SEP bir senaryo olayı, gerçek kayıttan sürülmüyor |
| 6 | Giysinin hareketliliğe etkisi; "avoiding significant obstacles such as large rock formations" | Çekirdek | **Orta**: eğim kısıtı var; giysi/insan parametreleri kaynaksız; 1 m DEM kayayı çözmez |
| 7 | Biçim: habitat ekranı / tablet / kask HUD | Opsiyonel | **İyi fırsat**, roller tanımsız |
| 8 | Çıktı: statik / etkileşimli / **harita üreten sistem** | Opsiyonel | **İyi** (manifest tam olarak bu) |
| 9 | Başka dünyaların nasıl haritalandığından ilham | Opsiyonel | Zayıf (Apollo traverse mirası hiç anılmıyor) |
| 10 | Zaman çerçevesi: geçmiş veri / öngörülen koşul / kalıcı özellik | Opsiyonel | Orta; katman başına açıkça seçilmemiş |
| 11 | **Yüzey görevlerinin bakış-noktası (POV) görüntüleri** haritanın parçası | Opsiyonel | **Yok** (Navcam yalnız aday) |
| 12 | "rovers or other robotic systems to help **transport the crew and their tools**"; astronotların **çiftler hâlinde** çalışması | Opsiyonel | **Zayıf**: rover keşifçi; taşıyıcı/alet arabası değil; ikili EVA yok |
| 13 | Resources (5): Mars Trek, USGS-NASA Planetary Geologic Mapping, "Curiosity's Proposed Path Up Mount Sharp", NASA Worldview, Perseverance Raw Images | Kaynak listesi | **Zayıf**: listedeki hiçbir kaynak adıyla kullanılmıyor (Gale DEM USGS Astrogeology'den ama listelenen sayfa değil) |
| 14 | Jüri: Impact, Creativity, Validity, Relevance, Presentation | Jüri rehberi (arama sonucu düzeyinde [D]; 2026 rehberini açmadım) | Validity ve Relevance en açık iki boşluk |

"Interplanetary" yalnız başlıkta ve Background'da geçiyor; Objectives'te bir gereksinim değil [D].

Bir EVA planlamacısı olarak özet: challenge sizden bir **traverse planı + güvenlik gerekçesi + bilim gerekçesi** istiyor. REDLINE'ın çizgi fikri tam bu; ama şu an çizgiyi çizen sayıların hiçbiri bir ölçüme ya da yayımlanmış insan verisine bağlı değil. Güçlendirme oradan başlamalı.

---

## 2. Öncelik sırasıyla eklemeler

### E1. SEP'i senaryo olmaktan çıkar: Eylül 2017 olayını gerçek RAD kaydından yeniden oynat
- **Ne:** Demo krizindeki SEP, 10–12 Eylül 2017 olayının Gale yüzeyinde RAD ile ölçülmüş zaman serisinden sürülsün. Uyarı zinciri de gerçek olsun: DONKI'deki parlama/CME/SEP kayıtları → Mars'a varış → RAD'de yükseliş → Forbush düşüşü.
- **Neden:** Madde 5 ("space weather data") + veri türü "radiation" + Validity. Jürinin "bu uyarı uydurma mı?" sorusuna cevap: "Hayır, Curiosity bunu 2017'de bu kraterde ölçtü."
- **Veri:** MSL RAD RDR, `MSL-M-RAD-3-RDR-V1.0`, PDS PPI (https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/), ASCII + ayrık PDS etiketi, alan tanımları LABEL/*.FMT; cruise + yüzey kapsıyor [D]. Doz hızı alanının tam adı/birimi için DOCUMENT içindeki RDR SIS okunmalı [doğrulanmadı]. Olay büyüklüğü: doz hızı GCR arka planının ~2–3 katı, birkaç saat; RAD'in yüzeyde gördüğü en büyük olay; bütünleşik doz yalnız hafifçe arttı; ardından ~%15 ani düşüş (Hassler 2018, Zeitlin 2018, Ehresmann 2018) [D, arama özeti]. Uyarı zinciri: NASA CCMC DONKI (`/DONKI/SEP`, `/FLR`, `/CME`, `/WSAEnlilSimulations`), JSON. DONKI sunucusu bu oturumda bağlantıyı reddetti; Mars varış alanı doğrulanamadı.
- **Tür:** Gerçek ölçüm (RAD) + gerçek olay kaydı (DONKI). İnsan dozuna çeviri ve "sığınağa dönüş kuralı" senaryo varsayımı.
- **Operasyonel dürüstlük (önemli):** Gerçek veri, Mars yüzeyinde bu olayın akut öldürücü olmadığını gösteriyor. Bunu saklamayın, öne çıkarın: kural "doz öldürür" değil, **ALARA + uçuş kuralı** ("SEP başlangıcı teyit edilince T dakika içinde sığınakta ol"). REDLINE'ı daraltan şey doz değil, kuralın verdiği süre. Bu, gerçek EVA operasyonunun işleyişidir ve abartılı bir radyasyon sahnesinden çok daha inandırıcıdır.
- **Jüride:** Zaman kaydırıcısı 10 Eylül 2017'ye gelir, RAD eğrisi yükselir, çizgi daralır; köşede ürün kimliği.

### E2. "Robot doğrular" adımını gerçek Curiosity yer verisiyle yap (önce/sonra deneyi arşivle)
- **Ne:** Önce/sonra deneyinin bir kolu tamamen gerçek veriyle: (a) yalnız yörünge (HiRISE 25 cm orto + 1 m DEM) ile çıkarılan engel/eğim; (b) aynı noktada Curiosity Navcam stereo türevleri (XYZ/menzil, eğim, pürüzlülük) ile yerden görülen. Fark = "yörüngenin bilmediği". Simüle rover/drone bu gerçek farkın üstüne eklenen genelleme olur.
- **Neden:** Summary'deki "robotik görevler insanlı görevin yolunu açar" anlatısı + Madde 6 (kaya engeli) + Validity. "NASA verisini çıkarınca ne kaybolur?" itirazını kapatır: deneyin kendisi kaybolur.
- **Veri:** MSL Navcam RDR (`MSL-M-NAVCAM-5-RDR-V1.0`, PDS Imaging / Analyst's Notebook; PDS3 IMG) — XYZ, RNG, UVW, SLP, RUF ürün tipleri [H; tekil ürünler seçilmeli]. Yörünge tarafı: katalog D01/D02 + `PSP_010573_1755_RED` (0,25 m grid, kutu Yellowknife'ı kapsıyor; yerel not [D]).
- **Tür:** Gerçek ölçüm (iki tarafta da). Monte Carlo kolu simüle, ayrı etiketli.
- **Jüride:** Aynı 20×20 m yama: solda yörünge "temiz", sağda rover gözünden 30 cm kayalar; rota kayar.

### E3. Giysi/insan modelini yayımlanmış EVA verisine bağla: tek "O₂ bütçesi" yerine sınırlayıcı sarf + walkback
- **Ne:** REDLINE = her hücre için "buradan sığınağa dönüş süresi × marj ≤ kalan en kısıtlı sarf". Sarflar ayrı izlenir (O₂, CO₂ tutma, soğutma suyu, batarya); çizgiyi **en kısıtlı olan** çizer ve hangisi olduğu ekranda yazar. Yürüme hızı ve metabolik hız eğime bağlı tablo. İki çizgi: **sarı = terminate** (düzenli dönüş başlat), **kırmızı = abort** (hemen dön). Bu ayrım gerçek EVA terminolojisidir.
- **Neden:** Madde 6 (giysi hareketliliği) + Madde 5 + Validity.
- **Veri/kaynak:** NASA'nın BASALT analog programında kullanılan SEXTANT traverse planlayıcısı aynı yapıdadır: DEM + maliyet fonksiyonu (eğime bağlı metabolik maliyet, mesafe, süre) + optimizer; metabolik model Marquez'in Apollo hız/metabolik verisinden ekstrapolasyonu [D, arama özeti; NTRS 20170002364]. Saha bulgusu: **gerçek traverse süresi SEXTANT tahmininden anlamlı uzun, mesafe farksız** (n=6, p<0,01) [D, arama özeti]. Bu bulgu doğrudan kullanılmalı: süre tahminine açık bir marj çarpanı ve belirsizlik bandı. Apollo metabolik hızları (Biomedical Results of Apollo, SP-368) ve 10 km walkback testi (Norcross ve ark.) [H].
- **Tür:** Yayımlanmış insan verisi → model parametresi. Mars giysisi için ölçüm yok; "Apollo/analog türevi varsayım" diye etiketlenir. Arşiv ölçümü değildir.
- **Jüride:** Çizgi tek sihirli sınır değil; "sınırlayan: CO₂, marj 1,4×, kaynak: Apollo/BASALT" yazan bant.

### E4. EVA'yı gerçek bir traverse yap: 4–5 belgeli istasyon
- **Ne:** John Klein ile Cumberland arası ~2,75 m (yerel not [D]); bu bir yürüyüş değil, tek istasyon. Yellowknife Bay/Glenelg çevresinde Curiosity'nin ölçüm yaptığı durakları istasyon yapın: Rocknest (kum; ilk scoop, CheMin/SAM), Point Lake, Shaler, Gillespie Lake, Sheepbed (John Klein + Cumberland) [H: adlar ve hangi cihazın nerede çalıştığı APXS tablosundan/PLACES'ten teyit edilmeli]. Bilim sorusu tek cümle: "Bu eski göl yatağı yaşanabilir miydi; kanıt hangi katmanda?"
- **Neden:** Madde 4 (bilim hedefi) + Madde 2 (rota). Rota ancak istasyonlar arasında mesafe olursa güvenlik çizgisiyle anlamlı etkileşir.
- **Veri:** APXS supplement `ds01_2020je006536rr.csv` (712 satır, hedef/site/sol/koordinat/oksit; PDS Geosciences; yerel not [D]) — site alanına göre süzülür; CheMin `CMA_414856883MIN...`, `CMB_422579177MIN...` (yerel not [D]); PLACES `localized_interp.csv`.
- **Tür:** Gerçek ölçüm, istasyon başına. Numune kökeni ≠ analiz konumu ayrımı korunur.
- **Jüride:** Her istasyon pini tıklanınca gerçek oksit tablosu + sol + ürün kimliği.

### E5. Resources listesini adıyla kullan (Mars Trek + USGS jeoloji + "Proposed Path")
- **Ne:** (a) Mars Trek katman servisinden bölgesel taban: CTX mozaik, THEMIS gündüz/gece IR, MOLA. (b) USGS-NASA jeolojik harita birimlerini "jeolojik birim" katmanı olarak. (c) "Curiosity's Proposed Path Up Mount Sharp" ile aynı görsel dilde bir "insan traverse haritası" çıktısı.
- **Neden:** Madde 13 + Relevance. Jüri Resources'ı kendisi seçti; ilk bakacağı şeylerden biri budur. Ayrıca Madde 2: Odyssey (THEMIS) ve MGS (MOLA) ile görev sayısı dörde çıkar.
- **Veri:** https://trek.nasa.gov/mars/ (katman/WMTS erişimi [H; uç noktalar doğrulanmadı]); https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars; THEMIS 100 m (katalog D10).
- **Karar rolü (süs olmasın):** THEMIS gece IR/termal atalet → gevşek kum vs ana kaya ayrımı için bölgesel ipucu (ayak tutuşu, batma). 100 m çözünürlükte "bölgesel bağlam" etiketiyle; hücre güveni düşük.
- **Tür:** Gerçek ölçüm/arşiv türevi.

### E6. POV katmanı: "varınca ne göreceksin"
- **Ne:** Her istasyon ve kritik rota noktasında, o konumdan çekilmiş gerçek Curiosity Navcam/Mastcam karesi; HUD'da Unreal görüntüsünün yanında "gerçek fotoğraf" kartı. İkinci sahada Perseverance Raw Images (listelenen Resource).
- **Neden:** Opsiyonel madde 11 kelimesi kelimesine + Madde 13 + Presentation. EVA eğitiminde saha tanıma (landmark) gerçek bir ihtiyaçtır; Apollo ekipleri traverse fotoğraflarıyla çalıştı [H].
- **Veri:** MSL Navcam/Mastcam (PDS Imaging, Analyst's Notebook https://an.rsl.wustl.edu/msl/); https://mars.nasa.gov/mars2020/multimedia/raw-images/. Çekim konumu ≠ görülen hedef; ayak izi ayrı kaydedilir.
- **Tür:** Gerçek görüntü.

### E7. Go/No-Go penceresi: gerçek sol kaydından EVA başlangıç saati
- **Ne:** Seçilen gerçek sol(ler) için REMS (yer/hava sıcaklığı, basınç, UV) + atmosferik opaklık (tau) + SPICE güneş yüksekliği ve DEM gölgesi → "EVA penceresi" şeridi. Güneş açısı kuralı: çok alçak güneş uzun gölge/karşıdan parlama, çok yüksek güneş kontrast kaybı (Apollo iniş/EVA planlama pratiği [H]). 2018 küresel toz fırtınası solü "No-Go" örneği.
- **Neden:** Summary'deki "current conditions" + veri türü "atmospheric" + Madde 10 (zaman çerçevesi).
- **Veri:** MSL REMS `MSL-M-REMS-5-MODRDR-V1.0` (PDS Atmospheres, katalog D08); NAIF SPICE; tau için Mastcam opaklık kaydı [H; ürün seçilmeli].
- **Tür:** Gerçek ölçüm; "tarihsel sol yeniden oynatımı" etiketli, canlı hava değil. Eşik değerleri senaryo kuralı.

### E8. İkili EVA + rover'ın gerçek işi: taşıma, röle, sığınak
- **Ne:** İki astronot (EV1/EV2); çizgi **daha kötü durumdaki** kişiye göre. Acil durum: bir kişi yavaşlarsa (yaralanma/giysi kaçağı) dönüş hızı düşer, çizgi yeniden hesaplanır. Rover: alet/numune arabası, iletişim rölesi, açık varsayımla sarf takviye noktası. DEM'den **görüş hattı (LOS) iletişim kapsama katmanı**: habitat ve rover'a göre; rover konum değiştirince kapsama ve çizgi genişler.
- **Neden:** Opsiyonel madde 12 kelimesi kelimesine + Madde 5. Mevcut "vana/kaçak" görevi burada challenge'a bağlanır: kaçak habitat vanası değil **giysi kaçağı** olursa doğrudan çizgiyi sürer.
- **Veri:** D01 DEM (gerçek) → türetilmiş viewshed. Rover taşıma kapasitesi senaryo.
- **Jüride:** Rover bir tepeye çıkar, gölgedeki istasyon "iletişimli" olur, çizgi açılır. Robotun insan seferine katkısı tek karede.

### E9. Üç biçim = üç operasyonel rol + üretilen EVA zaman çizelgesi
- **Ne:** Habitat ekranı = IV operatörü (Mars'ta gecikme nedeniyle Dünya gerçek zamanlı yönetemez; habitat içindeki ekip üyesi "yerel MCC"dir; BASALT bu konsepti gecikmeli iletişimle çalıştı [H]). Tablet = planlama/brifing. HUD = yalnız marj, sonraki istasyon, dönüş yönü. Sistem haritadan **PET tabanlı zaman çizelgesi ve "cuff checklist"** üretir: bacak süreleri, istasyon işleri, karar noktaları, her noktada dönüş süresi.
- **Neden:** Opsiyonel 7–8 + Impact. Gerçek planlamacının isteyeceği teslimat harita değil, **haritadan türeyen zaman çizelgesi ve kurallardır**.
- **Veri:** Tümü yukarıdaki katmanlardan türetilir.

### E10. İkinci saha: Jezero yerine (veya önce) Gale boxwork
- **Ne:** Manifest gösterimi challenge'ın kendi örneğiyle: Curiosity 2025–2026'da Mount Sharp'ta boxwork sırtlarını örnekledi (Altadena, Nevado Sajama 2; sırtta kil, çukurda karbonat bulguları) [D, arama özeti]. Jezero üçüncü olarak kalabilir; orada Ingenuity'nin gerçek hava görüntüleri "drone tarar" adımının arşiv karşılığıdır [H].
- **Neden:** Madde 4'teki örnek birebir; Creativity yerine Relevance puanı.
- **Veri:** Gale DEM/orto mozaiğinin boxwork bölgesini kapsayıp kapsamadığı ve sol ~4500+ APXS/CheMin ürünlerinin PDS'te yayımlanıp yayımlanmadığı **doğrulanmadı**; önce bu kontrol edilmeli. Yoksa bu saha "yalnız yörünge + POV" profiliyle yüklenir ve bu da dürüstçe gösterilir.

---

## 3. Yeniden çerçevelenmesi gerekenler

1. **SEP "ölümcül kriz" değil, kural tetikleyicisi.** RAD verisi yüzeyde olayın sınırlı olduğunu gösteriyor. Çizgiyi daraltan mekanizma uçuş kuralı ve sığınağa varış süresi olmalı. EVA risk sıralamasında gerçek sürücüler sarf, giysi arızası, düşme/yaralanma, iletişim kaybı ve termal yüktür; radyasyon ALARA başlığıdır. Ayrıca Dünya kaynaklı tahmin Mars'a ışık süresiyle gelir ve Mars farklı manyetik bağlantıdadır; yerinde dozimetre (RAD benzeri) anlatısı daha doğru [H].
2. **Güven katmanı renk değil, marj üretmeli.** "Bilinmeyen hücre" → hız cezası ve süre belirsizliği → çizgiye yansır. Planlamacı "haritanın neyi bilmediğini" değil, "bilinmeyenin bana kaç dakika marja mal olduğunu" sorar. E2 farkı ve BASALT'ın "gerçek süre > tahmin" bulgusu bu cezanın kaynağı olur.
3. **Beş görev → tek EVA'nın evreleri.** Brifing/Go-No-Go → robot öncü keşif → traverse → istasyon bilimi → dönüş/acil durum. Vana görevi giysi kaçağı acil durumuna, eğitim/sınav görevi brifing/prova evresine dönüşür. Yerel jüri notunun §5 önerisiyle uyumlu.
4. **"Interplanetary" manifesti başlık cümlesi olmasın.** Metinde gereksinim değil. Manifesti "harita üreten sistem" (opsiyonel madde 8) olarak sunun ve boxwork ile kanıtlayın.
5. **Önce/sonra deneyi önce arşivle, sonra simülasyonla.** Monte Carlo tek başına "kendi modelimizi kendi modelimizle doğruladık" izlenimi verir. Gerçek yörünge–yer farkı (E2) ve mümkünse planlayıcı rotasının Curiosity'nin gerçek izinden (PLACES) sapmasının raporu Validity'yi taşır. Rover izi insan için onay değildir; yalnız geçilebilirlik karşılaştırmasıdır.

---

## 4. Doğrulayamadığım iddialar

- Resmî challenge sayfası açılmadı; tüm metin yerel kopyadan ve araç özeti üzerinden. Tam verbatim metin alınamadı.
- Jüri kriterleri (Impact/Creativity/Validity/Relevance/Presentation) arama sonucundan; 2026 rehberi ve ağırlıklar okunmadı.
- RAD RDR'de doz hızı alanının adı, birimi, kadansı ve Eylül 2017 dosyalarının varlığı: yalnız dizin ve AAREADME görüldü. AAREADME ürünleri hem "calibrated" hem "Level 1A" diye tanımlıyor; RDR SIS okunmalı.
- DONKI uç noktaları ve WSA-ENLIL çıktısında Mars varış zamanı: sunucu bağlantıyı reddetti; Mars alanı her koşuda olmayabilir.
- Eylül 2017 olayının sayıları makalelerden değil arama özetinden; kaynaklar taban/tepe tanımında farklı (2× – 3×).
- MSL Navcam türev ürün tipleri (XYZ/RNG/UVW/SLP/RUF) ve Yellowknife sollerinde bulunmaları: hafızadan.
- Yellowknife istasyon adları ve cihaz eşleşmeleri (Rocknest, Point Lake, Shaler, Gillespie Lake): hafızadan; APXS tablosunun `site` alanıyla teyit edilmeli.
- SEXTANT/Marquez modelinin katsayıları; Apollo metabolik hızları; 10 km walkback testi; BASALT gecikme değerleri; Apollo güneş açısı kuralı: hafızadan veya ikincil kaynaktan.
- Mars Trek katman listesi ve WMTS erişimi; USGS jeolojik haritanın Gale ölçeğindeki uygunluğu.
- Mastcam tau ürününün erişimi; 2018 toz fırtınası solleri için REMS kapsamı.
- Boxwork bölgesi için DEM/orto kapsaması ve yeni APXS/CheMin ürünlerinin PDS yayımı.
- Ingenuity görüntülerinin PDS ürün kimlikleri.
- Yerel notlardaki ürün doğrulamalarını (APXS satırları, CheMin etiketleri, HiRISE kutusu) yeniden çalıştırmadım; notların beyanına dayandım.
