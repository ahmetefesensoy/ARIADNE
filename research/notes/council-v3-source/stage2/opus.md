# Stage 2 değerlendirmesi (opus)

## 0. Benim yaptığım doğrulamalar (13 araç çağrısı, salt-okunur)

| İddia | Kim | Sonuç |
|---|---|---|
| Challenge'da "You may consider including at least three kinds of data" (zorunlu değil, öneri) | A doğru alıntılıyor; B çelişkiyi işaretliyor; C "Çekirdek", D "istek" diyor | **Doğrulandı (hackathlone kopyası):** ifade "may consider". C ve D bunu gereksinim gibi sunuyor. Küçük ama jüri dilinde önemli. |
| "Interplanetary" yalnız başlık + Background'da | C | **Doğrulandı.** Objectives'te geçmiyor. |
| Resources'ın 3. maddesi | hepsi | Sayfadaki ad: "Example of a route map visual for the Curiosity example mentioned above". Yani bir **rota görselleştirme örneği**; veri kaynağı değil, tasarım dili referansı. A bunu en doğru okuyor ("açıklamalı rota ve flyover tasarım dili"). |
| Yerel AOI ile John Klein arasında ~13 km | D, B | **Doğrulandı.** AOI northing −286.000…−284.000 m (`Gale_PLACES_AOI_KONTROLU.md`), John Klein satırı northing −272.040 m (`APXS_HEDEF_ON_KONTROL.json`). Easting aralığı örtüşüyor, fark tamamen kuzey-güney: 12,0–14,0 km. A ve C bu hatayı **hiç fark etmemiş**. |
| APXS John Klein ve Cumberland satırları ~1 m ayrı; easting = boylam(rad) × 3.396.190 | A | **Doğrulandı.** Δeasting 1,01 m, Δnorthing 0,37 m (≈1,07 m). 137,4491296° → 8.147.255,6 m, satırdaki değerle aynı. A'nın "tablodaki konum hedef değil rover gövdesi" yorumu bununla tutarlı (PLACES eşleşmesini ben yeniden çalıştırmadım). |
| CheMin John Klein label'ı "preliminary", kil ~22±11, amorf ~28±15 | A, B | **Doğrulandı** (`SAHA_OLCUM_METADATA_KONTROLU.json`). |
| PLACES sorgusu `sol in [182,279,1223,1225]`, 0 eşleşme | B | **Doğrulandı.** B'nin "sonuç anlamsız olabilir" uyarısı doğru. Gerçek açıklama büyük olasılıkla A'nınki: PLACES satırları sol başına değil site/drive olaylarına bağlı. Rover sondaj sollerinde park hâlindeydi. B'nin önerdiği "APXS sollerine geç" düzeltmesi de aynı nedenle boş dönebilir. |
| RAD dosyası `SOL_00180_00269/RAD_RDR_2013_101_07_02_0242_V00.TXT` | A | **Dosya var.** İlk bloğun `DOSIMETRY_TOTAL_DOSE_B` = 9,27688; A'nın serisi "9,28 → …" ile başlıyor. Zirve değerini (12,13) dosya 6,5 MB olduğu için ben okumadım. |
| Löwe ve ark. 2025, arXiv 2502.02469: %25 eşik, ≥30 dk uyarı, "near-zero" yanlış alarm, yüzeyde 16 SEP | A | **Doğrulandı** (başlık: "Nowcasting Solar Energetic Particle Events for Mars Missions"). |
| Trek `Gale_DEM_SMG_1m`, "MRO HiRISE, Gale Crater DEM", 5,78 GB, lon 137,12–137,73, lat −4,93…−4,25 | A | **Birebir doğrulandı.** Bu kutu hem YKB'yi (−4,59) hem mevcut AOI'yi kapsıyor. |
| Mars Trek katalogda yok | B | **Yanlış.** `KAYNAK_VE_VARLIK_KATALOGU.md` içinde **D17 NASA Mars Trek WMTS** satırı var ("servis doğrulandı; tekil ürün/kapsam denenmedi"). A'nın "işlevsel olarak kullanmıyor" ifadesi ise savunulabilir. |
| Yerel ağ 4 m | B | **Doğru.** D01 satırı "Yerel 2×2 km kırpım ve 4 m görsel/fizik ağı" diyor. |
| Eylül 2017 olayı "RAD'in yüzeyde gördüğü en büyük olay" | C | **2026 için yanlış (eskimiş).** NASA, 20 Mayıs 2024 olayını Curiosity RAD'in inişten beri ölçtüğü en büyük artış olarak duyurdu: ~8.100 µGy, ~30 göğüs röntgeni. Eylül 2017 rekoru 2018 makaleleri için doğruydu. |

