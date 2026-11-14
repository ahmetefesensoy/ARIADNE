# REDLINE v2 - Stage 1 (Sonnet 5.5, mercek: vizyoner ürün tasarımcısı / jüri hikâyecisi)

## 0. Kaynak durumu (dürüstlük notu)
- Resmî challenge sayfası: WebFetch "unable to get local issuer certificate" verdi -> AÇILAMADI.
- Yerel organizatör kopyası (hackathlone.com) AÇILDI; ancak fetch aracı özetledi, birebir alıntı vermedi. Aşağıdaki "alıntılar" bu özetin sadık çevirisidir, birebir değildir.
- Yerel dosyalardan okunanlar: SPACE_APPS_MAPPING_JURI_INCELEMESI.md (başı), Gale_PLACES_AOI_KONTROLU.md, APXS_HEDEF_ON_KONTROL.json (başı), KAYNAK_VE_VARLIK_KATALOGU.md D01-D16 satırları. PROJE_KILAVUZU.md ve SPACE_APPS_KAPSAMLI_ARASTIRMA.md okunmadı.

## 1. Challenge'ın gerçek istekleri (hackathlone kopyası) ve mevcut fikrin karşılaması

Objectives (özet): "Mars yüzey astronotu için harita/araç/arayüz üret":
| # | İstek | REDLINE şimdi |
|---|---|---|
| 1 | Bir BİLİM HEDEFİyle başla, ona uygun konum seç | Zayıf. Saha (Yellowknife Bay) var ama tek bir araştırma sorusu/hedef cümlesi yok; jüri incelemesi de "nihai bilim AOI'si seçilmedi" diyor |
| 2 | En az 3 veri türü (optik, termal, spektral, topografik, atmosferik, radyasyon, kimyasal) | İyi kâğıt üstünde (DEM, HiRISE, APXS, CheMin, RAD, REMS, THEMIS); kanıt: hepsi "aday", entegre çalışan zincir yok |
| 3 | Mürettebat güvenliği: radyasyon ve uzay havası öncelikli | Orta. SEP uyarısı demoda var ama RAD gerçek ölçümüne bağlı mı belirsiz; "insan maruziyeti varsayımlı" |
| 4 | Giysi hareket kabiliyeti + büyük engellerden kaçan rotalar | Orta. Eğim kısıtı var; giysi modeli varsayımlı, kaynaklanmamış |
| Opsiyonel a | Biçim: habitat ekranı / tablet / kask HUD | İyi (UE5 astronot gözü); HUD'a açıkça bağlanmamış |
| b | Statik, etkileşimli veya "farklı siteler için harita üreten araç" | İyi (manifest + Jezero) |
| c | Dünya/Ay/diğer NASA haritalarından ilham | Yok (anılmıyor) |
| d | Geçmiş, tahmin edilen veya zamandan bağımsız veri | Orta (REMS/RAD geçmiş, SEP senaryo) |
| e | Rover bakış açılı görüntü: "vardığında ne beklemeli" | ZAYIF/YOK - katalogda Navcam (D04) aday ama ürün özelliği değil. En kolay kaçırılan istek |
| f | Robotik taşıma desteği veya çift astronot | Orta (rover/drone yardımcı; ikinci astronot yok) |

Resources: Mars Trek, USGS-NASA Planetary Geologic Mapping (ArcGIS Hub), Curiosity "proposed path up Mount Sharp", NASA Worldview (Dünya!), Mars Perseverance Raw Images. REDLINE bunların yalnız USGS DEM'ini (D01) kullanıyor gibi; Trek, jeolojik harita, Mount Sharp rota ürünü, Perseverance ham görüntü ve Worldview-tarzı zaman kaydırıcı atlanmış.

Büyük yapısal gözlem: challenge bir HARİTA/karar aracı ister; REDLINE'ın beş görevli oyun-zinciri ve Monte Carlo kısmı challenge'ın dışına taşıyor (jüri incelemesi de aynısını söylüyor). Kapsam tavsiyesi değil, çerçeve: ürünün kimliği "yürüyüş planlama haritası" olmalı; robot/oyun bunun kanıt motoru.

