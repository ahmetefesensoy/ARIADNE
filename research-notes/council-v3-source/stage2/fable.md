# Stage 2 incelemesi (fable)

Tarih: 2026-11-14. Yalnız okuma ve salt-okunur HTTP sorgusu yapıldı; proje dosyası değiştirilmedi.

## 0. Bu turda kendim kontrol ettiklerim

| # | Kontrol | Sonuç |
|---|---|---|
| V1 | Yerel organizatör kopyası (hackathlone) ham HTML | Açıldı. "You **may consider** including at least three kinds of data" birebir böyle; yani üç veri türü öneri, zorunluluk değil. "updates on current conditions", "boxwork formations ... Curiosity rover studied in 2025", "you might include space weather data", "transport the crew and their tools ... work in pairs", "hyperlocalized areas", "5 resources" ve Worldview bağlantısı metinde var. |
| V2 | PDS PPI `MSL-M-RAD-3-RDR-V1.0/DATA/SOL_00180_00269/` | Sol 241, 242, 243 dosyaları var. `RAD_RDR_2013_101_07_02_0242_V00.TXT` içinde `DOSIMETRY_TOTAL_DOSE_B` blokları 00–11: 9,277 / 8,898 / 9,540 / 10,732 / **12,132** / 11,550 / 11,071 / 10,848 / 10,518 / 10,446 / 10,265 / 10,258. Response A'nın serisiyle basamağına kadar aynı. |
| V3 | arXiv 2502.02469 | "Nowcasting Solar Energetic Particle Events for Mars Missions", Löwe ve ark., 4 Şubat 2025. Özet: "at least 25%", "at least 30 minutes", "near-zero false alarm rate", yüzeyde 16 olay. A'nın alıntıları doğru. |
| V4 | Mars Trek arama servisi (`searchItems?key=Gale`) | `Gale_DEM_SMG_1m` ("MRO HiRISE, Gale Crater DEM"), kapsam 137,122–137,730 / −4,925…−4,249. `Gale_CTX_BlockAdj_dd` de var. A'nın verdiği ad ve kapsam doğru. |
| V5 | Yerel `Gale_PLACES_AOI_KONTROLU.md` ve `APXS_HEDEF_ON_KONTROL.json` | Eski AOI: enlem −4,824993…−4,791252, northing −286.000…−284.000 m. John Klein (Wernecke_Brushed, sol 169): enlem −4,589485, northing −272.040 m. Fark 12–14 km. B ve D'nin "~13 km" bulgusu doğru. MgO 9,8 ± 0,25 (D'nin örneği) dosyada aynen var. |
| V6 | Yerel `SAHA_OLCUM_METADATA_KONTROLU.json` | PLACES filtresi gerçekten `sol in [182,279,1223,1225]`, eşleşme boş. CheMin John Klein etiketi "~22 +/- 11", "~28 +/- 15", "preliminary analysis" diyor (A ve B'nin alıntısı doğru). |

Kontrol etmediklerim: A'nın STAC, SIM 3292/3464, MMGIS, REMS JSON, Release 42 ve Grotzinger/Dehouck alıntıları; C'nin SEXTANT/BASALT ve Eylül 2017 sayıları; resmî challenge sayfası ve 2026 jüri rehberi.

---

## 1. Yanıtların tek tek değerlendirmesi

### Response A

**Doğruluk.** Sınadığım dört somut iddianın dördü de tuttu (V1–V4) ve bunlar yanıtın taşıyıcı iddiaları: challenge alıntıları birebir, RAD sol 242 serisi basamağına kadar doğru, Löwe eşiği doğru, Trek DEM kapsamı doğru. Diğer üç yanıtın hiçbiri bu düzeyde birincil kaynağa inmedi. §4'teki doğrulanmayanlar listesi dürüst ve ayrıntılı (birim tutarsızlığı, 18 blok sorusu, hesaplanmamış RMSE).

**Bulduğum kusurlar.**
- **Kadans sorunu söylenmemiş.** Sol 242'de 18 blok var; bu, blok başına yaklaşık 80 dakika demek. Löwe'nin "en az 30 dakika uyarı" iddiası bu çözünürlükte gösterilemez. E1'deki "sığınağa varış süresi ≤ uyarı süresi" isokronu bu RDR bloklarıyla değil, daha ince kadanslı bir ürünle ya da açık bir varsayımla kurulabilir. A bunu "blok UTC zamanlarını çıkarmadım" diye geçiştiriyor; oysa E1'in ana mekanizmasını etkiliyor.
- **Blok numaralaması belirsiz.** "4. ile 5. bloklar eşiği aşıyor" ifadesi dosyadaki 04 ve 05 indeksleri için doğru (12,13 ve 11,55 > 11,454), ama sıra sayısı olarak 5. ve 6. bloklar. Ekranda "blok 5: +%32" yazılacaksa indeks tabanı sabitlenmeli.
- **Alarm dedektöre bağlı.** A bunu kendisi söylüyor (E dedektöründe %24,1, eşik altı). Sonuç olarak "gerçek olay protokolü tetikledi" cümlesi yalnız B dedektörü için doğru; insan dokusuna daha yakın dedektörde alarm çıkmıyor. Bu, sunumda zayıf nokta olarak hazırlanmalı.
- **Eski deponun AOI uyumsuzluğunu görmemiş.** Yerel notlar okunabilir kaynak olarak verilmişti; A'nın önerdiği YKB çalışmaları için eski kırpımın 13 km güneyde kaldığını yazmıyor. Yeni depo sıfırdan kurulacağı için etkisi sınırlı, ama eski koordinatların taşınma riski var.
- **İnsan/giysi modeli boş bırakılmış.** REDLINE çizgisinin diğer yarısı (sarf, yürüme hızı, metabolik maliyet) "senaryo varsayımı" diye geçiliyor; C bunu çok daha iyi dolduruyor.
- E3'te Worldview için önerilen "etkileşim dilini ödünç alma" Relevance açısından zayıf bir bağ; A bunu abartmıyor ama "beş kaynağın beşine işlev" iddiası bu satırda incelir.

**İçgörü ve uygulanabilirlik.** En güçlü yanıt. Üç fikir kendi başına karar değiştirir: (1) YKB'de aynı yerde ölçülmüş gerçek SEP, (2) 2012 hedef seçiminin geriye dönük sınanması ve "CRISM kili göremedi" karnesi, (3) APXS koordinatının rover pozu olduğu bulgusu. Ürün kimlikleri, erişim yolları, biçim ve gerçek/türetilmiş statüsü neredeyse her satırda var. Boxwork'ü aynı Trek DEM içinde ikinci saha yapmak, challenge'ın kendi örneğine (V1) en ucuz bağ.

### Response C

**Doğruluk.** Challenge maddeleri doğru özetlenmiş, [D]/[H] etiketlemesi dürüst. Ancak:
- **"RAD'in yüzeyde gördüğü en büyük olay" (Eylül 2017) güncel değil.** Yerel notlar 20 Mayıs 2024 olayını (8.100 µGy iddiası) anıyor; bu değer doğrulanmamış olsa da 2017'nin hâlâ rekor olduğu söylenemez. Kaynak 2018 makaleleri; iddia o tarihte doğruydu.
- **Eylül 2017 olayı YKB'de değil.** Curiosity o tarihte Vera Rubin Ridge civarındaydı (hafızamdan). "Curiosity bunu bu kraterde ölçtü" doğru, ama A'nın "tam bu noktada" bağı C'de yok; saha–olay eşleşmesi daha gevşek.
- "At least three kinds" maddesini "Çekirdek" diye sınıflıyor; metin "may consider" diyor (V1).
- RAD dosyasına inmemiş (yalnız dizin ve AAREADME), DONKI açılmamış, Trek uç noktaları hafızadan. Kendisi de söylüyor.

**İçgörü.** A'nın boş bıraktığı yarıyı dolduruyor ve bu yüzden değerli: sınırlayıcı sarf mantığı, terminate/abort çift çizgisi, SEXTANT/BASALT'ın "gerçek süre tahminden uzun" bulgusunun marj çarpanına çevrilmesi, "güven katmanı renk değil marj üretmeli" çerçevesi, beş görevin tek EVA'nın evrelerine dönüştürülmesi (vana → giysi kaçağı). E4 (John Klein–Cumberland 2,75 m, bu bir yürüyüş değil) fikrin gerçek bir zaafını yakalıyor; diğer üç yanıt bunu görmedi. E8'deki görüş hattı kapsaması somut ve DEM'den türetilebilir.

**Zayıflık.** Veri tarafı A'ya göre belirgin biçimde daha az doğrulanmış; Navcam türev ürünleri, istasyon adları, SEXTANT katsayıları hafızadan. Uygulamadan önce bir doğrulama turu gerektirir.

### Response D

**Doğruluk.** 13 km AOI bulgusu doğru (V5) ve sayıları yerel dosyalarla tutuyor. MgO örneği doğru. Ancak:
- Challenge'ı yalnız araç özetinden okumuş, alıntı yok; "en az 3 veri türü"nü istek gibi yazıyor.
- Jüri ölçütleri tutarsız: bir yerde Impact/Relevance, başka yerde "Technical/Data usage", "Technical rigor" gibi beş ölçüt arasında olmayan adlar.
- Eylül 2017 olayı, SIM 3292, CRISM, giysi kaynakları hafızadan ve kendisi de doğrulamadığını söylüyor; ürün kimliği düzeyi katalogdaki D-kodlarının tekrarı.
- "Vana/kaçak/eğitim görevi challenge'a hiçbir şey katmıyor" ve "challenge'ın dışına taşıyor" ifadeleri brief'in yasakladığı kapsam tavsiyesine yaklaşıyor; C aynı görevleri yeniden bağlayarak daha yapıcı çözüyor.

**İçgörü.** Doğru yönde ama çoğu öneri A ve C'de daha derin hâliyle var. Özgün katkılar: "veri soy ağacı ilk 30 saniyede" ve "NASA ürününü çıkarınca ürün çökmeli" testi; her katmana "hangi kararı değiştirdi" satırı; AI4Mars'ın kaya yoğunluğu için kullanımı (uygunluğu doğrulanmamış). E10 (Dünya analoğu) odağı dağıtır; kendisi de kabul ediyor.

### Response B

**Doğruluk.** Red-team bulgularının bir kısmı sağlam: K1 (13 km) doğru, K4 (CheMin "preliminary", geniş belirsizlik) doğru, K5–K9 yerel notlarla tutarlı ve yerinde uyarılar. "At least three" ifadesinin zorunlu mu öneri mi olduğu şüphesi haklıydı; cevap "öneri" (V1).

**Hatalar ve zaaflar.**
- **K2/K3 teşhisi yanlış yönde.** 182 ve 279 John Klein ile Cumberland'ın sondaj solleri; "yanlış sol" değil. Sıfır eşleşmenin daha olası nedeni PLACES'ın yalnız poz değişiminde satır yazması (A: John Klein satırı site 6 / drive 0 / sol 166, Cumberland sol 274). B bunu "sorgu hatalı" diye sunuyor ve kendi iddiasının doğrulanmadığını da ekliyor; sonuç belirsiz bir suçlama.
- Resources'ın hiçbirini açmamış, hiçbir ürünü kontrol etmemiş; veri önerileri (G1–G8) katalogdaki bilinen satırların yeniden sıralanması. Soru "somut eklemeler" istiyordu; yeni veri ürünü neredeyse yok.
- Brief'e aykırı kapsam dili: "vaktine göre", "yalnız biri tam bitmişse", Unreal provasının "ana ürün olmaması".
- Worldview'un Dünya ürünü olduğunu bile teyit etmemiş ("Mars kapsamı doğrulanırsa").
- R1'i "Zayıf" saymak aşırı sert; diğer üç yanıt aynı maddeyi "İyi" buluyor ve gerekçeleri daha ikna edici.

**Değeri.** Eski deponun kusur listesi olarak yararlı, yeni fikri güçlendirme planı olarak en zayıfı. Ayrıca kusurların çoğu yeni depoda sıfırdan başlanacağı için kendiliğinden düşüyor.

---

## 2. Dört yanıtın da kaçırdıkları

1. **Eski "yanlış" AOI büyük olasılıkla boxwork tarafında.** Eski AOI (−4,825…−4,791; 137,428–137,462) ile A'nın verdiği boxwork kampanya kutusu (−4,798…−4,809; 137,379–137,386) aynı enlemde ve yaklaşık 3 km arayla duruyor (kaba hesap; A'nın MMGIS koordinatlarını doğrulamadım). B "eski araştırma Mount Sharp/boxwork kullanıyordu" diyor, B ve D 13 km farkı buluyor, A boxwork'ü öneriyor; ama kimse üçünü birleştirmedi. Sonuç: eski arazi kırpımı YKB için yanlış, boxwork ileri sahası için neredeyse doğru yerde.
2. **RAD kadansı ile uyarı süresi çelişkisi.** Yukarıda A için yazdığım nokta herkes için geçerli: hiçbir yanıt, yeniden oynatılacak ürünün zaman çözünürlüğünün "T dakikada sığınakta ol" kuralını gösterecek kadar ince olup olmadığını sormadı. Bu çözülmeden kriz sahnesinin zamanlaması gerçek değil, kurgu olur.
3. **Gerçek verinin iki motora aynı sözleşmeyle girmesi.** Brief yığını ve "açık frame/birim/saat sözleşmeleri"ni sabit veriyor; hiçbir yanıt buna veri tarafından bağlanmadı: aynı DEM'in Gazebo yükseklik haritası ve Unreal arazisi olarak tek kaynaktan üretilmesi, eqc harita frame'i → yerel ENU → site frame dönüşümü, sol/LMST ↔ UTC ↔ simülasyon saati eşlemesi (yeniden oynatılan RAD/REMS için zorunlu). Jüri açısından da "gerçek ölçüm simülasyonda nerede duruyor" sorusunun cevabı bu.
4. **Drone için gerçek veri çapası yok.** "Drone tarar" adımı dört yanıtta da simüle kaldı. REMS basıncı ve sıcaklığından hava yoğunluğu türetilip uçuş zarfına (uçulabilir saat penceresi) bağlanabilir; Ingenuity'nin uçuş kayıtları Jezero'da arşiv karşılığıdır. A ve C yalnız Ingenuity görüntülerini doğrulayamadıklarını yazdı.
5. **Yörüngeden kaya bolluğu.** Engel maddesi için herkes "DEM kayayı çözmez, robot çözer" dedi. Gale iniş elipsi için HiRISE gölge tabanlı kaya bolluğu haritaları yayımlandığını hatırlıyorum (Golombek ve ark.; doğrulamadım). Varsa, "yörünge önseli" ile "rover gözlemi" karşılaştırması gerçek veriyle yapılabilir ve D'nin AI4Mars önerisinden daha uygun bir üründür.
6. **Karşı-olgusal çizgi için gerçek büyük olay.** A, ağır senaryoyu "×k ölçekli" çiziyor; C, 2017'yi kullanıyor. Yerel notlardaki Mayıs 2024 olayı gerçekten daha büyükse, uydurma çarpan yerine "aynı kraterde, başka sol, gerçek ölçüm" olarak kullanılabilir. Kimse bu ürünü açıp doğrulamadı.
7. **Resmî sayfa ve 2026 jüri rehberi hâlâ okunmadı.** Dört yanıt da hackathlone kopyasına ve beş ölçütün adına dayanıyor. Ölçüt tanımları ve ağırlıkları, ayrıca yarışmanın önceden hazırlık kuralının indirilen veri ve araştırma notları için ne dediği teslimden önce birincil kaynaktan okunmalı.
8. **Veri hacmi ve erişim biçimi.** `Gale_DEM_SMG_1m` 5,78 GB; kimse pencere okuma (COG/WMTS/VRT kırpımı) ile tam indirme arasındaki tercihi ve bunun CRS/nodata sonuçlarını tartışmadı.

---

## 3. Sıralama gerekçesi

A, doğrulanabilirlik ve özgün içgörüde açık ara önde; sınadığım her iddiası tuttu. C, A'nın eksik bıraktığı insan/operasyon modelini kaynaklı biçimde dolduruyor ama veri iddiaları daha az sınanmış ve bir iddiası güncelliğini yitirmiş. D doğru yönde, kapsamlı ama sığ ve hafızaya dayalı. B'nin kusur avı kısmen isabetli, fakat sorunun istediği somut eklemeleri vermiyor, bir teşhisi hatalı ve brief'in kapsam kuralını çiğniyor.

FINAL RANKING:
1. Response A
2. Response C
3. Response D
4. Response B