---

## 1. Yanıtların tek tek değerlendirmesi

### Response A (veri bilimcisi merceği)

**Doğruluk.** Dört yanıt içinde açık ara en çok birincil kaynağa dayanan yanıt bu. Benim kontrol ettiğim her somut iddia tuttu: RAD dosya yolu ve ilk değer, Löwe 2025 sayıları, Trek DEM kimliği ve kutusu, APXS koordinat semantiği, CheMin label'ı. Ayrıca doğrulayamadıklarını tek tek ve dürüstçe listeliyor: sol 242 blok sayısı, birim belirsizliği, MMGIS'in arşiv olmaması.

**İçgörü.** Üç şey öne çıkıyor:
- **"2012 kararı yeniden üretilir" (E2).** Grotzinger 2014'ün termal atalet + HiRISE ile YKB seçimini ve CRISM'in toz yüzünden kili kaçırmasını bir "isabet/kaçırma karnesi" hâline getiriyor. Bu, önce/sonra deneyini simülasyondan arşive taşıyor ve Validity için en güçlü öneri.
- **APXS koordinatı = rover pozu bulgusu.** AGENTS.md'deki "numune kökeni ≠ analiz konumu" ilkesinin gerçek veriyle kanıtı.
- **Üç bağımsız HiRISE DTM + PLACES tilt ile ampirik eğim σ'sı.** "Güven katmanı"nı elle verilen bir değer olmaktan çıkarıp ölçülebilir hâle getiriyor.

Resources tablosu da beş kaynağa somut işlev veriyor. Worldview'ün Mars'ta olmadığını doğru tespit ediyor ve onun swipe ve zaman etkileşimini ödünç alıyor. Jezero'da RAD benzeri dozimetre olmadığı için "eksik katman beyanı" da iyi bir fikir.