## 2. En değerli eklentiler (öncelik sırasıyla)

### E1. KRİTİK: AOI'yi gerçek Yellowknife Bay/John Klein'a taşı (doğrulanmış sorun)
- Ne: Mevcut 2x2 km AOI (enlem -4.825...-4.791, boylam 137.428...137.462; northing -286...-284 km) ile APXS John Klein hedefi (Wernecke_Brushed, sol 169: lat -4.589, lon 137.449, northing -272040 m, easting 8147255 m) arasında ~12-14 km fark var. Yani AOI "Yellowknife Bay'i" değil, ~13 km güneydeki araziyi kapsıyor; PLACES kontrolü de AOI'de 0 örnek buldu. Hikâye "Curiosity'nin ilk sondajı" ise AOI'yi John Klein/Cumberland çevresine (~lat -4.59, lon 137.44) koy.
- Neden: Challenge #1 (bilim hedefi -> uygun konum) ve jüri "hedefin gerçekten orada olduğu" kontrolü. Aksi halde APXS/CheMin ölçümünü yanlış arazide göstermiş olursunuz.
- Veri: MSL Gale DEM 1 m v3 (USGS Astrogeology, GeoTIFF), HiRISE LRGB COG (D02), PLACES localized_interp (JPL PDS, CSV). Tüm CRS ürün metadatasından; AGENTS.md'ye uygun.
- Not: Koordinat karşılaştırması benim hesabım (iki yerel dosyadan); HiRISE/DEM'in yeni AOI'yi kapsadığını DOĞRULAMADIM.

### E2. "Bilim hedefi cümlesi" + gerçek ölçümle başlayan hikâye: "Sheepbed çamurtaşı neden burada, yaşam için ne söylüyor"
- Ne: Tek soru: "Habitability kanıtı olan Sheepbed mudstone'u (John Klein, Cumberland) yerinde incelemek için hangi güvenli rota/durak seti?" Duraklar gerçek ölçüm hedefleridir (Wernecke_Brushed vb.).
- Challenge: #1, #2; jüri: Impact/Relevance.
- Veri: APXS supplement (PDS Geosciences, ds01_2020je006536rr.csv, 712 satır, oksit % + hata, GERÇEK ölçüm); CheMin (John Klein/Cumberland XRD, GERÇEK, kontrol dosyası CUMBERLAND_CHEMIN_URUN_KONTROLU.json mevcut); Strat sütunları (Yellowknife Bay/Sheepbed) jeolojik birim bağını verir.
- Jüride: haritada her durağa dokununca "Curiosity bunu sol 169'da ölçtü: MgO 9.8±0.25..." - NASA'nın kendi ölçümü astronot ekranında.