**Hatalar ve eksikler.**
1. **En büyük eksik:** Yerel AOI'nin YKB'den ~13 km güneyde olduğunu fark etmemiş. Bütün tez YKB üzerine kurulu, ama projenin mevcut arazi kırpımı orada değil. Trek DEM önerisi pratikte sorunu çözüyor, fakat yanıt bunu açıkça söylemiyor.
2. **Sol 242 olayı zayıf.** Olay +%30, ~50 µGy. A dürüstçe "karşı-olgusal ×k" çizgisi öneriyor. Oysa gerçek ve büyük bir olay var: Mayıs 2024. A bunu yalnız "doğrulanmamış yerel not" diye geçiyor. Ölçekli kurgu yerine gerçek ikinci bir olay kullanılabilirdi.
3. Çok uzun. Bazı ayrıntılar (DTM provenance'ta UInt16/Float32 tutarsızlığı) jüri değeri düşük, doğrulanmamış süs.

**Uygulanabilirlik.** Ürün kimlikleri, uç noktalar ve hücre şeması hazır. Ekip doğrudan iş listesine çevirebilir.

### Response B (red-team)

**Doğruluk.** Red-team bulgularının çoğu doğru ve karar açısından önemli. K1 (13 km) doğrulandı. K4 (CheMin "preliminary") doğrulandı. K5 (HiRISE görüntüsü 2008, iniş öncesi) A'nın verdiği tarihle tutarlı. K6 ("bbox ≠ hizalama") ve K7 (4 m ağ) yerel dosyalarla tutarlı. "Üç veri türü zorunlu mu?" belirsizliğini işaretlemesi de doğru içgüdüydü; cevap "öneri" çıktı.

Hatalar:
- "Mars Trek katalogda yok, D-19 olarak eski araştırmada" yanlış. Katalogda D17 olarak var.
- Worldview'ün Mars kapsamını "doğrulanırsa" diye açık bırakıyor. Worldview yalnız Dünya'yı gösterir; bu basit bir kontrolle kapanırdı.
- K2'deki düzeltme önerisi (APXS sollerine geçmek) muhtemelen yine boş dönecek. Doğru anahtar site/drive.

**İçgörü.** "Survival oyunu mu, EVA karar aracı mı?" çerçevesi ve "her robot görevi tek delta yazsın, o delta bir karar değiştirsin" ilkesi yerinde. "Yanlış yer iddiası jüride ilk ceza" uyarısı da doğru.

**Eksikler.** Geliştirme listesi (G1–G8) büyük ölçüde katalogdaki adayların yeniden sıralanması. Yeni ürün kimliği yok, tek bir canlı sorgu yok. Kuvveti eleştiride, önerilerinde değil. Bu, yanıtın kendi rolüyle tutarlı ama sorunun "somut eklemeler" kısmını zayıf bırakıyor.

### Response C (EVA operasyon merceği)

**Doğruluk.** Challenge tablosu metne sadık; "interplanetary" tespiti doğru. İki hata var:
- Eylül 2017'yi "RAD'in yüzeyde gördüğü en büyük olay" diye sunuyor. 2024'ten beri bu doğru değil. Jüride bir bilimci bunu düzeltebilir.
- "En az üç veri türü"nü "Çekirdek" diye işaretliyor; metin "may consider" diyor.

Navcam türev ürün tipleri (XYZ/RNG/UVW/SLP/RUF), istasyon adları ve SEXTANT bulgusu hafızaya ya da arama özetine dayanıyor. C bunları dürüstçe [H] olarak etiketlemiş. AOI'nin 13 km kaymasını o da kaçırmış.

**İçgörü.** Dört yanıt içinde operasyonel olarak en olgun olanı:
- **John Klein–Cumberland ~2,75 m: "bu bir yürüyüş değil, tek istasyon".** Bu tespit traverse'in ölçeğini düzeltiyor ve gerçek istasyon dizisi (Rocknest → Sheepbed) önermesi doğru.
- **Terminate/abort çizgileri** ve "çizgiyi en kısıtlı sarf çizer, hangisi olduğu ekranda yazar". REDLINE çizgisini gerçek EVA terminolojisine bağlıyor.
- **BASALT/SEXTANT'ın "gerçek süre > tahmin" bulgusu** marj çarpanının kaynağı olarak kullanılıyor.
- **Vana/kaçak görevinin giysi kaçağı acil durumuna dönüşmesi.** Eski beş görevi challenge'a bağlayan en zarif öneri.
- **DEM viewshed ile iletişim kapsama katmanı** ve rover'ın röle rolü.
- **PET zaman çizelgesi ve cuff checklist** çıktısı.
- "Güven katmanı renk değil marj üretmeli" çerçevesi. Bu, A'nın ölçülebilir σ önerisiyle birleşince çok güçlü.

**Uygulanabilirlik.** Yüksek, ama veri tarafında A kadar doğrulanmış kimlik yok. RAD alan adlarını ve DONKI'yi açamadığını kendisi söylüyor.

### Response D (ürün/hikâye merceği)

**Doğruluk.** AOI–John Klein ~12–14 km hesabı doğru; northing değerleri dosyalarla birebir tutuyor. "MgO 9,8±0,25" doğru. Hatalar:
- Jüri ölçütlerini "Technical/Data usage", "Technical rigor" diye adlandırıyor. Space Apps'in beş ölçütü (Impact, Creativity, Validity, Relevance, Presentation) ile eşleşmiyor.
- Challenge'ı "radyasyon ve uzay havası öncelikli" diye abartıyor; metin "might include space weather data" diyor.
- "REDLINE yalnız USGS DEM'ini (D01) kullanıyor": D01, Resources'taki PGM sayfası değil. C bu ayrımı doğru yapıyor.
- Eylül 2017 olayını hafızadan alıyor ve doğrulamadığını söylüyor. Bu dürüst, ama yeni bilgi eklemiyor.

**İçgörü.** E1 (AOI'yi taşı) gerçekten kritik ve D bunu en üste koymuş. Bu doğru bir önceliklendirme. "Veri soy ağacı ekranı ilk 30 sn'de" ve "NASA ürününü çıkarınca ürün çökmeli" sunum açısından iyi fikirler. POV görüntüsünde "çekim konumu ≠ görülen arazi, viewshed onaylarsa eşleştir" notu da doğru.

**Eksikler.** Daha az dosya okunmuş (PROJE_KILAVUZU okunmamış). Önerilerin çoğu katalog adaylarının listelenmesi. Worldview ile Dünya analoğu (E10) yaratıcı ama challenge'ın ana isteklerine katkısı düşük. AI4Mars'ı "kaya yoğunluğu" için önermesi zayıf: AI4Mars bir Navcam arazi sınıflandırma etiket seti, yörünge ölçekli bir kaya haritası değil (D bunu kısmen belirtiyor).

---

## 2. Bütün yanıtların kaçırdığı önemli noktalar

1. **Mevcut AOI "yanlış yer" değil, potansiyel bir "çalışılmamış saha".** D ve B kaymayı buldu ama yalnız "AOI'yi YKB'ye taşı" dedi. Oysa:
   - AOI'nin enlemi (−4,791…−4,825), A'nın verdiği boxwork kampanyası enlemiyle (−4,798…−4,809) örtüşüyor.
   - Boylamca kampanyanın ~2,5–5 km doğusunda kalıyor (A'nın MMGIS koordinatlarına göre; ben doğrulamadım).
   - PLACES'te AOI içinde hiç rover örneği yok.
   - Challenge açıkça "an area that hasn't been studied as closely" seçeneğine izin veriyor.

   Bu yüzden en güçlü kurgu şu olabilir: **YKB = kalibrasyon/karne sahası (A-E2), mevcut AOI veya boxwork-Batı = robotun bilinmeyeni çözdüğü ileri EVA sahası (A-E6).** Böylece yerel araziyle yapılmış iş boşa gitmez ve 13 km tutarsızlığı bir hikâye unsuruna dönüşür. Önce AOI'nin neden orada seçildiğine bakılmalı (B, eski araştırmanın boxwork/Mount Sharp kullandığını söylüyor). Ardından Trek `Gale_DEM_SMG_1m` ve HiRISE DTM kapsaması iki saha için de ayrı ayrı kontrol edilmeli.

2. **20 Mayıs 2024 SEP olayı.** RAD'in inişten bu yana ölçtüğü en büyük olay (~8.100 µGy). NASA aynı olayı MAVEN ile de gözledi ("largest SEP event MAVEN has ever seen", aurora). Bunun iki faydası var:
   - Gerçek, büyük ve **çok görevli** (MSL RAD + MAVEN SEP/IUVS) bir uzay havası veri seti sağlıyor. Bu, Summary'deki "multiple NASA science missions" isteğine doğrudan hizmet ediyor.
   - A'nın "karşı-olgusal ×k" çizgisine ve C'nin eskimiş 2017 rekoruna gerek bırakmıyor.

   En iyi kurgu iki gerçek olay: sol 242 (aynı saha, düşük doz, protokol tetikleyici) ve Mayıs 2024 (yüksek doz, ALARA ve sığınak kuralı). Basın bültenlerine göre Curiosity'nin navigasyon kameraları bu olayda parçacık çarpmalarını görüntülerde iz olarak kaydetti. Ben bunu doğrulamadım, ama doğruysa POV katmanı için çarpıcı bir kanıt.

3. **Teslim biçimi jüri etkisini belirler.** Hiçbir yanıt Space Apps teslim kurallarına bakmamış. Hafızama göre (doğrulamadım) proje sayfası bir demo bağlantısı ister: kısa bir video ya da sınırlı sayıda slayt. Global jüri canlı ROS/Unreal çalıştırmaz. "Jüride nasıl görünür" önerilerinin hepsi (bölünmüş ekran, kaydırıcı, karne) bu kayıtlı formata göre tasarlanmalı. 2026 Judging Guide ağırlıkları da kimse tarafından okunmadı.

4. **A ve C birbirini tamamlıyor.** A'nın ampirik σ'sı ile C'nin "güven = marj (dakika)" çerçevesi birleşince güven katmanı ölçülmüş bir zaman maliyetine dönüşür. Hiçbir yanıt bu iki fikri açıkça birleştirmedi. "Bilinmeyen hücre → eğim σ ve tespit sınırı altı kaya olasılığı → hız cezası → dönüş isokronu" zinciri, REDLINE'ın merkez tezini tek denklemde gösterir.

5. **Işık süresi ve otonomi.** Ayrıntılı ele alınmamış. A güneş kavuşumunu, C ise yerel MCC'yi andı, ama hiçbiri seçilen sollerdeki gerçek Dünya–Mars ışık süresini SPICE'tan hesaplayıp "neden yerel otonom alarm" gerekçesine sayı olarak koymadı.

---

## 3. Sıralama gerekçesi

- **A** en çok doğrulanmış gerçek veri zincirine ve en özgün Validity önerisine (2012 kararının yeniden üretimi) sahip. AOI kaymasını kaçırması ciddi ama Trek DEM önerisiyle telafi edilebilir.
- **C** operasyonel içgörüde en iyisi ve uygulanabilir. Eskimiş SEP rekoru ve AOI eksikliği onu A'nın gerisinde bırakıyor.
- **B**'nin red-team bulguları çoğunlukla doğru ve karar açısından önemli. Katalog konusunda bir olgu hatası var ve önerileri yüzeysel.
- **D** AOI hatasını öne çıkarıyor, ama jüri ölçütlerini yanlış adlandırıyor, daha az kaynak okumuş ve yeni veri katkısı en az.

FINAL RANKING:
1. Response A
2. Response C
3. Response B
4. Response D