### E3. "Vardığında ne göreceksin": rover-POV panoramik ön izleme (Opsiyonel e)
- Ne: Her durak için gerçek Curiosity Mastcam/Navcam görüntüsü; astronot UE5'te durağa varmadan önce gerçek fotoğrafla karşılaştırır ("harita vs gerçek"). Ayrıca Perseverance Raw Images (Resources listesinde) ile Jezero ikinci sahada aynısı.
- Veri: MSL Navcam/Mastcam RDR (PDS Imaging / Analyst's Notebook an.rsl.wustl.edu, JPEG/IMG, GERÇEK); Perseverance raw images API/galeri (mars.nasa.gov/mars2020/multimedia/raw-images, JPG).
- Not: görüntü çekim konumu != gördüğü arazi (PLACES kontrol notu); yalnız konum+yön+DEM görüş hesabı onaylarsa "bu görüntü bu durağı gösterir" de.
- Jüri: en somut "wow": UE5 sahnesi ile gerçek rover fotoğrafı yan yana/yarım perde (swipe).

### E4. Katman sayısı: 3 değil 5+ gerçek veri türü, her katmana "karar etkisi" etiketi
- Ne: optik (HiRISE), topografik (DEM + MOLA), termal (THEMIS gece/gündüz IR), kimyasal (APXS), spektral/mineral (CheMin XRD; opsiyonel CRISM - doğrulanmadı), atmosferik (REMS), radyasyon (RAD). Her katman için "bu katman hangi kararı değiştirdi" satırı (örn. THEMIS termal inertia -> yumuşak toz/kaya tahmini -> teker/ayak batma riski).
- Challenge: #2 (3 tür) aşıldı; jüri: Technical/Data usage.
- Veri: THEMIS 100 m mozaik (mars.asu.edu, D10), MOLA MEGDR (PDS, D11), REMS MODRDR (PDS Atmospheres), RAD RDR (PDS PPI). Çözünürlük farkı (100 m / 463 m vs 1 m) güven katmanında görünür - bu sizin güçlü yanınız.
- Dikkat: THEMIS/MOLA yerel yürüyüş engelini çözmez; bölgesel bağlam olarak etiketle.

### E5. Radyasyon/uzay havası: gerçek RAD zaman serisinden "sol-bazlı doz bütçesi" + gerçek SEP olayı yeniden oynatma
- Ne: Demo krizindeki SEP uyarısını uydurma değil, gerçek bir olaydan yeniden oynat: MSL RAD'ın kaydettiği gerçek bir güneş olayı (örn. Eylül 2017 SEP olayı Curiosity RAD'da gözlendi - olay tarihi ve RAD'da görüldüğü bilgisini web'de DOĞRULAMADIM, hafızadan). Doz hızı zamanla "dönüş sınırı"nı daraltır.
- Challenge: #3 "radyasyon ve uzay havası"; jüri: Impact + Technical.
- Veri: MSL-M-RAD-3-RDR-V1.0 (pds-ppi.igpp.ucla.edu, GERÇEK doz hızı: yüzey, Gale içi, kabuk-korumasız), katalog uyarısı: counts vs doz vs insan maruziyeti ayrı. Astronot dozuna çeviri = SENARYO (etiketle). 
- Jüri: "Bu eğri Curiosity'nin gerçek ölçümü" rozetli zaman kaydırıcı; REDLINE çizgisi bu eğriyle canlı oynar.

### E6. Giysi hareketliliğini kaynaklı yap: eğim/engel parametreleri literatürden
- Ne: Giysi eğim ve engel eşiği için varsayım yerine kaynak (Apollo LRV/EVA yürüyüş eğim verileri, NASA xEMU/EVA literatürü) ve DEM'den türetilen eğim + kaya yoğunluğu rota maliyeti. Kaya yoğunluğu için AI4Mars (D15) veya HiRISE tabanlı kaya haritası türevi.
- Challenge: #4; jüri: Technical rigor.
- Veri: DEM eğim (gerçek türetilmiş), AI4Mars etiketleri (NASA/JPL, MSL+MER Navcam, insan etiketli; yörünge ölçüsü değil). Giysi eşiği: kaynak bulunamazsa "senaryo varsayımı" etiketle. Spesifik sayıları DOĞRULAMADIM.

### E7. Resources'ı kullanan "Mount Sharp / Trek / USGS jeoloji" katmanı + Mars Trek ile çapraz doğrulama
- Ne: USGS-NASA jeolojik haritadan birim sınırları (sahada Bradbury/Yellowknife Bay birimi) katman olarak; Mars Trek WMTS ile DEM/HiRISE'ı bağımsız doğrula ("kendi ürünümüz Trek ile uyuşuyor"); Curiosity "proposed path up Mount Sharp" haritasını gerçek geniş rota bağlamı olarak ilk ekran.
- Challenge: Resources listesi; jüri: sağlanan kaynakları kullanma. 
- Veri: USGS Astrogeology ArcGIS Hub (SIM 3292 benzeri jeolojik harita - kesin ürün ID'sini DOĞRULAMADIM); Trek (trek.nasa.gov/mars, WMTS/GDAL erişimi).

### E8. Çift astronot + rover "taşıyıcı" rolü haritaya yazılsın (Opsiyonel f)
- Ne: İki astronot görünümü: lider ve eşlikçi aynı haritayı paylaşır, "buddy mesafesi" REDLINE çizgisine girer (eş kurtarma süresi); rover numune/ekipman taşır, taşıma kapasitesi O2/süre bütçesini değiştirir.
- Jüri: insan-otonomi sorumluluğunu (madde 7) challenge'ın gerçek maddesiyle eşleştirir.
- Veri: simüle (senaryo); etiketli.

### E9. "Harita her saha için üretilir" sunumu: Jezero ikinci saha aynı manifestle (Opsiyonel b)
- Ne: Aynı manifest ile Jezero (Perseverance); D13 MEDA + Sample Dossier (D14) + Perseverance Raw Images. Dört dakikalık demoda "tek komut, ikinci gezegen sitesi" gösterilir.
- Veri: Mars 2020 MEDA calibrated env (PDS Atmospheres), Sample Dossier (PDS Geosciences). Jezero DEM/HiRISE CRS ürün metadatasından; Gale'e özgü varsayım yok.

### E10. Yeni, beklenmedik: "Dünya analoğu" yan panel (Worldview ile jüri bağı)
- Ne: Resources'ta NASA Worldview var (Dünya). Challenge "Dünya, Ay ve diğer varış noktaları için NASA haritalarından ilham" der. Haritaya, Dünya'da bir analog sahaya (çöl/Atacama ya da Utah) aynı katman arayüzünü uygulayıp Worldview gerçek verisiyle "aynı arayüz Dünya'da da çalışır" kanıtı. Ayrıca "ilham" maddesi için kısaca Ay/Apollo EVA traverse haritası (LROC/Apollo) karşılaştırma.
- Not: Bu ek özgünlük sağlar ama odağı dağıtabilir; yalnız 1 slayt/bir ekran yeterli.

## 3. Yeniden çerçevelenmesi gereken 3-5 şey
1. Kimlik: "Beş görevli robotik oyun" yerine "tek bir bilim yürüyüşü için güvenlik-farkında, katmanlı, kaynak-şeffaf harita". Görevler harita katmanını güncelleyen kanıt senaryoları olsun; vana/kaçak/eğitim/sınav görevi challenge'a hiçbir şey katmıyor (jüri incelemesi ile uyumlu).
2. "REDLINE çizgisi" iddiasını güvence değil, "açık modelle karar desteği + duyarlılık" olarak çerçevele; O2/giysi parametreleri varsayımlı etiketli; kesin "güvenli" deme.
3. "Gerçek / türetilmiş / simüle / senaryo" ayrımını sadece rozet değil, jüriye ilk 30 sn'de gösterilen bir "veri soy ağacı" ekranı yap; NASA ürününü çıkarınca ürünün çökmesi gerektiğini kanıtla (jüri itirazı: "NASA verisini çıkarınca oyun neden değişmiyor?").
4. Monte Carlo "önce/sonra" deneyini sonuçla değil soruyla çerçevele: "yörünge verisi ile rotada kalan bilinmeyen alan oranı kaç" - ölçüt rover gözlemi ile ölçülebilen ve harita yerine eklenen bilgi olsun; Monte Carlo'yu ana vitrin yapma.
5. "Interplanetary" başlığı gezegenler arası değil yalnız Mars'ta çok sahalı ve çoklu görev verili; abartma.

## 4. Doğrulayamadığın iddialar
- Resmî challenge metni (SSL hatası); alıntılar hackathlone özetinden.
- John Klein ile AOI arasındaki ~13 km mesafe: yerel dosyalardaki sayılardan kendi hesabım; ürünle yeniden hesaplamadım. Yellowknife Bay'in gerçek koordinatı da yalnızca APXS CSV satırından.
- Eylül 2017 SEP olayının MSL RAD'da görüldüğü (hafıza).
- USGS jeolojik harita ürün ID'si; CRISM kapsamı; giysi eğim eşiği sayıları; AI4Mars'ın yörünge ölçeğinde engel haritası vermeyeceği (katalog notuna dayanıyor).
- HiRISE LRGB COG ve DEM v3'ün yeni AOI'yi kapsadığı.
- PROJE_KILAVUZU.md'de beş görevin mevcut tanımı (okunmadı).
