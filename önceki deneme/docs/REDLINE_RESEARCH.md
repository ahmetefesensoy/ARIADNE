# REDLINE

> **Araştırma arşivi · 31 Ekim 2026.** Bu dosya önceki geniş planın kaydıdır. Güncel tek uygulama kapsamı ve çalışan demo için [REDLINE.md](../REDLINE.md) dosyasına bakın. Aşağıdaki “kod yok” beyanları arşivlendiği andaki planı anlatır; klasörün güncel durumunu anlatmaz.

**İnsanlı Mars yürüyüşleri (EVA) için hiper-yerel katmanlı harita, planlama ve güvenlik sistemi**

| | |
|---|---|
| Takım | CRST |
| Etkinlik | NASA Space Apps Challenge 2026, Ankara |
| Challenge | Interplanetary Survival Guide: Martian Map |
| Belge | Tasarım belgesi v0.4, fikir ve araştırma aşaması |
| Tarih | 31 Ekim 2026 |
| Sonraki revizyon | 13 Kasım 2026 (Resources sekmesi açılınca) ve H0 |

> **Kural sınırı.** Space Apps kuralları proje çalışmasının 14 Kasım 2026 09:00'dan (Ankara) önce başlamasını yasaklıyor; ihlal diskalifiye sebebi olabilir. Bu belge yalnızca fikir, araştırma ve planlama içerir. Kod, mesaj/arayüz dosyaları, sahaya özel veri işleme ve sunum materyali bu belgede yok; hepsi H0'dan sonra üretilecek. Buradaki sayısal örnekler ya literatürden alındı ya da elle yapılmış kaba hesaplardır ve H0'dan sonra gerçek veriyle yeniden hesaplanacak. Sınırdan emin olunmayan her konu Ankara etkinlik sorumlusuna sorulacak.

**Notasyon**

- **H0** = 14 Kasım 2026 09:00 (Ankara). **Hn** = H0 + n saat. Son teslim anı H38:59 (15 Kasım 23:59). Hedef teslim H38 (23:00).
- **(teyit)**: Uygun ilk fırsatta birincil kaynaktan doğrulanacak bilgi veya parametre.

**v0.4 jüri denetimi (31 Ekim 2026).** Bu belgenin eleştirel incelemesi ve daraltılmış teslim önerisi [JURI_DEGERLENDIRME.md](../JURI_DEGERLENDIRME.md) dosyasındadır. Bölüm 10 ve 15 geniş tasarım uzayını korur; yarışma teslimi için başlangıç kapsamı değerlendirme dosyasındaki tek saha, tek harita, tek karar döngüsüdür.
- **Kaba hesap**: bu belgede elle yapılmış, gerçek veriyle yeniden yapılacak örnek hesap.
- **Kimlik önekleri**: CH challenge gereksinimi · A varsayım · SS alt sistem · D veri seti · L katman · M teorik modül · FR uçuş kuralı · OFF arıza senaryosu · V doğrulama deneyi · R rol · G karar kapısı · RK risk · Q açık soru · E eklenti.

**v0.3 değişiklikleri (31 Ekim 2026)**

- **Yeni Bölüm 15:** 14 eklenti (E-01–E-14), seçim matrisi ve önerilen seçki.
- **Yeni 6.12:** eklenti mimarisi ve ara katman haritası (PX4 uORB, Zenoh, ROS 2, cFS, F´, Bundle Protocol).
- **Yeni 1.6:** NASA Moon to Mars hedefleriyle eşleme.
- **SEP tasarımı güncellendi (v0.3 varsayımı).** Löwe ve ark. (2025) inceledikleri olaylarda tepe dozdan önce yaklaşık 30 dakikalık fırsat bildiriyor. v0.4'te bu süre evrensel güvenlik garantisi değil, olay bazında sınanacak bir girdi olarak ele alınıyor.
- **M1:** Kluis ve ark. (2025) kalibrasyon verisi eklendi.
- **M3:** Khaksarighiri ve ark. (2025) tepki matrisleri ve Charpentier ve ark. (2025) nötron/arazi bulgusu eklendi.
- **Diğer:** A-13 (yüzey gücü, ACR 2024 fisyon kararı); D-20–D-22; V10–V12; yeni riskler, sorular ve hazırlıklar.

## İçindekiler

0. Özet
1. Challenge analizi
2. Görev konsepti (ConOps)
3. Sistem mimarisi
4. Veri ve katmanlar
5. Teorik modüller (M1–M11)
6. Yazılım tasarımı
7. Doğrulama planı (V1–V8)
8. Demo ve teslim
9. Takım organizasyonu
10. 39 saatlik uygulama planı
11. Risk kaydı
12. H0 öncesi hazırlık (kurallara uygun)
13. Açık sorular
14. Sözlük
15. Eklentiler (E-01–E-14)
16. Kaynaklar

---

## 0. Özet

**Problem.** Challenge metninin işaret ettiği boşluk şu: Mars Trek ve USGS haritaları bölgesel ya da küresel ölçekte. Tek bir yürüyüşün ihtiyaç duyduğu metre ölçekli, insana ve güvenliğe göre hazırlanmış katmanlar yok. Bir astronot için asıl soru "bu bölgenin eğimi ne?" değil. Asıl soru şu: "Şu noktadan, kalan oksijenimle, bu skafanderle, bu radyasyon koşullarında rovera dönebilir miyim?"

**Çözüm.** REDLINE, NASA'nın yörünge, rover ve uzay havası verilerinden katmanlı bir EVA haritası üretmeyi hedefler. Astronotun sarf malzemesi ve rover konumunu kullanarak her noktaya bir **tahmini geri dönüş bedeli** atar. Bu bedelin kullanılabilir rezerve eşitlendiği eğri, projeye adını veren **kırmızı çizgidir**. Çizginin içi, kullanılan veri, model ve varsayımlar altında hesaplanan geri dönüş alanıdır; gerçek görev güvenliği garantisi değildir. Çizgi sarf malzemesi tükendikçe daralır. SEP senaryosunda ayrı bir sığınağa erişim sınırı gösterilir.

**Kullanıcının gördüğü dört yüzey:**

1. **Habitat ekranı** (basınçlı roverın içinde): EVA öncesi planlama ve plan doğrulama.
2. **Kask HUD'u** (Unreal Engine 5 + Cesium Mars): kırmızı çizgi doğrudan arazinin üstünde.
3. **Bilek tableti**: sadeleştirilmiş harita ve geri sayım.
4. **Dünya'daki görev kontrolü**: DTN üzerinden, 3–22 dakika gecikmeli.

**Arkadaki teknoloji:**

- Python veri hattı ve C++20 planlayıcı
- ROS 2 Jazzy + rmw_zenoh
- NASA'nın FRET → Ogma → Copilot zinciriyle üretilen gerçek zamanlı güvenlik izleyicileri
- ION/HDTN ile DTN
- Space ROS Curiosity modeli + Nav2 + Gazebo
- TypeScript/CesiumJS konsolları

**Eklentiler (v0.3).** Çekirdeğin üstüne, tek tek açılıp kapatılabilen 14 eklenti tasarlandı (Bölüm 15). Öne çıkanlar:

- belirsizliği uçarak azaltan bir Mars helikopteri (SCOUT),
- NASA uçuş yazılımı katmanı (cFS + JAXA'nın RACS2 köprüsü, F´),
- Curiosity görüntüleriyle santimetre ölçekli arazi füzyonu ve Gaussian splat görselleştirme,
- 30 sollük kampanya planlayıcısı,
- model denetimiyle kanıtlanmış mod yöneticisi,
- Türkiye'deki Salda Gölü ile Jezero'yu eşleyen analog modu.

Eklentilerle birlikte sistem altı farklı haberleşme dünyasını birleştiriyor: PX4 uORB, Zenoh, ROS 2, cFS yazılım veri yolu, F´ portları ve Bundle Protocol.

**Demo hikâyesi.** 20 Mayıs 2024 uzay havası olayını boxwork sahasındaki varsayımsal insan EVA'sına uyguluyoruz. Bu, aynı yerde ve tarihte gerçekleşmiş bir ölçümün yeniden oynatımı değildir.

- O gün Güneş'in Dünya'dan görünmeyen yüzünde bir patlama oldu. Solar Orbiter bu patlamayı X12 sınıfı olarak tahmin etti. Parçacıklar Mars'a onlarca dakikada ulaştı.
- Curiosity'nin RAD dedektörü 8.100 µGy ölçtü; bu, inişten beri ölçülen en büyük sıçrama.
- Curiosity o sırada Gediz Vallis çevresindeydi; boxwork kampanyası 2025'te başladı. RAD dozu başka bir noktada ölçüldü. Boxwork'e aktarımı senaryo varsayımı ve belirsizlik kaynağıdır.

Sorumuz: **O olayın ölçülmüş zaman çizelgesi boxwork sahasında yaşansaydı, modeldeki iki astronot sığınağa yetişebilir miydi?** Olayın zamanı ve Curiosity RAD kaydı gerçektir; EVA, konumlar arası doz aktarımı, skafander ve sığınak varsayımsaldır. Sonuç yalnızca bu koşullu senaryo için raporlanır.

**Fikir cümlesi (İngilizce):** *REDLINE turns NASA orbital, rover and space-weather data into a hyperlocal, physiology-aware safety map for a two-person Mars EVA, and keeps the crew inside a formally verified red line even when Earth is twenty minutes away.*

**Jüri gözüyle güçlü yanlar**

| Kriter | Dayanak |
|---|---|
| Relevance | Challenge'ın Marswalk haritası, güvenlik ve bilim hedefiyle doğrudan ilişkili bir plan var (Bölüm 1.1); uygulama kapsamı ayrıca daraltılmalı |
| Validity | Curiosity rotası, RAD, NASA skafander testleri ve Navcam ile sınanabilecek hipotezler listelendi (Bölüm 7); test sonuçları henüz yok |
| Creativity | Roverı hareketli güvenli liman olarak optimize etmek; arazinin radyasyon gölgesi; tek ufuk hesabının üç ayrı kullanımı |
| Impact | Senaryo NASA'nın 2024 Mars yüzey mimarisiyle uyumlu; veri hattı başka sahalara taşınabilir; skafander tasarımı için "ya şöyle olsaydı" aracı |
| Presentation | Gerçek 2024 uzay havası olayı üzerine kurulu karşı-olgusal senaryo; canlı sahne henüz yapılmadı |

---

## 1. Challenge analizi

### 1.1 Gereksinim izlenebilirliği

| ID | Challenge beklentisi | REDLINE karşılığı | Demoda nerede görünür |
|---|---|---|---|
| CH-01 | EVA ölçeğinde hiper-yerel harita (Mars Trek/USGS'den ayrıntılı) | 25 cm görüntü + 1 m arazi üzerinde 20+ türetilmiş katman (Bölüm 4.3) | Video 0–12 sn; habitat ekranı |
| CH-02 | En az 3 veri türü | Görüntü, arazi, termal atalet, spektral (CRISM), radyasyon (RAD), meteoroloji (REMS, MGCM), geometri (SPICE), uzay havası (DONKI), rover görüntüleri | Proje sayfasındaki veri tablosu |
| CH-03 | Güvenlik öncelikli: radyasyon ve uzay havası | M3 topografik radyasyon, SEP modu, uyarı bütçesi, sığınağa ulaşma süresi | SEP sahnesi |
| CH-04 | Skafander ve ekipmanın hareket kabiliyetine etkisi | M1 metabolik model (NASA EWT/IST verisiyle kalibre), hız ve eğim sınırları | Rota maliyetleri; HUD sarf göstergeleri |
| CH-05 | Büyük kayalardan kaçınan rota | M2: gölgeden kaya tespiti + Golombek modeli + Poisson karşılaşma olasılığı | Rota katmanı; HUD kaya vurgusu |
| CH-06 | Bilim hedefi (ör. Mount Sharp boxwork) | M5 bilim değeri (hipotezler arası bilgi kazancı), M7 durak seçimi | Bilim kartları; posterior güncellemesi |
| CH-07 (ops.) | Habitat ekranı / tablet / kask HUD | Üçü de var, ek olarak Dünya konsolu | Tüm demo |
| CH-08 (ops.) | Rover bakış açısından görüntüler | Navcam/Mastcam panoramaları: UE5 görsel doğrulaması ve ufuk eşleştirme testi (V6); E-03 yer–yörünge arazi füzyonu ve Gaussian splat | Lokalizasyon sahnesi; yakın plan görüntüler |
| CH-09 (ops.) | İkili çalışan astronotlar / rover desteği | EV1+EV2 buddy kuralları; rover hareketli güvenli liman (M8); E-01 SCOUT helikopteri | Rover yer değiştirme sahnesi; SCOUT uçuşu |
| CH-10 (ops.) | Başka yerler için de harita üreten sistem | Veri hattı AOI parametreli ve STAC kataloglu; Jezero ile tekrar (Cesium Mars'ta 6 m görüntü / 20 m arazi var); E-11 Salda ↔ Jezero analog modu; E-13 Ay portu | Kapanış |

### 1.2 Jüri kriterleri ve strateji

Space Apps jürisi beş kriteri 1–5 arasında puanlıyor. Değerlendirme yolu şöyle: yerel jüri → Global Nominee → Global Finalist → 10 Global Winner.

| Kriter | Jürinin muhtemel sorusu | Cevabımız | Kanıt |
|---|---|---|---|
| Impact | Bu gerçek bir göreve ne katar? | “Ne kadar uzağa gidilir?” kararını planlama senaryosunda görünür kılabilir; gerçek görev güvenliği ayrıca doğrulama ister | Aynı sahada iki rota ve varsayım duyarlılığı |
| Creativity | Bu bir harita mı, yeni bir şey mi? | Harita bir karar alanına dönüşüyor: geri dönüş bedeli, kırmızı çizgi, hareketli güvenli liman | M6, M8 |
| Validity | Sayılar nereden geliyor? | Kaynak kökeni, işleme adımı ve ölçülmeyen varsayımlar ayrı gösterilmeli | Bölüm 4; gerçek deney sonucu H0 sonrası |
| Relevance | Bu challenge'a mı uyuyor, yoksa kendi projenize mi? | İzlenebilirlik tablosu; boxwork bilim hedefi; radyasyon ve uzay havası birinci sınıf bileşen | 1.1 |
| Presentation | 30 saniyede anlaşılıyor mu? | Tek haritada iki rota, daralan dönüş sınırı ve varsayım etiketi | Bölüm 8; jüri değerlendirmesi |

### 1.3 Ödül kategorisi hedefleri

- **Birincil:** Best Use of Science, Best Use of Technology, Best Mission Concept.
- **İkincil:** Best Use of Data, Galactic Impact, Best Storytelling.
- 2026 kategori listesi resmi sayfadan teyit edilecek.

### 1.4 Yenilik iddiaları

Bileşenlerin her biri literatürde ayrı ayrı mevcut. Bildiğimiz kadarıyla aşağıdakiler bir insan EVA'sı için birlikte kurulmamış (H0 sonrası hızlı literatür kontrolü yapılacak):

- **N1. Topografik GCR koruma haritası.** Kapalı formda hesaplanır (M3) ve RAD ölçümleriyle doğrulanır. Khaksarighiri ve ark. (2025, JGR Planets) zenit açısına bağlı tepki matrislerini çıkarıp topografik haritayı bir sonraki çalışmaya bırakıyor.
- **N2. Roverın zaman indeksli güvenli liman olarak yerleşimi.** Darboğaz dinamik programlamasıyla kesin çözüm (M8).
- **N3. Ortak güvenlik kuralı tanımları.** Planlayıcı kısıtı, senaryo sınaması ve çalışma zamanı izleyicisi aynı kural kimliklerine bağlanır; uygulama eşdeğerliği ayrıca sınanır (M9).
- **N4. Belirsizlik zinciri.** DTM güven haritası → eğim σ → şans kısıtı → kırmızı çizgi.
- **N5. SEP uyarı bütçesi.** 20 Mayıs 2024'ten çıkan ders: Dünya kör olabilir. Yerel dozimetre nowcast'ı (Löwe ve ark. 2025) alarm kaynağı adayıdır. Her olayın alarm zamanı, sığınak erişimi ve varış öncesi dozu ayrı sınanır; yaklaşık 30 dakikalık literatür sonucu her senaryo için garanti sayılmaz (M3, FR-03).
- **N6. Tek ufuk küpü, üç kullanım.** Radyasyon koruması, gölge takvimi ve ufuk çizgisiyle konum belirleme aynı hesaptan beslenir.

### 1.5 Kapsam dışı

- Gerçek skafander donanımı ya da tıbbi doğruluk iddiası. Fizyoloji modeli kalibre edilmiş ama basitleştirilmiş.
- Gerçek RF yayılım fiziği. Görüş hattı + basit yol kaybı modeli kullanılıyor.
- "Uçuşa hazır yazılım" iddiası. İddiamız şu: yöntem doğru ve gerçek veriyle test edildi.
- ML modelinin literatürün en iyisi olması. ML yalnızca kural tabanlı yöntemin üstüne eklenen bir katman.

### 1.6 NASA Moon to Mars hedefleriyle eşleme

NASA'nın insanlı keşif mimarisi, hedef temelli bir yapıyla ilerliyor. REDLINE'ın her parçasını bu resmi hedeflere bağlamak, Relevance ve Impact puanı için doğrudan kanıt sağlar.

Kaynaklar: Moon to Mars Objectives (Eylül 2022) ve Moon to Mars Mimari Tanım Belgesi. OP-2 numarası teyit edilecek.

| Hedef | Özü | REDLINE karşılığı |
|---|---|---|
| OP-5 | Yüzey hareketlilik sistemlerini işletmek (EVA skafanderleri, aletler, araçlar) | Çekirdek: M1, M6, M8 |
| OP-9 | Entegre robotik sistemlerle mürettebatın yararlı işini en üst düzeye çıkarmak | M8 hareketli güvenli liman; E-01 SCOUT |
| OP-10 | Mürettebatı destekleyen robotları otonom ya da uzaktan işletmek | Nav2 rover; E-01 |
| OP-2 (teyit) | İletişim gecikmesi ve otonomi seviyesini gözeterek Dünya ekibi ile Mars yüzey ekibinin etkileşimini optimize etmek | M10, MCC, bilim arka odası |
| SE-2 | Dünya'daki bilimcilerin yüzeydeki astronotları uzaktan desteklemesi | Bilim arka odası, DTN notları |
| SE-5 | Robotik yöntemlerle sahayı astronotlardan önce ve onlarla eşzamanlı incelemek | E-01 SCOUT, E-03 füzyon |
| SE-7 | Özel ilgi alanlarını korumak (ör. Mars'ta RSL) | E-14 |
| HS-1 | Ay ve Mars'ta uzay havası gözlem ve tahminini geliştirmek | M3 SEP modu, E-12 |
| HBS-3 | Keşif sistemleri ve ortamın insan sağlığı, performansı ve insan faktörlerine etkisi | M1, HUD, V8 |
| LPS-2 / LPS-4 | Jeolojik süreçler / yaşanabilir ortamlar ve yaşamın kökeni | M5 boxwork hipotezleri |
| MI-2 / MI-3 | Mars iletişim / konum-navigasyon-zaman altyapısı | M10, M11, E-07 |
| TH-7 / TH-10 | Mürettebatın yüzeyde keşif ve bilim yapmasını sağlayan sistemler / insan–robot eşleştirmesi | Tüm sistem / M8, E-01 |
| RT-3 / RT-4 / RT-7 | Mürettebatın güvenli dönüşü / mürettebat zamanı / birlikte çalışabilirlik | Kırmızı çizgi / M7 / TSS, 3D Tiles, CCSDS Bundle Protocol |

---

## 2. Görev konsepti (ConOps)

### 2.1 Görev mimarisi varsayımları

Referans: NASA'nın 2024 Mimari Kavram İncelemesi (ACR 2024) Mars yüzey güç kararı belgesindeki "mütevazı" referans görev. Bu görevde 2 kişilik mürettebat en fazla 30 gün boyunca basınçlı bir roverda yaşıyor. Bizim türettiğimiz varsayımlar:

| ID | Varsayım | Değer | Dayanak |
|---|---|---|---|
| A-01 | Mürettebat | 2 (EV1, EV2) | ACR 2024 |
| A-02 | Yüzeyde kalış | ≤30 gün | ACR 2024 |
| A-03 | Yaşam ve güvenli liman | Basınçlı rover (PR) | ACR 2024 |
| A-04 | EVA düzeni | İkisi birlikte dışarıda; PR otonom "gölge" modunda | Bizim tercihimiz: 2 kişilik mürettebatta içeride kalacak kimse yok |
| A-05 | Skafander profili 1 (MKIII-IST) | 121 kg (PLSS maketi ve gimbal dahil), 29,6 kPa | Norcross ve ark., IST-1 (NASA TP-2010-216115) |
| A-06 | Skafander profili 2 (gelecek Mars skafanderi) | 70 kg, 29,6 kPa | Varsayım; "ya şöyle olsaydı" analizi için |
| A-07 | Nominal EVA | 6 saat dışarıda + rezerv | Varsayım |
| A-08 | Kullanılabilir O₂ | ≈1 kg | Kaba hesap: 8,5 sa × 350 W ortalama × 0,256 g/(W·sa) ≈ 760 g + pay |
| A-09 | PR fırtına sığınağı | Var (su duvarı vb.) | Varsayım |
| A-10 | PR kabin atmosferi | Keşif atmosferi (ör. 56,5 kPa, %34 O₂), dolayısıyla kısa ön-solunum | Varsayım (teyit) |
| A-11 | Dünya bağlantısı | Röle orbiterleri TGO, MRO, Odyssey; Mars Express yedek | NASA Mars Relay Network sayfası (2026). MAVEN Aralık 2025'te sustu; görevi 3 Haziran 2026'da sonlandırıldı |
| A-12 | Konum | GPS yok | Mars gerçeği |
| A-13 | Yüzey gücü | Ana güç fisyon. PR'nin enerji bütçesi parametrik; rover yer değiştirmeleri M8'de enerji maliyeti olarak sayılır | ACR 2024 kararı: NASA insanlı Mars için fisyonu ana yüzey güç teknolojisi seçti; 2 kişi / 30 gün görevi en az 10 kW istiyor |

A-05 ile A-08'den çıkan **erken tasarım içgörüsü** (kaba hesap):

- NASA'nın EVA Walkback Test'inde (EWT) MKIII skafanderiyle 3/8 g'de en yavaş yürüyüş hızında bile VO₂ ≈ 27,6 ml·kg⁻¹·dk⁻¹ ölçüldü.
- 80 kg'lık biri için bu yaklaşık 2,2 L O₂/dk, yani ≈740 W ve ≈189 g O₂/sa demek.
- 1 kg'lık O₂ bütçesi bu tempoyla ≈5,3 saat dayanır.
- Sonuç: skafander kütlesi, Mars'taki EVA menzilinin birinci derece belirleyicisi. REDLINE bunu bir kaydırıcıyla canlı olarak gösterecek.

### 2.2 Senaryo zamanı: 20 Mayıs 2024'ün yeniden oynatılması

Bu tarihi seçmemizin sebepleri:

1. **Gerçek yörüngeler.** SPICE çekirdekleri o gün aktif olan gerçek röle orbiterlerini içeriyor: MRO, TGO, Odyssey ve o tarihte hâlâ çalışan MAVEN. Böylece geçiş saatleri uydurma değil, gerçek.
2. **Gerçek uzay havası kaydı.** DONKI'de olay kayıtları var (CME, FLR, SEP, ENLIL).
3. **Gerçek doz ölçümü, farklı saha.** RAD, 2024'te Curiosity'nin bulunduğu Gediz Vallis çevresinde 8.100 µGy ölçtü; demo EVA'sının boxwork sahasında ölçüm yapılmadı. Kaba hesapla bu, yaklaşık 39 günlük GCR soğurulmuş dozuna eşit (8,1 / 0,21 mGy/gün). Soğurulmuş doz, kişiye ait sağlık riski veya etkin dozla özdeş değildir.
4. **Yerel öncü uyarısı var, Dünya bağımsız bir doğrulama sunamadı.** Kaynak bölge AR3664 o sırada Dünya'dan görünmeyen yüzdeydi. Patlamayı Solar Orbiter'ın STIX aleti gördü; Mars'a doğru giden X ve gama ışınları parçacıklardan önce, ışık hızında ulaştı. Parçacıklar Mars'a onlarca dakikada vardı. Bu yüzden faydalı öncü sinyal ancak Mars'ta veya Mars'a bakan bir varlıkta yerel olarak algılanabilir. Dünya'nın bağımsız teyidi, bir yöne en az 3–22 dakika süren Dünya–Mars hattında dakikalarca geç kalır. Bunun pratik çözümünü Löwe ve ark. (2025) RAD verisiyle gösterdi. Önerdikleri yerel nowcast sistemi, doz hızı arka planı en az %25 aştığında alarm veriyor. Mars yüzeyindeki olaylarda bu alarm, tepe dozdan ve toplam dozun çoğundan kaçınmak için en az ~30 dakika kazandırıyor; yanlış alarm oranı da neredeyse sıfır. **Tasarım sonucu:** REDLINE Dünya'dan gelecek uyarıya güvenmez. Alarm yerel dozimetre nowcast'ından gelir ve rota boyunca sığınağa ulaşma süresi bu ~30 dakikanın, güvenli bir pay bırakarak altında tutulur (FR-03, FR-04).
5. **Gerçek ışık gecikmesi.** O günkü Dünya–Mars ışık süresi SPICE ile hesaplanacak.

**Karşılaştırma varyantları:**

| Varyant | Açıklama |
|---|---|
| S0 | Aynı gün, SEP yok (nominal EVA) |
| S1 | 20 Mayıs 2024 SEP'i (ana demo) |
| S2 | "2026 ağı": MAVEN'siz kontak planı. Ağın kırılganlığını gösterir |
| S3 | Varsayımsal sürekli röle. NASA'nın Mayıs 2026'da teklif çağrısına çıktığı Mars Telecommunications Network fikri. Etki anlatısı için |

### 2.3 Saha: boxwork ağı (Altadena üyesi), Mount Sharp

Bilinenler (NASA, Curiosity blogları ve Siebach ve ark. LPSC 2026 özeti):

**Morfoloji**

- Sırtlar 1–2 m yüksek ve ~5 m genişliğinde.
- Sırtlar kesişerek ~10–20 m çaplı çokgenler oluşturuyor.
- Çukurlar çoğunlukla kumla dolu.

**Konum ve yayılım**

- Ağ, Gale tabanının ~1 km üstünde.
- Yörüngeden yapılan haritalama, boxwork'ün Curiosity'nin rotasından **14 km batıya** kadar uzandığını ve ~100 m'lik bir yükselti aralığında açıkta olduğunu gösteriyor.

**Curiosity kampanyası**

| Faz | Sol aralığı | Dönem |
|---|---|---|
| Faz 1 | 4534–4570 | Mayıs–Haziran 2025. Altadena sondajıyla sonuçlandı |
| Faz 2 | 4571–4599 | Bölgesel bağlam |
| Faz 3 | 4600–4805 | En iyi gelişmiş sırt ve çukurlar |
| Faz 4 | 4805 ve sonrası | Kontaklar. Rover Mart–Nisan 2026'da boxwork'ten ayrılıp sülfat biriminde güneye devam etti |

**Örnekler**

| Örnek | Konum | Bulgu |
|---|---|---|
| Altadena | Geçiş bölgesi | — |
| Valle de la Luna | Çukur ana kayası | Siderit / karbonat |
| Nevado Sajama | Sırt tepesi | Kil mineralleri (fillosilikat) |
| Dördüncü örnek | — | Islak kimya (organik arama) |

**Kritik bulgular**

- Sırt ile çukur arasında doku ve mineraloji farkı var.
- Buna karşın uzaktan kimya aletleri (ChemCam, APXS) tutarlı bir **toplu kimya farkı görmedi**. Bu, kapalı sistem (izokimyasal) bir yeraltı suyu değişimine işaret ediyor.
- Tamamen erozyonla oluşmuş bir desen hipotezi (tafoni benzeri) henüz dışlanamıyor.

**Curiosity sırasında yaşanan küçük olaylar.** Sırt ortalarındaki koyu çizgiler kum ya da regolit birikimi. Bir çukurda santimetre ölçekli, 120°'lik açılarla kesişen küçük çokgenler bulundu.

**İnsanlı EVA'nın gerekçesi.** Curiosity ağın yalnızca doğu kenarını gördü. Batıdaki 14 km'lik ağda doğudaki sonuçların genellenip genellenmediği açık bir soru. İnsanın hızı ve yargısıyla, birkaç EVA'da onlarca sırt–çukur çifti örneklenebilir.

**İki çalışma alanı (AOI):**

| AOI | Amaç | Boyut | Seçim ölçütü |
|---|---|---|---|
| AOI-V (doğrulama) | Curiosity'nin boxwork traversini içerir; V1 ve V2 burada | ~2×3 km | Curiosity rotası + DEM/ortofoto kapsamı |
| AOI-E (keşif) | Batıdaki, ziyaret edilmemiş açık yüzeyler; demo EVA'sı burada | ~3×3 km | Boxwork'ün en iyi göründüğü yer, FOM'lu HiRISE DTM kapsamı (teyit), PR'nin erişebileceği arazi |

### 2.4 Bilim soruları ve hipotezler

**EVA'nın bilim sorusu.** Batıdaki boxwork ağında sırt ile çukur arasındaki mineraloji ve doku farkı doğudakiyle aynı mı? Toplu kimya farkı gerçekten yok mu?

| Gözlem | H1: Kırık kenarı boyunca yeraltı suyu sertleşmesi (kapalı sistem) | H2: Açık sistem kimyasal çimentolanma | H3: Yalnızca erozyon (tafoni benzeri) |
|---|---|---|---|
| o1 Toplu kimya farkı (sırt − çukur) | Yok / küçük | Belirgin | Yok |
| o2 Mineraloji farkı (ör. kil ve siderit) | Var | Var | Yok |
| o3 Doku gradyanı (nodül/damar yoğunluğu, sırt tepesinden tabana) | Var | Var | Zayıf / rastgele |
| o4 Kırık geometrisi ile sırt ağının uyumu (DTM'den) | Güçlü | Güçlü | Zayıf |

- **Doğu kenarı sonuçları.** o1 yok, o2 var. Bu durum posterior'u H1 lehine çeviriyor. Batıdaki EVA bunun genelliğini test eder.
- **İstasyon tasarımı: eşleştirilmiş örnekleme.** Her bilim istasyonu bir sırt ve ona komşu bir çukurdan oluşan bir çift. Aynı ölçümler iki tarafta da yapılır, böylece fark doğrudan ölçülür (kontrollü tasarım).
- **Ölçüm araçları (simüle).** El tipi XRF ile toplu kimya, el tipi spektrometre ile mineraloji, kask kamerası ve el lensi ile doku. TSS şemasında kaya kimyası için hazır bir alan var (`SPEC`).

### 2.5 Roller ve yetki

| Aktör | Rol | Yetki |
|---|---|---|
| EV1 | Navigasyon ve güvenlik lideri | Gerçek zamanlı son karar |
| EV2 | Bilim ve örnekleme | Bilim kararları; EV1'e öneri |
| PR + REDLINE çekirdeği | Otonom güvenli liman. Yerdeki "IV operatörü" rolünü üstlenir | Kural ihlalinde otomatik uyarı ve yeniden planlama; kararı mürettebat onaylar |
| Dünya görev kontrolü (MCC) | Uçuş direktörü, sistem izleme | Danışma (3–22 dk gecikmeli); sonraki EVA planını onaylar |
| Bilim arka odası | BASALT tarzı bilim desteği | Önceliklendirme önerileri, hipotez güncellemesi |

İlke: **Mars'ta otorite yereldir.** Dünya gerçek zamanlı karar veremez, yalnızca öneri verebilir. Tasarım, Dünya bağlantısı olmadan da güvenli çalışmalı (OFF-09).

### 2.6 Bir EVA günü (şablon: Sol 12, EVA-3)

| LTST | Faz | Mürettebat | Aktif REDLINE modülleri | Dünya |
|---|---|---|---|---|
| 07:30 | Plan güncelleme | Habitat ekranı | Gece gelen DTN notları, M5 posterior, M7 durak seçimi | Önceki gecenin önerileri DTN ile ulaşmış |
| 08:00 | Plan doğrulama | Habitat ekranı | M6 + Monte Carlo + M9 kuralları; M8 rover istasyon planı | — |
| 08:30 | Ön-solunum, skafander kontrolü | Suitport | TSS tarzı telemetri kontrolü (FR-11) | — |
| 09:00 | Çıkış | — | İzleyiciler aktif; kırmızı çizgi HUD'da | Ertesi röle geçişinde "çıkış" paketi |
| 09:15–10:30 | Traverse 1 (sırt tepeleri boyunca) | EV1+EV2 | M6 rota, M11 lokalizasyon, M10 bağlantı | — |
| 10:30–11:15 | İstasyon 1 (sırt/çukur çifti) | Örnekleme | M5 posterior güncellemesi → M7 yeniden sıralama | — |
| 11:15–13:00 | Traverse 2 + İstasyon 2 | — | — | Röle geçişi: özet telemetri gönderilir |
| 13:00–14:00 | İstasyon 3 (opsiyonel) | — | Kırmızı çizgi payı izlenir | — |
| 14:00–14:45 | Dönüş | — | — | — |
| 14:45 | Giriş | — | Doz ve sarf özeti | Öğleden sonra geçişiyle tam veri gönderilir |
| 15:30 | EVA sonrası | Habitat ekranı | MCAP kaydı, STAC'a gözlemler | Bilim arka odası ertesi gün için öneri hazırlar |

Saatler şablondur. Gerçek röle geçiş saatleri SPICE'tan, aydınlatma pencereleri M4'ten gelecek.

### 2.7 Arıza senaryoları kataloğu

| ID | Tetikleyici | Algılayan | Otomatik tepki | HUD | Dünya ne zaman görür |
|---|---|---|---|---|---|
| OFF-01 | SEP: doz hızı eşiği aşar | PR ve skafander dozimetresi; FR-04 | Hedef "sığınak" olur; D\* Lite ile yeni rota; M8 roverı karşılamaya gönderir | Kırmızı tam ekran uyarı, sığınak oku, geri sayım | Sonraki röle geçişi + OWLT |
| OFF-02 | O₂ tüketimi beklenenden hızlı (sızıntı) | consumables_estimator; FR-01 | Kırmızı çizgi daralır; duraklar düşürülür; dönüş önerilir | Pay azalıyor uyarısı | Aynı |
| OFF-03 | Metabolik aşım (HR yüksek) | FR-07 | Hız sınırı düşürülür; dinlenme önerilir | Sarı uyarı | Aynı |
| OFF-04 | Sırt arkasında görüş hattı kaybı | link_manager; FR-06 | Buddy rölesi önerilir; süre aşılırsa son bağlantı noktasına dönülür | Bağlantı ikonu, geri sayım | Kayıt EVA sonrası |
| OFF-05 | Konum belirsizliği büyür | localization; FR-09 | Yeniden lokalizasyon prosedürü (360° ufuk taraması, UWB) | "Konum düşük güven" | — |
| OFF-06 | Mürettebat üyesi çalışamaz hâle gelir | Buddy bildirimi; FR-13 | Rover kurtarma moduna geçer, en kısa sürüş planı yapılır | Kurtarma ETA | Aynı |
| OFF-07 | PR arızası (hareketsiz) | Rover sağlık durumu | Güvenli liman sabitlenir; kırmızı çizgi yeniden hesaplanır (genelde daralır) | Yeni çizgi | Aynı |
| OFF-08 | Düşük güneş, uzun gölgeler, kayalar görünmez | M4; FR-12 | Tehlike katmanı ağırlığı artırılır; gün batımı payı kontrol edilir | Görüş uyarısı | — |
| OFF-09 | Dünya bağlantısı yok (geçiş yok, kavuşum) | DTN kontak planı | Normal işleyiş: tüm kararlar yerelde | "Dünya: sıradaki temas 13:42" | Bağlantı gelince |

---

## 3. Sistem mimarisi

### 3.1 Bağlam diyagramı

```
╔═══════════════════════════════ DÜNYA ═══════════════════════════════╗
║  Görev Kontrolü (MCC)                 Bilim Arka Odası               ║
║  gecikmeli telemetri, "tahmini şimdi"  posterior, not ve öneri       ║
║            └──────── ROS 2 "earth" alanı ────────┘                   ║
║                        DTN düğümü ipn:2                              ║
╚══════════════════════════════╤══════════════════════════════════════╝
                               │ Bundle Protocol v7 / LTP
                               │ SPICE'tan kontak planı · OWLT 3–22 dk
╔══════════════════════════════╧══════ MARS YÖRÜNGESİ ═════════════════╗
║  Röle düğümü ipn:3 (TGO / MRO / Odyssey geçişleri, sakla-ilet)       ║
╚══════════════════════════════╤══════════════════════════════════════╝
                               │ UHF geçişleri
╔══════════════════════════════╧══════ MARS YÜZEYİ ════════════════════╗
║  Basınçlı Rover (PR): DTN ipn:1 · zenohd router · REDLINE çekirdeği  ║
║   planner_server · walkback_field · science_optimizer · rover_placer ║
║   copilot_monitor · safety_aggregator · human_model · env_server     ║
║   localization (EKF) · Nav2 + Gazebo · habitat ekranı (web)          ║
║            ▲  rmw_zenoh · görüş hattına bağlı kayıplı bağlantı       ║
║            ▼                                                         ║
║   EV1: UE5 kask HUD + tablet  ◄── buddy rölesi ──►  EV2: UE5/simüle  ║
╚══════════════════════════════▲══════════════════════════════════════╝
                               │ önceden hesaplanmış katmanlar (COG + STAC)
╔══════════════════════════════╧══ VERİ HATTI (Python, çevrimdışı) ════╗
║  HiRISE 25 cm, 1 m DEM (+FOM) · CTX/HRSC/MOLA · THEMIS · CRISM       ║
║  RAD · REMS · MGCM/AmesCAP · SPICE · DONKI · Curiosity rotası/Navcam ║
║  → eğim, kaya, sınıf, ufuk küpü, radyasyon, gölge, görüş hattı,      ║
║    bilim değeri, maliyet tabloları                                   ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Mimari karar: Dünya ve Mars ayrı ROS 2 alanları.** Aralarında tek bağlantı DTN geçidi. Böylece ışık gecikmesi ve kesinti, bir ayar değil mimarinin kendisi olur; "Dünya'dan gerçek zamanlı komut" hatası yapısal olarak imkânsızdır.

### 3.2 Alt sistemler

| ID | Alt sistem | Sorumluluk | Dil / teknoloji | Rol | Kademe |
|---|---|---|---|---|---|
| SS-01 | DATA | Veri edinme, yeniden projeksiyon, türev katmanlar, STAC | Python: GDAL, rasterio, pyproj, numpy/numba, PyTorch | R1 | 0 |
| SS-02 | HUMAN | Metabolik ve sarf modeli, maliyet tabloları, çevrimiçi kestirim | Python (+C++'a taşınan tablolar) | R2/R1 | 0 |
| SS-03 | TERRAIN | Eğim σ, pürüzlülük, sırt tespiti, kaya, sınıf | Python, OpenCV, PyTorch (stretch) | R1 | 0 |
| SS-04 | RAD | Ufuk küpü, F_α, doz hızı, SEP modu | Python + GPU/numba veya C++ | R1 | 0 |
| SS-05 | ENV | SPICE güneş konumu, gölge, MGCM, DONKI | Python: SpiceyPy, AmesCAP | R1/R3 | 1 |
| SS-06 | PLAN | Graf, Dijkstra, walkback, kırmızı çizgi, D\* Lite, Monte Carlo | C++20 çekirdek, ROS 2 action server, WASM (stretch) | R2 | 0 |
| SS-07 | SCI | Hipotez modeli, bilgi kazancı, MILP durak seçimi | Python: HiGHS / OR-Tools | R2 | 2 |
| SS-08 | ROVER | Space ROS Curiosity modeli, Nav2, DEM'den Gazebo dünyası, rover yerleşimi | ROS 2 C++/Python | R3 (+R2) | 1–2 |
| SS-09 | SAFE | FRET kuralları → Ogma → Copilot → C99 ROS 2 izleyici; toplayıcı | FRET, Haskell, C99, Python | R4 | 1 |
| SS-10 | COMM | rmw_zenoh, link_manager, ION/HDTN, DTN geçitleri, kontak planı | ROS 2, C (ION), Python (pyion, teyit) | R3 | 2 |
| SS-11 | LOC | EKF, UWB, güneş pusulası, ufuk eşleştirme | C++ (robot_localization), Python/OpenCV | R4 | 2–3 |
| SS-12 | HUD | UE5 sahnesi, kask HUD'u, EV piyonları, köprü | UE5 C++/Blueprint, Cesium for Unreal | R5 | 1 |
| SS-13 | CONSOLE | Habitat, tablet, MCC, bilim arka odası | TypeScript, React, CesiumJS | R6 | 0 (harita) / 2 |
| SS-14 | SIM | Senaryo motoru, sim saati, olay enjeksiyonu, EV simülasyonu | Python ROS 2 | R3/R4 | 0 |
| SS-15 | OPS | Docker compose, MCAP kaydı, CI | Docker, GitHub Actions | R3 | 0 |

### 3.3 Dağıtım

```
Windows 11 ana makine (GPU)
├─ UE5 + Cesium for Unreal  → EV1 kask HUD'u (oyuncu kontrollü), EV2 izleyici kamerası
├─ Tarayıcı                  → habitat / tablet / MCC / bilim arka odası konsolları
└─ WSL2 Ubuntu 24.04 (networkingMode=mirrored)
   ├─ ROS 2 Jazzy · "mars" alanı (rmw_zenoh, zenohd)
   │   ├─ planner_server · walkback_field · science_optimizer · rover_placer
   │   ├─ copilot_monitor (Ogma üretimi) · safety_aggregator
   │   ├─ human_model · consumables_estimator · localization · skyline_matcher
   │   ├─ env_server · link_manager · sim_clock · scenario_player · ev_sim
   │   ├─ Gazebo Harmonic + Nav2 + Curiosity modeli (PR vekili)
   │   └─ rosbridge_server / foxglove_bridge (ws://)
   ├─ Docker: dtn-mars (ION), dtn-relay (ION), dtn-earth (ION veya HDTN), tile sunucusu
   └─ ROS 2 "earth" alanı (ayrı router) ◄── yalnızca DTN geçidi üzerinden
```

- **Çok makine.** UE5 güçlü GPU'lu dizüstünde, ROS/Gazebo ikinci makinede çalışır. Bağlantı yerel ağ üzerinden kurulur. Mekân Wi-Fi'ı güvenilmez, bu yüzden **seyahat router'ı** getirilecek.
- **Tek makine yedeği.** Her şey localhost'ta çalışabilmeli (RK-04).

### 3.4 Çalışma döngüleri

| Döngü | Ne | Frekans / bütçe |
|---|---|---|
| L0 çevrimdışı | Veri hattı → katmanlar → ufuk küpü → maliyet tabloları | Dakikalar; EVA öncesi bir kez |
| L1 plan | Plan + rover istasyonları + Monte Carlo doğrulama | ≤60 sn; EVA öncesinde ve talep üzerine |
| L2 taktik | Olay tetikli yeniden planlama (D\* Lite) + walkback güncellemesi | ≤2 sn |
| L3 izleme | Copilot izleyicileri | 10 Hz |
| L4 HUD | Veri 10 Hz, görüntü ≥45 fps | — |
| L5 Dünya | DTN paketleri | Dakikalar–saatler |

### 3.5 Koordinat ve zaman çerçeveleri

**Gezegen çerçevesi**

- USGS ürünlerinde planetosentrik enlem ve doğuya pozitif boylam kullanılıyor (DEM etiketi: `LatitudeType = Planetocentric`, `LongitudeDirection = PositiveEast`).
- Cesium Mars, `IAU_2015:49901` CRS'ini kullanıyor.
- Dönüşümler PROJ'un IAU_2015 veritabanıyla pyproj üzerinden yapılır (PROJ ≥8.2, teyit).
- Küre ile elipsoit arasındaki yükseklik farkları sözleşmede açıkça yazılacak.

**Saha çerçevesi**

- `site` çerçevesi ENU'dur (x doğu, y kuzey, z yukarı); orijini AOI merkezi.
- Veri yolunda **yalnızca saha ENU metreleri** dolaşır. UE5 ve Cesium kendi dönüşümlerini kendileri yapar.

**TF ağacı (REP-103/105)**

```
mars_iau → site (map) → odom → ev1/base_link, ev2/base_link, rover/base_link
```

**UE5.** Santimetre birimi ve sol el koordinat sistemi kullanır. Dönüşüm yalnızca köprüde yapılır, başka hiçbir yerde değil.

**Zaman**

- Ana saat UTC. ROS zamanı `/clock`'tan gelen sim zamanıdır.
- Mars yerel saati (LMST/LTST) Allison & McEwen (2000) algoritmasıyla ya da SPICE ile hesaplanır. Ayrıca sol sayacı tutulur.
- Işık süresi SPICE'tan alınır (LT+S düzeltmesi).
- Demo için zaman ×1–×60 hızlandırılabilir. İzleyiciler sim zamanını kullanır.

### 3.6 Arayüz sözleşmeleri (taslak; H0–H2'de dondurulacak)

Aşağıdaki liste bir **planlama taslağıdır**. Gerçek mesaj ve aksiyon tanımları H0'dan sonra yazılacak.

| Grup | Konu / aksiyon | İçerik | Frekans | QoS |
|---|---|---|---|---|
| EVA | `/eva/{ev}/pose` | Konum + kovaryans (saha ENU) | 10 Hz | best_effort, keep_last 1 |
| EVA | `/eva/{ev}/biomed` | HR, metabolik kestirim | 1 Hz | best_effort |
| EVA | `/eva/{ev}/consumables` | O₂, H₂O, batarya, CO₂: kalan miktar, hız, tahmin (TSS eşlemesiyle) | 1 Hz | reliable |
| Rover | `/rover/pose`, `/rover/station_plan` | Konum; zaman damgalı istasyon dizisi | 10 Hz / olay | reliable |
| Plan | `/plan/route` | Yol + segment başına maliyet vektörü (ortalama, varyans) | Olay | reliable, transient_local |
| Plan | `/plan/walkback_field`, `/plan/redline`, `/plan/margin` | Izgara; çokgen; dakika cinsinden pay | 1 Hz / olay | reliable, transient_local |
| Plan | `/plan/science_stops` | Sıralı duraklar, değer, zaman pencereleri | Olay | reliable |
| Güvenlik | `/safety/violations` | Kural kimliği, önem, zaman, bağlam | Olay | reliable, keep_all |
| Çevre | `/env/sun`, `/env/dose_rate`, `/env/sep_alert` | Az/el; µGy/sa; alarm | 1 Hz / olay | reliable |
| İletişim | `/comm/link/{ev}` | Görüş hattı, kayıp yüzdesi, gecikme, röle yolu | 1 Hz | best_effort |
| Bilim | `/science/observation`, `/science/posterior` | Ölçüm; P(H) | Olay | reliable |
| Aksiyonlar | `PlanEva`, `Replan`, `PlaceRover` | — | — | — |
| Servisler | `QueryCost(point)`, `QueryWalkback(point)` | — | — | — |

**Katman şeması.** Her katman bir COG dosyasıdır ve şunları içerir:

- Bantlar: `value`, `sigma` (varsa), `mask`.
- Etiketler: birim, kaynak veri seti kimlikleri (D-xx), işleme sürümü.
- Her katman bir STAC öğesidir.

### 3.7 Tasarım ilkeleri

1. **Tek kaynak.** Eşikler (rezervler, süre sınırları, eğim sınırları) tek bir parametre dosyasında tutulur. FRET değişken veritabanı, planlayıcı ve HUD aynı dosyayı okur.
2. **Her şey yeniden oynatılabilir.** Senaryo dosyası + tohum + MCAP kaydı, birebir aynı demoyu verir.
3. **Her sayının kaynağı var.** STAC kaydı her katmanı hangi NASA verisinden türetildiğine bağlar. Proje sayfasındaki veri tablosu buradan otomatik üretilir.
4. **Önce yürüyen iskelet.** Sahte veriyle uçtan uca akış H6'da çalışır; gerçek modüller sonra yerine takılır.
5. **Her modülün bir yedeği var.** ML → kural tabanlı; Ogma → elle yazılmış izleyici; UE5 canlı → kayıtlı video; DTN → gecikme kuyruğu.

---

## 4. Veri ve katmanlar

### 4.1 Veri envanteri

| ID | Veri seti | Kaynak | Çözünürlük | Kullanım | Kademe |
|---|---|---|---|---|---|
| D-01 | MSL Gale Merged Orthophoto Mosaic (Calef & Parker 2016) | USGS Astrogeology. Kayıpsız ~23 GB; 2025 renkli COG ~1 GB | 25 cm | Taban görüntü, sınıflandırma, görsel | 0 |
| D-02 | MSL Gale Merged DEM (Parker & Calef 2016) | USGS Astrogeology | 1 m | Arazi, eğim, ufuk (yakın alan) | 0 |
| D-03 | HiRISE DTM'leri (UA) + FOM + ortho; ör. ESP_012907_1745 sülfat birimi | HiRISE PDS | 1 m (DTM) | Yükseklik belirsizliği (σ_z); AOI-E kapsamı teyit | 1 |
| D-04 | HiRISE tekil RDR görüntüleri (etiketinde güneş geometrisi) | HiRISE PDS | 25–32 cm | Gölgeden kaya tespiti. Mozaiklerde farklı güneş geometrileri karıştığı için tekil görüntü gerekir | 1 |
| D-05 | MOLA–HRSC Blended DEM + CTX | USGS / PDS | 200 m / 6 m | Uzak ufuk: Mount Sharp ve krater kenarı | 0 |
| D-06 | THEMIS termal atalet | ASU/PDS | 100 m | Pekişmiş zemin / kum ayrımı | 1 |
| D-07 | CRISM (MTRDR, özet parametreler: sülfat ve hidrasyon indeksleri) | PDS Geosciences | ~18 m | Bilim önselleri | 2 |
| D-08 | MSL RAD doz hızı zaman serileri | PDS PPI | — | V2, V5; SEP doz eğrisi | 1 |
| D-09 | MSL REMS basınç ve sıcaklık | PDS Atmospheres | — | M4 doğrulaması | 3 |
| D-10 | MSL konum ve rota verisi (MMGIS / PDS; PDS4 "PLACES" konum ürünleri) | JPL/PDS | — | V1; E-03 hizalama başlangıcı | 1 |
| D-11 | MSL Navcam/Mastcam görüntüleri | PDS Imaging | — | V6; UE5 görsel referansı | 2 |
| D-12 | MSL ChemCam/APXS + CheMin sonuçları | PDS Geosciences / yayınlar | — | M5 önselleri (sırt/çukur) | 2 |
| D-13 | NASA Ames MGCM çıktıları (MCMC) | NASA Ames + AmesCAP | Kaba ızgara | Sıcaklık, toz τ, rüzgâr | 2 |
| D-14 | NAIF SPICE çekirdekleri (jenerik + MRO/TGO/ODY/MAVEN SPK) | NAIF | — | Güneş, röle geçişleri, ışık süresi | 1 |
| D-15 | DONKI (CME, FLR, SEP, WSAEnlilSimulations) | NASA CCMC | — | Olay zaman çizelgesi | 1 |
| D-16 | MAVEN SEP verisi | PDS PPI | — | Mars'ta parçacık zaman çizelgesi (V5) | 2 |
| D-17 | Cesium Mars (ion varlık 3644333) | Cesium ion | Gale: 25 cm görüntü / 1 m arazi | UE5 ve CesiumJS tabanı. D-01 ve D-02'den üretilmiş | 0 |
| D-18 | NASA 3D Resources (astronot / rover modelleri) | NASA | — | UE5 varlıkları (lisans teyit) | 1 |
| D-19 | Mars Trek WMTS katmanları | NASA | — | Çapraz kontrol | 3 |
| D-20 | MSL Navcam RDR stereo türevleri: XYZ, UVW normalleri, range, pürüzlülük, eğim | PDS Imaging | cm–dm (menzile bağlı) | E-03 füzyon, V10 | E |
| D-21 | NASADEM, Landsat 8/9 OLI, ASTER, HLS (Salda) | NASA Earthdata | 30 m / 15 m | E-11 analog modu | E |
| D-22 | Cesium Moon, LRO LOLA / NAC DTM | Cesium ion / PDS | — | E-13 Ay portu | E |

**Veri türü sayısı.** Görüntü, yükseklik, termal, spektral, radyasyon, meteoroloji, geometri/efemeris, uzay havası, rover görüntüsü ve rover rotası. Toplam **10 tür**; challenge'ın istediği en az 3'ün çok üzerinde.

### 4.2 Veri hattı aşamaları

| Aşama | İş | Not |
|---|---|---|
| P-1 | AOI tanımı ve edinme | Büyük dosyalar GDAL `/vsicurl/` ile pencere okunur; 23 GB indirmek gerekmez. Renkli mozaik zaten COG |
| P-2 | Yeniden projeksiyon | Saha yerel projeksiyonu (Mars küresinde ekidistant veya transverse Mercator), pyproj + IAU_2015 |
| P-3 | Hizalama kontrolü | Ortofoto ile DEM'in hillshade'i arasında çapraz korelasyon; ofset raporu |
| P-4 | Arazi türevleri | Çok tabanlı eğim (2, 3, 5 m), σ_eğim, pürüzlülük, eğrilik, TPI, sırt haritası (morfolojik top-hat) |
| P-5 | Kaya | Tekil HiRISE görüntüsünde gölge segmentasyonu → kaya listesi → 50 m hücrelerde k tahmini (M2) |
| P-6 | Sınıflandırma | Kural tabanlı (eğim + pürüzlülük + parlaklık + TI) → stretch: segmentasyon ağı |
| P-7 | Ufuk küpü | Her nokta ve 72 azimut (5°) için ufuk yüksekliği. Yakın alan 1–2 m DEM (~2 km), uzak alan 200 m DEM (~50 km); gezegen eğriliği düzeltmesiyle |
| P-8 | Türetilmiş fiziksel katmanlar | F_α, doz hızı, gölge takvimi, aday istasyonlardan görüş alanı, bağlantı kalitesi, termal |
| P-9 | Paketleme | COG + STAC; konsol ve UE5 için karolar (MVP: `gdal2tiles` geodetic profil; stretch: dinamik tile sunucusu); planlayıcı için ikili ızgara |

**Ufuk küpü ayrıntıları**

- **Eğrilik düzeltmesi.** Uzaklık r'deki yüzey, küre eğriliği yüzünden $r^2/2R$ kadar aşağıda kalır. Mars yarıçapı R = 3.396.190 m için 10 km'de ~15 m, 20 km'de ~59 m, 50 km'de ~368 m eder (kaba hesap). Mount Sharp ufku için bu düzeltme zorunlu.
- **Algoritma.** Saf ışın yürütme N × 72 × adım sayısı kadar işlem ister. Bunun yerine Dozier & Frew (1990) tarzı yön başına doğrusal süpürme (üst dışbükey zarf) veya GPU kullanılır.
- **Depolama.** 3×3 km, 2 m ızgara (2,25 M nokta) × 72 yön × 1 bayt (0,5° nicemleme) ≈ 160 MB.

### 4.3 Katman kataloğu

| ID | Katman | Birim | Türetildiği yer | Belirsizlik | Kullanan |
|---|---|---|---|---|---|
| L-01 | Ortofoto | DN | D-01 | — | Konsol, UE5 |
| L-02 | Yükseklik | m | D-02/D-03 | σ_z (FOM veya EP) | Hepsi |
| L-03 | Eğim (b = 2, 3, 5 m) | ° | L-02 | σ_eğim | M1, M2, M6 |
| L-04 | Pürüzlülük / TPI | m | L-02 | — | M2 |
| L-05 | Sırt / çukur haritası, sırt "kapıları" | sınıf | L-02 (top-hat) | — | M2, M5, M6 |
| L-06 | Arazi sınıfı | sınıf | L-01, L-03, L-04, L-08 | Sınıf olasılığı | M1, M2 |
| L-07 | Kaya bolluğu k ve N(≥D\*) | %, m⁻² | D-04 | Güven aralığı | M2, M6 |
| L-08 | Termal atalet | TIU | D-06 | — | M2 (η) |
| L-09 | Sülfat / hidrasyon indeksi | — | D-07 | — | M5 |
| L-10 | Ufuk küpü h(p, φ) | ° | L-02 + D-05 | — | M3, M4, M11 |
| L-11 | GCR görünür gökyüzü faktörü F_α | 0–1 | L-10 | α belirsizliği | M3 |
| L-12 | GCR doz hızı | µGy/sa | L-11 + RAD | — | M6 |
| L-13 | Gölge takvimi (10 dk adım) | bool × t | L-10 + SPICE | — | M4, HUD |
| L-14 | Yüzey sıcaklığı (stretch) | K | MGCM + eğim/bakı | — | M1 |
| L-15 | Aday rover istasyonlarından görüş alanı | bool | L-02 | — | M8, M10 |
| L-16 | Bağlantı kalitesi | dB / kayıp % | L-15 | — | M10 |
| L-17 | Bilim önsel değeri | bit | L-05, L-09, L-08 | — | M5, M7 |
| L-18 | İnsan maliyet tabloları (eğim × sınıf → t, O₂, H₂O) | sn, g, kg | M1 | ortalama/varyans | M6 |
| L-19 | Rover maliyet haritası | — | L-03, L-07 | — | Nav2, M8 |
| L-20 | Walkback alanı W_ε | dk / g O₂ | M6 | ε kuantili | HUD, M7, M8 |
| L-21 | Kırmızı çizgi | çokgen | L-20 | — | HUD, konsol |
| L-22 | SEP sığınak süresi | dk | M6 + M8 | — | FR-03, HUD |

### 4.4 Kaynak izlenebilirliği

- Her COG'nin STAC kaydı, `derived_from` alanıyla D-xx kimliklerine bağlanır.
- Proje sayfasındaki "Kullanılan NASA verileri" tablosu bu kayıtlardan üretilir. Jüri hangi katmanın hangi alete dayandığını tek tıkla görebilir.

---

## 5. Teorik modüller

Her modül aynı şablonla anlatılıyor: **Amaç · Girdi → Çıktı · Model · Belirsizlik · Doğrulama · MVP → Stretch · Sahibi**

### M1. İnsan hareketi ve sarf modeli

**Amaç.** Her eğim ve arazi sınıfı için yürüyüş hızı ile süre, O₂, su ve batarya maliyetini ortalama ve varyansıyla vermek. EVA sırasında bu tahminleri canlı ölçümle güncellemek.

**Girdi → Çıktı.** Eğim (yönlü), arazi sınıfı, skafander profili, kişi parametreleri, HR telemetrisi → L-18 maliyet tabloları, çevrimiçi metabolik kestirim, sarf tahminleri.

**Model**

1. **Hız ve Froude benzerliği.** Sarkaç tipi yürüyüşte tercih edilen hız $\sqrt{gL}$ ile ölçeklenir. Mars için:

   $$\frac{v_M}{v_E}=\sqrt{\frac{g_M}{g_E}}=\sqrt{\frac{3{,}71}{9{,}81}}\approx 0{,}615$$

   Yürüyüşten koşuya geçiş Froude sayısı ~0,5'te olur. Bacak boyu L = 0,9 m için $v_{wr}=\sqrt{0{,}5\cdot 3{,}71\cdot 0{,}9}\approx 1{,}29$ m/s; Dünya'da aynı değer ~2,10 m/s. Bunlar kaba hesap ve bir hipotez.

   Eğime göre hızın biçimi Tobler (1993) fonksiyonundan alınır, Froude çarpanıyla ölçeklenir:

   $$v(S)=0{,}615\cdot 6\,e^{-3{,}5\lvert S+0{,}05\rvert}\ \text{km/sa},\quad S=\tan\theta$$

2. **Metabolik güç, IST ayrıştırmasıyla.** NASA'nın IST/EWT metodolojisi skafanderin maliyetini iki parçaya ayırıyor: ağırlıktan gelen kısım ve diğer etkenler (kinematik kısıtlar, eylemsizlik, basınç). Modelimiz aynı yapıyı izliyor:

   $$M = M_{\text{çıplak}}(V,G,g) + \Delta M_{\text{ağırlık}}(m_s,g,V) + \Delta M_{\text{skafander}}(P,V,g)$$

   - **Eğim terimi fiziksel olarak ölçeklenir.** Pandolf (1977) denklemindeki eğim terimi $0{,}35\,V G$ (G yüzde cinsinden). Bu terim, kas verimi ε ≈ 0,28 olan dikey kaldırma işine karşılık gelir: $g_E/(100\,\varepsilon)=0{,}35 \Rightarrow \varepsilon\approx 0{,}28$. Dolayısıyla Mars'ta eğim terimi $0{,}35\,(g_M/g_E)\,VG\approx 0{,}132\,VG$ olur.
   - **Düz zemin ve duruş terimleri** $(g/g_E)^\beta$ ile ölçeklenir. β, Norcross verisine uydurulur. Beklentimiz β < 1, çünkü denge ve salınım maliyetleri yerçekimiyle orantılı küçülmez.
   - **İniş kolu** Minetti ve ark. (2002) yürüme polinomunun biçiminden alınır (katsayılar teyit):

     $$C_w(i)=280{,}5i^5-58{,}7i^4-76{,}8i^3+51{,}9i^2+19{,}6i+2{,}5\ \ [\text{J}\,\text{kg}^{-1}\text{m}^{-1}],\quad -0{,}45\le i\le 0{,}45$$

     Polinom asimetrik: yokuş aşağı da maliyetlidir ve minimum yaklaşık −%10 eğimdedir. Bu asimetri, graf kenarlarının **yönlü** olmasının fiziksel gerekçesi.
   - **Arazi çarpanı η** (Soule & Goldman 1972; teyit): sert zemin 1,0, toprak yol 1,1, gevşek kum ~2,1. Boxwork'te sırt tepeleri görece düz ve sert, çukurlar kumlu. Bu yüzden model **sırt tepelerini yürüme yolu gibi** kullanan rotalar üretmeli.
   - **Kalibrasyon hedefi (V3).** EWT Tablo 5, 3/8 g, en düşük üç hız:

     | Koşul | VO₂ (ml·kg⁻¹·dk⁻¹) |
     |---|---|
     | Skafanderli | 27,6 / 32,5 / 35,7 |
     | Ağırlığı eşlenmiş skafandersiz | 12,7 / 13,7 / 14,1 |
     | Skafandersiz | 11,0 / 12,1 / 12,1 |
     | Ağırlık dışı skafander maliyeti | 14,9 / 18,8 / 21,6 (toplam skafander maliyetinin ~%90'ı) |

     Rapordan iki sonuç daha: Mars yerçekiminde skafanderli denekler 1,5 m/s'de grup ortalaması VO₂peak'e yaklaştı. Ay yerçekiminde ağırlık dışı skafander maliyeti ~8 ml·kg⁻¹·dk⁻¹ civarında sabit kaldı.
   - **Skafandersiz terim için ikinci kalibrasyon kaynağı: Kluis ve ark. (2025, J Appl Physiol).**
     - Çalışma: 12 denek; 0,25 / 0,5 / 0,75 / 1 g; 3 ve 4 mph; %0 ve %10 eğim.
     - Bulgular: hız × yerçekimi ile yerçekimi × eğim etkileşimleri anlamlı. Ortalama artışlar: 3'ten 4 mph'ye ~1,16, %0'dan %10 eğime ~1,21, 0,25 g'den 1 g'ye ~10,2 ml·kg⁻¹·dk⁻¹.
     - Kullanım: çıplak terimdeki β ve eğim teriminin yerçekimiyle ölçeklenmesi bu doz-yanıt eğrilerine uydurulur. EWT ise skafander terimini kalibre eder.

3. **Hız seçimi: kendini sınırlayan yürüyüş.** Her eğim ve sınıf için metre başına enerjiyi en aza indiren hız seçilir:

   $$V^*(G)=\arg\min_V \frac{M(V,G)}{V}\quad \text{koşullar: } M\le M_{cap}=f_{cap}\,\dot V O_{2,peak},\ \ V\le v_{wr}$$

   Varsayılan değer $f_{cap}$ = 0,5. EWT'deki 10 km'lik Ay geri dönüş yürüyüşü aerobik kapasitenin ~%50'siyle 2 saatin altında tamamlanmıştı. Sonuçlar L-18 tablolarına önceden hesaplanır, planlayıcı yalnızca tablo okur.

4. **Sarf dönüşümleri** (kaba hesap katsayıları):

   - **O₂.** 1 L O₂ ≈ 20,1 kJ, yoğunluk 1,429 g/L. Buradan $\dot m_{O_2}[\text{g/sa}]\approx 0{,}256\,M[\text{W}]$ çıkar. Örnekler: 300 W → 77 g/sa; 740 W → 189 g/sa. VO₂'den güce geçiş: $M[\text{W}]\approx 335\cdot \dot V O_2[\text{L/dk}]$.
   - **CO₂.** $\dot V_{CO_2}=RQ\cdot \dot V_{O_2}$, RQ ≈ 0,85.
   - **Isı ve su.** $Q=(1-\varepsilon_{mek})M+Q_{çevre}-Q_{rad}$ ve $\dot m_w=Q_{buh}/h_{fg}$, $h_{fg}\approx 2{,}45$ MJ/kg. Örnek: 450 W → ~0,66 kg/sa. Gale'de basınç ~7–9 hPa (REMS, mevsimsel) ve bu, suyun üçlü noktası olan 6,1 hPa'nın üstünde. Bu yüzden buharlaştırıcıyla ısı atma performansı belirsiz; geniş belirsizlikli bir parametre olarak modellenir ve duyarlılığı gösterilir.
   - **Batarya.** $P_{el}=P_0+k\,M$ (fan ve pompa yükü), parametrik.

5. **Çevrimiçi kestirim: mürettebatın dijital ikizi.** HR ile VO₂ arasında kişiye özel doğrusal bir kalibrasyon kurulur. Metabolik çarpan θ, rastgele yürüyüş durum modelli bir Kalman filtresiyle izlenir. θ güncellendikçe tüm sarf tahminleri ve walkback alanı da güncellenir.

**Belirsizlik.**

- θ kişi başına log-normal dağılır, σ ≈ 0,15–0,25.
- β, κ ve η parametrelerinin belirsizliği Monte Carlo'ya girer.
- θ yol boyunca tamamen korelasyonludur. Bu yüzden walkback varyansında ayrı bir terim olarak yer alır (M6).

**Doğrulama.** V3 (EWT/IST eğrilerinin yeniden üretimi).

**MVP → Stretch.** MVP: Pandolf yapısı + yerçekimi ölçeklemesi + sabit skafander terimi. Stretch: β ve κ'nın uydurulması, Kalman kestirimi, ısıl model.

**Sahibi.** R2 (R1 destekler).

### M2. Arazi ve kaya tehlikesi

**Amaç.** Her yönlü kenar için eğim, pürüzlülük, kaya ve sınıf kaynaklı maliyet ve kısıtları belirsizlikleriyle birlikte üretmek.

**Model**

1. **Eğim ve belirsizliği.**
   - HiRISE DTM'lerinin beklenen düşey hassasiyeti (Kirk ve ark. 2008): $EP\approx\rho\cdot GSD/(p/h)$, ρ ≈ 0,2. GSD 0,25–0,5 m ve p/h 0,2–0,5 için EP ~0,1–0,5 m.
   - FOM haritası olan DTM'lerde σ_z piksel bazında FOM'dan, olmayanlarda EP'den alınır.
   - Korelasyonsuz hata varsayımıyla üst sınır: $\sigma_s\approx\sqrt2\,\sigma_z/b$. σ_z = 0,17 m ile b = 1 m'de ~13,5°, b = 2 m'de ~6,9°, b = 5 m'de ~2,7° (kaba hesap).
   - Sonuç: 1 m tabanlı eğim kullanılamayacak kadar gürültülü; **2–5 m çok tabanlı eğim** kullanılır ve σ maliyete girer.
2. **Yönlü eğim.** Her kenar için $G_e=(z_v-z_u)/d_e$. Eğim yönlü olduğundan graf asimetriktir.
3. **Şans kısıtı.** $P(\lvert s\rvert>s_{max})\le\varepsilon \iff \lvert\mu_s\rvert+z_{1-\varepsilon}\sigma_s\le s_{max}$. Varsayılanlar: $s_{max}$ = 25°, 15°'nin üstünde hız cezası (parametre).
4. **Boxwork'e özgü bariyerler.**
   - 3–5 m pencerede yerel rölyef > 0,8 m ve eğim > 30° ise o hücre "sırt duvarı" sayılır ve geçilmez.
   - Sırtların alçak geçiş noktaları "kapı" olarak işaretlenir.
   - Sonuç: rota sırt tepeleri boyunca uzanır ve çukurları yalnızca kapılardan geçer. Bu, modelden kendiliğinden ortaya çıkan ve gösterilebilir bir davranış.
5. **Kaya tespiti.**
   - Tekil HiRISE görüntüsünde gölgeler segmentlenir (Huertas ve ark. 2006; Golombek ve ark. 2008, Phoenix iniş yeri). Geliş açısı i ve güneş azimutu görüntü etiketinden alınır.
   - Gölgenin güneşe dik genişliği kaya çapını verir: $D\approx$ genişlik. Gölge uzunluğu yüksekliği verir: $h\approx \ell_s\tan(90°-i)$.
   - Tespit edilebilen en küçük kaya çapı yaklaşık 1–1,5 m (4–6 piksel).
6. **Golombek–Rapp modeli ve çözünürlük altı kayalar.** Çapı D veya daha büyük kayaların kapladığı kümülatif alan oranı:

   $$F_k(D)=k\,e^{-q(k)D},\qquad q(k)=1{,}79+\frac{0{,}152}{k}$$

   k, 50 m'lik hücrelerde tespit edilen kayalardan (D ≥ D_min) en çok olabilirlik ile kestirilir. Birim alandaki kaya sayısı alan oranından türetilir. $E_1$ üstel integral olmak üzere:

   $$N(\ge D)=\int_D^\infty\frac{-F_k'(x)}{\pi x^2/4}\,dx=\frac{4kq}{\pi}\left[\frac{e^{-qD}}{D}-q\,E_1(qD)\right]$$

   Böylece HiRISE'ın göremediği 0,2–1 m'lik kayaların yoğunluğu da tahmin edilir.
7. **Poisson karşılaşma ve toplanabilir maliyet.** w efektif yürüyüş şeridi (~0,6 m) olmak üzere, bir kenarda eşik çaptan büyük bir kayayla karşılaşma olasılığı:

   $$P_e=1-e^{-N(\ge D^*)\,w\,L_e}$$

   Log-hayatta kalma toplanabilir olduğundan maliyet terimi $\lambda\,N w L_e$ yazılır ve yol boyunca hayatta kalma $\exp(-\sum N w L)$ olur. Bu sayede risk, Dijkstra'ya doğrudan eklenebilen bir maliyet hâline gelir.

   **Kaba hesap (k = %5 ⇒ q = 4,83 m⁻¹):**

   | D\* | N(≥D\*) | 1 km yolda beklenen karşılaşma (w = 0,6 m) |
   |---|---|---|
   | 0,5 m | ≈0,013 m⁻² | ≈8 (etrafından dolanma) |
   | 1,0 m | ≈0,0003 m⁻² | ≈0,18 |

**Belirsizlik.** σ_eğim, k'nın güven aralığı ve sınıf olasılıkları. Hepsi Monte Carlo'ya girer.

**Doğrulama.**

- AOI-V'de Curiosity'nin Navcam görüntülerinden elle sayılan kayalar ile model tahmini karşılaştırılır (stretch).
- V1 rota karşılaştırması da dolaylı bir doğrulama sağlar.

**MVP → Stretch.** MVP: eğim, pürüzlülük, kural tabanlı sınıf, sırt bariyerleri, basit kaya tespiti + Golombek uydurması. Stretch: SPOC benzeri segmentasyon ağı, FOM'lu σ_z.

**Sahibi.** R1.

### M3. Topografik radyasyon modeli (GCR) ve SEP modu

**Amaç.** Arazinin gökyüzünü kapatmasından doğan radyasyon korumasını harita olarak hesaplamak. Güneş fırtınası durumunda "sığınağa ulaşma süresi" alanını üretmek.

**Taban değerler.**

- Gale'de GCR soğurulmuş doz hızı 0,21 ± 0,04 mGy/gün, doz eşdeğeri 0,64 ± 0,12 mSv/gün (Hassler ve ark. 2014). Bu yaklaşık 8,75 µGy/sa ve 26,7 µSv/sa eder.
- 6 saatlik açık gökyüzü EVA'sı ≈ 160 µSv.
- Karşılaştırma: Dünya–Mars yolculuğu sırasında ~1,84 mSv/gün (Zeitlin ve ark. 2013). NASA'nın kariyer limiti 600 mSv (NASA-STD-3001).

**Yön bağımlılığı.** RAD ölçümleri zenit açısı bağımlılığını $J(\theta)\propto\cos^{\alpha}\theta$, α ≈ 1,18 olarak veriyor (Wimmer-Schweingruber ve ark. 2015). Bu üssün yoğunluk tanımına mı yoksa düz bir dedektörün akı tanımına mı ait olduğu kontrol edilecek. Fark, bir cos θ çarpanı demek. İki tanımla da hesaplanıp V2 ile seçilecek (Q4).

Daha ayrıntılı bir alternatif de var. Khaksarighiri ve ark. (2025, JGR Planets), Gale yükseltisi için zenit açısına bağlı **tepki matrisleri** çıkardı: yüzeye ulaşan ikincil parçacıkların birincil girdiye oranı, GCR ve SEP için ayrı ayrı. Bu matrisler veri olarak yayınlandıysa cos^α yaklaşımının yerine doğrudan kullanılır (Q13); özellikle $\alpha_{SEP}$'yi kestirmek için.

**Kapalı form.** Her azimut için ufuk yüksekliği h(φ) olsun. Ufkun altındaki yönler engellenir; gökyüzünde görünen açı θ < π/2 − h(φ) aralığıdır. $\int_0^{\Theta}\cos^\alpha\theta\sin\theta\,d\theta=(1-\cos^{\alpha+1}\Theta)/(\alpha+1)$ ve $\cos\Theta=\sin h$ olduğundan görünür gökyüzü faktörü:

$$F_\alpha(p)=\frac{1}{2\pi}\int_0^{2\pi}\Big[1-\sin^{\alpha+1}\big(h(p,\varphi)\big)\Big]d\varphi\ \approx\ \frac{1}{N_\varphi}\sum_{k=1}^{N_\varphi}\Big[1-\sin^{\alpha+1}\big(\max(h_k,0)\big)\Big]$$

Özel durumlar: α = 0 için F, düz gökyüzü katı açı oranıdır. α = 1 için iklim literatüründeki klasik sky-view factor $(1/N)\sum\cos^2 h_k$ elde edilir. Yani **F_α bu iki iyi bilinen ölçüyü genelleştirir.**

**Doz modeli.** Yüzeyden geri saçılan (albedo) bileşen ayrı yazılır:

$$\dot D(p)=\dot D_{açık}\Big[(1-f_a)\,F_\alpha(p)+f_a\,G(p)\Big],\qquad f_a\approx 0{,}18\text{–}0{,}24$$

MVP'de G = 1. Stretch'te G, yan duvarlardan gelen ek albedoyu temsil eden bir β terimiyle RAD verisine uydurulur. Charpentier ve ark. (2025, ön baskı) RAD verisiyle arazinin nötron ortamını da değiştirdiğini gösteriyor: rölyef arttıkça termal nötronlar artıyor, >1 MeV nötronlar azalıyor. Bu bulgu, G(p)'nin görünür arazi katı açısına bağlı modellenmesi gerektiğini destekliyor.

**Elle kontrol: Murray Buttes.** Ehresmann ve ark. (2021) burada gökyüzünün ~%19'u kapalıyken %4–5 doz düşüşü ölçtü. α = 1,18 ile iki uç geometri (kaba hesap):

| Geometri | Kapalı katı açı | Gökyüzü dozundaki düşüş | Toplam düşüş (f_a = 0,2) |
|---|---|---|---|
| Her yönde h = 11° | %19 | $0{,}19^{2{,}18}\approx$ %2,7 | ≈ %2,1 |
| 137°'lik sektörde h = 30° | %19 | $0{,}38\cdot0{,}5^{2{,}18}\approx$ %8,4 | ≈ %6,7 |

Ölçülen %4–5 bu iki ucun arasında. Sonuç, büyük ölçüde engelin **geometrisine** bağlı. V2'de RAD'ın bulunduğu noktadaki gerçek ufuk profili DEM'den çıkarılarak karşılaştırma yapılacak. Guo ve ark. (2021/2026) farklı arazilerde %19'a varan düşüşler raporluyor; bu noktalar da V2'ye eklenecek.

**Dürüst büyüklük değerlendirmesi.** Kaba hesapla 6 saatlik bir EVA'da arazi koruması 8–24 µSv kazandırır. Yolculuk dozunun yanında bu küçük. Bu yüzden GCR haritası planlayıcıda ALARA amaçlı bir eşitlik bozucu olarak kullanılır. **Asıl güvenlik etkeni SEP.** Bunu jüriye açıkça söylemek Validity puanını artırır.

**SEP modu**

- **Fizik.** SEP spektrumu daha yumuşaktır, eğik atmosfer kolonları parçacıkları daha çok durdurur. Bu yüzden akı zenitte daha yoğunlaşır: $\alpha_{SEP}>\alpha_{GCR}$ (uydurulacak). Ufuk engeli daha az işe yarar; boxwork'ün 1–2 m'lik sırtları anlamlı koruma sağlamaz.
- **Asıl sığınak PR.** PR'ye ulaşma süresi alanı:

  $$T_{sh}(x)=\min\big\{W_{PR}(x),\ T^{R}_{PR\to x}+\tau_{al}\big\}$$

  Yani ya mürettebat rovera yürür ya da rover mürettebata gelir (M8 ile ortak hesap).
- **SEP sırasında alınan doz.**

  $$D_{SEP}\approx\int_0^{T_{sh}}\dot D_{SEP}(t)\,F_{SEP}(x(t))\,dt+\text{(PR içinde zayıflatılmış doz)}$$

  $\dot D_{SEP}(t)$'nin biçimi, 20 Mayıs 2024 RAD zaman serisinden alınır.

**Uyarı bütçesi.** $\Delta_{uyarı}=t_{varış}-t_{algı}$.

| Algı kaynağı | Algı zamanı | 20 Mayıs 2024'te |
|---|---|---|
| PR ve skafander dozimetresi; yerel nowcast: doz hızı > 1,25 × arka plan (Löwe ve ark. 2025) | Olayın başında; tepe dozdan en az ~30 dk önce | Çalışırdı |
| Dünya tahmini (DONKI vb.) + DTN | Algı + OWLT (3–22 dk) + işleme | Kaynak bölge Dünya'dan görülmüyordu; yalnızca Solar Orbiter gördü |
| Mars yörüngesinde ya da Mars'a bakan bir varlık (ör. Solar Orbiter, MAVEN SEP) | Değişken | Yalnızca kısmen mümkün |

**Tasarım gereksinimi.** Dünya'dan gelecek uyarıya güvenme. Yerel nowcast'ın sağladığı ~30 dakikalık pencereyi esas al ve $T_{sh}$'yi bunun altında, pay bırakarak tut. Bu gereksinim FR-03'tür: rota üzerindeki her noktada $T_{sh}(x)\le T_{SEP,max}$ olmalı. Varsayılan 20 dk (30 dk − 10 dk pay; parametre). V5'te bu eşik, RAD'ın Mars yüzeyinde kaydettiği 16 SEP olayının her biri için ayrı ayrı test edilir.

**Doğrulama.** V2 (arazi koruması), V5 (SEP replay).

**MVP → Stretch.** MVP: ufuk küpü, F_α, GCR doz katmanı, PR'ye yürüme süresine dayalı $T_{sh}$. Stretch: rover karşılaması, albedo ve β uydurması, $\alpha_{SEP}$ kestirimi.

**Sahibi.** R1.

### M4. Aydınlatma, termal ve atmosfer

**Güneş.** SPICE ile güneşin konumu Mars gövde çerçevesinde hesaplanır ve sahada az/el değerine çevrilir.

**Gölge.** Gölge koşulu $el_{güneş}<h(p,\varphi_{güneş})$. **Ufuk küpünün ikinci kullanımı** budur: ek bir ışın izleme gerekmez. 10 dakikalık adımlarla gölge takvimi üretilir (L-13).

**Düşük güneş tehlikesi.** Güneş yüksekliği 15°'nin altındaysa uzun gölgeler kayaları gizler ve derinlik algısı bozulur. Bu durumda tehlike ağırlığı artırılır ve HUD uyarı verir (OFF-08). FR-12, gün batımından önce dönüş payı ister.

**Atmosfer.**

- NASA Ames MGCM çıktısından Gale hücresi için yerel saate bağlı sıcaklık, toz τ ve rüzgâr değerleri AmesCAP ile alınır.
- Stretch: eğim ve bakıya göre yerel ölçek küçültme.
- Doğrulama: REMS (V9, opsiyonel).

**Çıktılar.** M1 için $Q_{çevre}$, HUD için ışık durumu, UE5 için güneş yönü.

**Not.** UE5'te Cesium'un Dünya güneş bileşeni Mars için doğru değil. Directional light, ROS'tan gelen SPICE az/el ile sürülür.

**Sahibi.** R1 (R3 destekler).

### M5. Bilim değeri (Bayesçi)

**Amaç.** Aday her istasyonun bilim değerini, hipotezler arasındaki **beklenen bilgi kazancı** olarak ölçmek ve ölçüm geldikçe güncellemek.

**Model**

- **Hipotezler ve önsel.** H ∈ {H1, H2, H3}, önsel P(H). Önseli takım bilimcisi belirler ve öznel olduğu belgelenir.
- **İstasyon özellikleri.** Her aday istasyon s'nin özellikleri yörünge verisinden gelir: sırt ifadesi (L-05), sülfat indeksi (L-09), TI (L-08).
- **Olabilirlik.** $p(o\mid H,\text{özellik}(s))$. Örnek: belirgin sırt ifadesi olan yerde mineraloji farkını tespit olasılığı daha yüksek.
- **Bilgi kazancı.**

  $$\mathrm{EIG}(s)=I(H;O_s)=\sum_H\sum_o P(H)\,p(o\mid H)\log\frac{p(o\mid H)}{p(o)}$$

- **Küme değeri.** Gözlemler H verildiğinde koşullu bağımsızsa $f(S)=I(H;O_S)$ submodülerdir (Krause & Guestrin 2005). Kardinalite kısıtı altında açgözlü algoritma (1 − 1/e) garantisi verir. Rota bütçesiyle birleşince problem submodüler orienteering olur (Chekuri & Pál 2005). Pratik çözüm: M7'deki MILP marjinal değerlerle çözülür ve birkaç tur güncellenir.
- **Çevrimiçi güncelleme.** Ölçüm gelince posterior güncellenir, kalan istasyonlar yeniden sıralanır ve yeniden planlama tetiklenir (güvenlik kısıtları içinde). Dünya'daki bilim arka odası önselleri ve olabilirlikleri DTN üzerinden gecikmeli olarak değiştirebilir.
- **Kapsama.** Ağ ~100 m yükselti aralığına ve 14 km boyuna yayılıyor. Bu yüzden istasyonları yükselti ve konum bakımından dağıtmak için ek bir değer terimi var (stretch).

**Çıktı.** İstasyon başına değer, servis süresi ve zaman pencereleri. Görüntüleme için güneş yüksekliği > 30° gibi koşullar zaman penceresine girer.

**Doğrulama.** Doğu kenarı sonuçlarının (o1 yok, o2 var) posterior'u nasıl değiştirdiği gösterilir. Bu bir tutarlılık kontrolüdür.

**Sahibi.** R2 (bilim önselleri R1 ile).

### M6. Planlama çekirdeği: graf, walkback alanı, kırmızı çizgi

**Graf.**

- Küresel planlama 2 m ızgarada, yerel planlama 0,5–1 m ızgarada.
- 16 komşuluk kullanılır; 26,6° ve 63,4° yönleri metrikleşme hatasını azaltır.
- Kenarlar yönlüdür.

**Kenar maliyet vektörü.** Her bileşen ortalama ve varyansıyla:

$$\mathbf c_e=(t_e,\ O_{2,e},\ H_2O_e,\ E_e,\ \text{doz}_e,\ \text{risk}_e)$$

Bileşenler L-18 tablolarından, kaya oranından (M2) ve doz hızı × süreden (M3) gelir.

**Rotalar.** Ağırlıklı toplam $J=\sum_k w_k\mu_k+\lambda\,\text{Risk}$ ile hesaplanır. ε-kısıt süpürmesiyle üç kanonik Pareto rotası üretilir: **hızlı**, **güvenli** ve **bilim**.

**Walkback alanı.** H mevcut güvenli liman kümesi olsun. Tek bir skaler kenar maliyeti için $W(x)=\min_{\pi:x\to H} c(\pi)$, **ters graf üzerinde çok kaynaklı Dijkstra** ile hesaplanır. Bu ters çevirme önemli: maliyetler yönlü olduğu için x'ten limana yürümenin bedeli, limandan x'e yürümenin bedeline eşit değil. Gelecekteki rover istasyonu ancak varış zamanı ve oraya gerçekten erişilebilirlik doğrulandıktan sonra H'ye girer.

- **Etiket taşıma.** Skaler maliyetle seçilen **aynı dönüş yolu** boyunca t, O₂, H₂O ve varyansları toplanır. Her kaynağın ayrı en iyi yolunun maliyetini birleştirmek uygulanabilir tek bir rota göstermez. İlk sürümde bu ortak yol bütün sarf sınırlarını geçmezse nokta güvenli işaretlenmez; daha iyi ortak yol bulma, çok ölçütlü etiket algoritmasına bırakılır.
- **Riske göre düzeltilmiş walkback.** M1'den gelen metabolik çarpan θ yol boyunca tamamen korelasyonlu olduğu için ayrı bir terim olarak eklenir:

  $$W_\varepsilon(x)=\mu_W(x)+z_{1-\varepsilon}\sqrt{\sum_e\sigma_e^2+\big(\sigma_\theta\,\mu_W(x)\big)^2}$$

**Kırmızı çizgi ve pay.** j ∈ {O₂, H₂O, batarya, gün ışığı} sarf kalemleri için, bütün $W_j$ değerleri aynı uygulanabilir dönüş yolunda hesaplanmışsa:

$$m_j(t,x)=R_j(t)-R_j^{rez}-W_{j,\varepsilon}(x),\qquad \text{Kırmızı çizgi}(t)=\partial\{x:\ \min_j m_j(t,x)\ge 0\}$$

HUD'daki pay göstergesi dakika cinsindendir: $\min_j m_j/\dot r_j$.

**Dönüşü olmayan nokta.** Plan boyunca s noktasına kadar harcanan miktar $C_\varepsilon(s)$ olsun. Plan ancak şu koşul her s için sağlanıyorsa geçerlidir:

$$R_0-C_\varepsilon(s)-W_\varepsilon(x(s))\ge R^{rez}$$

**Zamana bağlı maliyetler.** SEP ve aydınlatma, epoch'lar halinde parçalı sabit maliyetlerle temsil edilir. SEP modunda amaç fonksiyonu "sığınağa süre"ye geçer (M3).

**Yeniden planlama.**

- Mevcut hedefe rota: D\* Lite (Koenig & Likhachev 2002).
- Walkback alanı: 2 m ızgarada yeniden Dijkstra. 3×3 km için ≤1,5 s hedef; ilgi bölgesiyle (ROI) daha hızlı.

**Monte Carlo senaryo sınaması.** N = 1000 koşu yapılır: θ, arazi gürültüsü ve olaylar örneklenir, her koşuda izleyici çalıştırılır. İhlal oranı Wilson aralığıyla raporlanır. Bu aralık, seçilen simülasyon dağılımı altındaki örnekleme hatasını gösterir; gerçek Mars EVA'sının ihlal olasılığını veya güvenliğini doğrulamaz. İzleyici ile planlayıcı kuralının aynı sonuç verdiği sınır durumları ayrıca sınanır.

**Rover için ayrı planlama.** Nav2 Smac Hybrid-A\* rover maliyet haritası (L-19) üzerinde çalışır; rover kısıtları insanınkinden farklıdır.

**MVP → Stretch.** MVP: Dijkstra, walkback, kırmızı çizgi, üç Pareto rotası. Stretch: D\* Lite, Monte Carlo, zamana bağlı maliyetler, WASM ile tarayıcıda "ya şöyle olsaydı" analizi.

**Sahibi.** R2.

### M7. Bilim duraklarının seçimi: zaman pencereli, stokastik orienteering

**Kümeler ve değişkenler.**

- Hedefler N = {1..n}, başlangıç 0, bitiş n+1, senaryolar Ω (|Ω| = S).
- Karar değişkenleri: $x_{ij},y_i\in\{0,1\}$, varış zamanı $a_i\ge0$, senaryo ω'da i noktasına kadar kümülatif O₂ $u_i^\omega$.

**Formülasyon.**

$$\max\ \sum_{i\in N}v_i\,y_i$$

Kısıtlar:

1. **Akış korunumu.** $\sum_j x_{0j}=1$, $\sum_i x_{i,n+1}=1$, $\sum_i x_{ik}=\sum_j x_{kj}=y_k$.
2. **Zaman ve pencereler.** $a_j\ge a_i+\tau_i+t_{ij}-M(1-x_{ij})$ ve $e_i y_i\le a_i\le l_i+M(1-y_i)$.
3. **Senaryo başına tüketim.** $u_j^\omega\ge u_i^\omega+o_i^\omega+o_{ij}^\omega-M(1-x_{ij})$.
4. **Her durakta walkback (senaryo yaklaşımı).** $u_i^\omega+W_i^\omega\le C-R^{rez}+M(1-y_i)\quad\forall\omega$.
5. **Bitiş tüketiminde CVaR** (Rockafellar & Uryasev 2000):

   $$\eta+\frac{1}{(1-\beta)S}\sum_\omega\zeta_\omega\le C-R^{rez},\qquad \zeta_\omega\ge u_{n+1}^\omega-\eta,\ \ \zeta_\omega\ge0$$

**Teori notu.** Senaryo yaklaşımının (Calafiore & Campi 2006) ihlal olasılığına ilişkin sonucu, örnekleme dağılımı ve matematiksel koşullar sağlandığında geçerlidir. Bu problemdeki varsayımlar ve ikili değişkenler için sonuç doğrudan uygulanmış sayılmaz. M6 Monte Carlo sınaması model içi duyarlılığı gösterir; gerçek EVA güvenliğine istatistiksel garanti vermez.

**Boyut ve çözücü.**

- Problem boyutu n ≤ 25 hedef, S ≤ 50 senaryo.
- MILP için HiGHS ya da OR-Tools kullanılır; CP-SAT tercih edilirse katsayılar tamsayıya ölçeklenir.
- Hedefler arası mesafe matrisi, her hedeften başlatılan Dijkstra'larla hesaplanır.
- **Canlı modda** ≤1 s'lik sezgisel yöntem (açgözlü ekleme + yerel arama) kullanılır. EVA öncesinde kesin MILP çözülür ve sezgiselin optimallik açığı raporlanır.

**İkili çalışma.**

- MVP: EV1 ve EV2 birlikte hareket eder.
- Stretch: aynı istasyonda sırt ve çukur görevleri bölünür. Bu, senkronizasyon kısıtlı takım orienteering problemidir; buddy mesafesi FR-05 ile sınırlanır.

**Sahibi.** R2.

### M8. Rover hareketli güvenli liman yerleşimi

**Amaç.** Mürettebatın planı boyunca **en kötü kurtarma süresini** en aza indirecek şekilde roverın istasyonlarını ve zamanlarını seçmek.

**Kurtarma süresi.**

$$R_c(x)=\min\{\,W_c(x),\ T^{R}_{c\to x}+\tau_{al}\,\}$$

Mürettebat üyesinin çalışamaz durumda olduğu senaryoda (OFF-06) mürettebat yürüyemez, bu yüzden:

$$R_c^{inc}(x)=\min\{T^R_{c\to x}+\tau_{al},\ \beta_{taşıma}W_c(x)\}$$

**Zaman segmentleri.** Plan segmentlere bölünür; örneğin 10 dakikada bir, k = 1..K. Her segmentin örnek noktaları $X_k$'dır. Aday rover istasyonları C, rover maliyet haritasında erişilebilir noktalardan örneklenir.

**Düğüm maliyeti.**

$$\kappa(k,c)=\begin{cases}\max_{x\in X_k}R_c(x) & \text{görüş hattı oranı}\ge\rho\ \text{ve } c \text{ erişilebilirse}\\ \infty & \text{aksi halde}\end{cases}$$

**Darboğaz dinamik programlaması (kesin çözüm).** c'den c''ye geçişe yalnızca $T^R(c',c)\le\Delta t_k$ ise izin verilir.

$$B_1(c)=\kappa(1,c),\qquad B_k(c)=\max\Big\{\kappa(k,c),\ \min_{c':\,T^R(c',c)\le\Delta t_k}B_{k-1}(c')\Big\},\qquad B^*=\min_c B_K(c)$$

- **Karmaşıklık.** $O(K\,|C|^2)$. K = 40, |C| = 400 için ~6,4 M işlem, yani anlık.
- **Eşitlik bozma.** $B^*$ sabitlendikten sonra rover sürüş mesafesini en aza indiren ikinci bir geçiş yapılır (leksikografik).
- **Önhesap.**
  - $W_c(x)$: her rota örnek noktasından ileri Dijkstra (|X| ≈ 200).
  - $T^R_{c\to x}$: rover grafında her aday istasyondan ileri Dijkstra (|C| ≈ 400).
  - Rota koridorunda 2 m ızgarada bu hesap onlarca saniye sürer.

**Ortak problem.** Rota ile rover yerleşimi karşılıklı birbirine bağlı. Blok koordinat inişi uygulanır (rota sabit → rover; rover sabit → rota), 2–3 tur. Yakınsama garantisi yok; sezgisel olduğu açıkça belirtilir.

**Literatür bağlamı.** Graf üzerinde p-merkez problemi (Hakimi 1964) ve hareketli tesis yerleşimi / dinamik p-merkez ailesi.

**Çıktılar.** İstasyon planı Nav2'ye hedef olarak gider. HUD'da roverın gelecek konumları "hayalet" olarak görünür.

**Değerinin kanıtı.** V7 ablasyonu: sabit rover ile optimize edilmiş rover karşılaştırılır; maksimum kurtarma süresindeki azalma yüzde olarak raporlanır.

**Sahibi.** R2 (Nav2 entegrasyonu R3).

### M9. Formal güvenlik: uçuş kuralları

**Uçuş kuralları.** Parametreler köşeli parantez içinde. FRET'e H0'dan sonra FRETish olarak girilecek.

| ID | Kural (doğal dil) | Tür | Sinyaller | Planlayıcıdaki karşılığı |
|---|---|---|---|---|
| FR-01 | Kalan O₂ her an [walkback O₂ (ε-kuantil)] + [rezerv]'in üstünde olacak | Değişmez | o2_rem, wb_o2_q, o2_res | M6 dönüşü olmayan nokta kısıtı |
| FR-02 | Aynı kural su/soğutma için | Değişmez | h2o_rem, wb_h2o_q | M6 |
| FR-03 | Rota üzerindeki her noktada sığınağa ulaşma süresi ≤ [T_SEP,max = 20 dk; senaryo varsayımı] | Değişmez | t_shelter | M6 + M8 kısıtı; eşik olayın gerçek güvenli süresi diye sunulmaz |
| FR-04 | SEP alarmı (doz hızı > [1,25] × arka plan; Löwe ve ark. 2025) yükseldikten sonra [30 s] içinde sığınak moduna geçilecek, [T_sh] içinde sığınakta olunacak | Tepki + zamanlama | dose_rate, dose_bg, mode, at_shelter | SEP modu amaç fonksiyonu; varış öncesi doz ayrıca raporlanır |
| FR-05 | EV1–EV2 mesafesi ≤ [100 m] ve görüş hattı var; ihlal [60 s]'den uzun sürmeyecek | Zamanlı değişmez | buddy_dist, buddy_los | M7 ikili çalışma |
| FR-06 | Rover bağlantısı (doğrudan veya röle) kaybı [300 s]'yi geçerse son bağlantı noktasına dönüş moduna geçilecek | Tepki | link_ok, mode | M10 görüş hattı kısıtı |
| FR-07 | M > M_cap durumu [5 dk]'dan uzun sürerse yavaşlama/dinlenme; HR > [0,9·HR_max] ise anında uyarı | Tepki | met_est, hr | M1 hız seçimi |
| FR-08 | Eğimi ≥ s_max olan hücreye girilmeyecek (konum σ dahil) | Değişmez | slope_here, pos_sigma | M2 şans kısıtı |
| FR-09 | σ_konum > [20 m] olursa [120 s] içinde yeniden lokalizasyon veya durma | Tepki | pos_sigma, mode | M11 |
| FR-10 | Kümülatif EVA dozu ≤ [EVA doz bütçesi] | Değişmez | dose_cum | M6 doz maliyeti |
| FR-11 | Skafander basıncı ∈ [p_min, p_max], ppCO₂ ≤ [limit] | Değişmez | p_suit, ppco2 | (Plan dışı; telemetri) |
| FR-12 | Gün batımından en az [T_dusk] önce PR'de olunacak | Değişmez | sun_el, eta_home | M6 zaman penceresi |
| FR-13 | Kurtarma süresi $R_c(x)\le$ [T_rescue,max] | Değişmez | t_rescue | M8 |
| FR-14 (E-01) | Helikopter EV'lere [30 m]'den yakın uçmayacak ve her an iniş noktasına [rezerv] bırakarak dönebilecek | Değişmez | heli_dist_ev, heli_batt, heli_wb | E-01 VoI planlayıcısı |
| FR-15 (E-05) | SEP alarmı aktifken mod ∈ {SIĞINAK, KURTARMA} | Değişmez (Kind 2 ile kanıtlanır, ayrıca izlenir) | sep_alert, mode | E-05 mod yöneticisi |

**İşlem hattı.**

1. **FRET.** Kurallar FRETish olarak yazılır. FRET her kuralın biçimsel anlamını gösterir ve simüle eder.
2. **Gerçekleştirilebilirlik kontrolü.** FRET'in Kind 2 / JKind tabanlı analizi (teyit) kuralların birbiriyle çelişmediğini kanıtlar. Bu çıktı jüriye gösterilebilecek bir kanıt.
3. **Ogma `ros` komutu.**
   - Girdiler: `--variable-db` (değişken → topic/tip eşlemesi; pratikte zorunlu, çünkü eşlemesi olmayan değişken için abonelik üretilmez ve Ogma uyarı da vermez), `--handlers`, `--variable-file`, `--target-dir`, gerekirse `--template-dir`.
   - Çıktı: Copilot izleyicisini saran bir ROS 2 paketi.
4. **Copilot → C99.** Ogma'nın dokümantasyonuna göre Copilot'un ürettiği izleyici kodu pakette `monitor.c` / `monitor.h` olarak elle yerleştiriliyor; bu adım `ros` komutuyla otomatik gelmiyor.
5. **Çalışma zamanı.** Düğüm yeni veri geldikçe izleyicileri yeniden değerlendirir. İhlaller kural başına `copilot/handler<KuralID>` topic'lerine yayınlanır. Bizim `safety_aggregator` düğümümüz bunları `/safety/violations` altında önem derecesi ve HUD metniyle birleştirir.

**Zamanlama semantiği.** "N saniye içinde" türü kurallar, izleyicinin düzenli adım atmasını gerektirir. Bu yüzden `/clock`'tan türetilen 10 Hz'lik bir tick topic'i izleyicilere girdi olarak verilir; deterministik adım sağlanır.

**Gerçek zamanlılık.** Copilot izleyicileri sabit bellek ve adım başına sabit süreyle çalışır, dinamik bellek ayırmaz. Bu sert gerçek zamanlı kullanım için uygun.

**Plan zamanında yeniden kullanım.** Aynı C99 kodu Monte Carlo simülatörüne bağlanır (ctypes/cffi veya C++). Böylece plan doğrulaması ile çalışma zamanı izlemesi **aynı semantiği** kullanır.

**Güvence argümanı.** GSN (Goal Structuring Notation) taslağı:

```
G1  "EVA-3 planı kabul edilebilir düzeyde güvenli"
 └─ S1  "Her uçuş kuralı için ayrı argüman"
     ├─ G1.1  "FR-01 plan boyunca sağlanıyor"
     │    ├─ Kanıt: Monte Carlo sonucu (ihlal olasılığının üst sınırı ≤ %1)
     │    └─ Kanıt: izleyici birim testleri
     ├─ G1.2  "Kurallar birbiriyle tutarlı"
     │    └─ Kanıt: FRET gerçekleştirilebilirlik kontrolü
     └─ G1.3  "Modeller geçerli"
          └─ Kanıt: V1–V3 doğrulama deneyleri
```

NASA'nın AdvoCATE aracı referans gösterilir; biz GSN'yi diyagram olarak çizeceğiz.

**Yedek (G2 kapısı).** Ogma'nın ROS desteği kendi dokümantasyonunda "preliminary" olarak geçiyor. H12'de çalışmıyorsa aynı FRET formüllerinden elle yazılmış bir C++ izleyici düğümüne geçilir. Spesifikasyon FRET'te kalır, böylece hikâye korunur.

**Sahibi.** R4.

### M10. İletişim ve DTN

**Mars yerel ağı.**

- Topoloji: PR'de bir zenohd router, EV'ler istemci veya eş olarak bağlanır; ROS 2 tarafında rmw_zenoh.
- **Bağlantı modeli.**
  - Görüş hattı DEM'den hesaplanır (PR anteni 3 m, skafander 2 m).
  - Görüş hattı varken serbest uzay yol kaybı uygulanır. Engel varsa tek bıçak sırtı kırınım cezası eklenir (ITU-R P.526 yaklaşımı).
  - Sonuçta SNR'dan paket kaybı eğrisi elde edilir.
- **Buddy rölesi.** EV1'in PR'ye görüş hattı yoksa ama EV2'ye varsa, trafik EV2 üzerinden yönlendirilir.
- **Emülasyon seçenekleri.**
  - A (MVP): `link_manager` uygulama seviyesinde, modele göre mesaj düşürür veya geciktirir. Deterministik ve kolay.
  - B (stretch): ağ isim alanları + `tc netem` ile gerçek ağ emülasyonu.

**Mars–Dünya hattı.**

- **DTN düğümleri.** ipn:1 = PR, ipn:3 = röle orbiteri (sakla-ilet), ipn:2 = Dünya MCC.
- **Protokoller.** Bundle Protocol v7 (RFC 9171), LTP (RFC 5326), Contact Graph Routing (CGR). Bunları ION sağlar; HDTN alternatiftir.
- **Kontak planı.** SpiceyPy ile orbiterin Gale'den görünen yüksekliği hesaplanır; yükseklik > 10° iken kontak açıktır. Hız orbitere göre parametriktir, ışık süresi SPICE'tan alınır. Sonuç ION kontak ve menzil kayıtlarına dönüştürülür.
- **2026 gerçekliği (Mars Relay Network sayfası).** MAVEN Aralık 2025'te sustu. Şubat–Mayıs 2026 ortalama günlük veri hacimleri:

  | Orbiter | Ortalama veri |
  |---|---|
  | TGO | ~2.228 Mb/gün |
  | MRO | ~851 Mb/gün |
  | Odyssey | ~107 Mb/gün |

  Orbiter başına günde 2–4 geçiş var. S2 varyantı bu kırılganlığı gösterir. S3 varyantı varsayımsal sürekli röleyi (MTN) gösterir.
- **Kavuşum.** Yaklaşık 26 ayda bir, ~2 hafta iletişim yok. Bu yüzden sistemin tamamen Mars'ta otonom çalışabilmesi gerekiyor.
- **Paket sınıfları ve öncelikleri.**
  1. Güvenlik ihlalleri
  2. Özet telemetri
  3. Bilim verisi (görüntü)
  4. Arka oda notları (Dünya → Mars yönünde)
- **DTN geçidi.** Seçili ROS topic'leri serileştirilip paket olarak gönderilir. Python'da pyion bağlamaları ya da ION'un komut satırı araçları kullanılır (teyit).
- **Dünya konsolu.** "Son alınan durum" ile "tahmini şimdi" yan yana gösterilir. Tahmin, son bilinen durumun plana göre ileri yürütülmesi ve belirsizlik konisiyle yapılır. Mars'ta olan bir olayın Dünya'ya ne zaman ulaşacağını gösteren bir zaman çizelgesi de bulunur.
- **Analog referans.** BASALT analog çalışmaları ve NASA Ames'in xGDS araçları; gecikmeli bilim arka odası iş akışı buradan alınıyor.

**Sahibi.** R3.

### M11. GPS'siz konum belirleme

**Sensörler (simüle).**

- UE5 kask kamerası (render)
- IMU, adım modeli
- PR'ye ve buddy'ye UWB mesafesi
- Kameradan güneş yönü

**Kestirici.**

- MVP: robot_localization ile EKF (2D + yönelim).
- Stretch: GTSAM ile faktör grafı.

**Ufuk çizgisi eşleştirme (ufuk küpünün üçüncü kullanımı).**

1. Görüntüde gökyüzü segmentlenir. Mars gökyüzü ile arazi arasındaki renk ve parlaklık farkı bunu kolaylaştırır. Ardından azimut boyunca ufuk profili çıkarılır.
2. Önsel konum çevresindeki aday noktalarda bu profil, ufuk küpündeki h(p, φ) ile karşılaştırılır. Yönelim kayması üzerinden normalize çapraz korelasyon hesaplanır; sonuç konum ve yönelim için bir olabilirlik haritasıdır.
3. Olabilirlik haritası, kovaryansıyla birlikte EKF'ye ölçüm olarak girer.

Prosedür: astronot 360° döner ("ufuk fix'i"). Gale'de güneyde Mount Sharp, kuzeyde krater kenarı güçlü işaretler sağlar. Literatürde benzer yöntemlerle onlarca metre mertebesinde hatalar raporlanıyor (Chiodini ve ark. 2017).

**Güneş pusulası.** SPICE'tan gelen güneş azimutu ile görüntüdeki güneş yönü karşılaştırılarak mutlak yönelim bulunur (MER'deki güneş bulma yöntemine benzer).

**Çıktı.** Konum ve kovaryans. σ büyüdükçe planlayıcı eğim kısıtlarını genişletir ve walkback hesabında 2σ elipsinin en kötü noktasını kullanır. FR-09 da bu σ'ya dayanır.

**Doğrulama.** V6: Gerçek Navcam panoramaları bilinen Curiosity konumlarında DEM'e karşı eşleştirilir ve hata ölçülür.

**Sahibi.** R4.

---

## 6. Yazılım tasarımı

### 6.1 Diller ve gerekçeleri

| Dil | Nerede | Neden |
|---|---|---|
| Python 3.12 | Veri hattı, bilim, ENV, simülasyon, DTN geçidi, doğrulama | GDAL/rasterio/SpiceyPy/AmesCAP ekosistemi |
| C++20 | Planlayıcı çekirdeği, ROS düğümleri, UE5 | Performans; ROS 2 ve UE5'in doğal dili |
| Haskell | Copilot spesifikasyonları (Ogma üretir) | NASA'nın runtime verification zinciri |
| C99 | Copilot'un ürettiği izleyiciler | Sert gerçek zamanlı, sabit bellek |
| TypeScript | Konsollar (React + CesiumJS) | Web arayüzleri |
| UE5 Blueprint + C++ | HUD, piyonlar, köprü | Hızlı UI iterasyonu |
| (Opsiyonel) Rust | Zenoh tabanlı link emülatörü | Zenoh'un doğal dili |

### 6.2 Planlanan repo yapısı

```
redline/
├─ contracts/      arayüz sözleşmeleri (H0–H2), katman şeması, koordinat sözleşmesi
├─ data/           veri hattı + STAC kataloğu
├─ models/         insan, arazi, radyasyon, bilim modelleri + testler
├─ planner/        C++20 çekirdek · ROS 2 sarmalayıcı · WASM hedefi
├─ safety/         FRET projesi · Ogma girdileri ve çıktıları · Copilot · izleyici paketi
├─ ros_ws/src/     rover, lokalizasyon, iletişim, simülasyon, köprü paketleri
├─ dtn/            ION/HDTN yapılandırmaları · SPICE'tan kontak planı üretici
├─ unreal/         UE5 projesi
├─ web/            React + CesiumJS konsolları
├─ scenarios/      senaryo dosyaları (S0–S3)
├─ validation/     V1–V8 deneyleri ve grafikleri
├─ docs/           tasarım belgesi, ADR'ler, proje sayfası
└─ compose.yaml
```

### 6.3 ROS 2 düğüm grafiği

| Düğüm | Dil | Girdi | Çıktı |
|---|---|---|---|
| sim_clock | Python | Senaryo | `/clock`, 10 Hz tick |
| scenario_player | Python | Senaryo dosyası | Olaylar (SEP, sızıntı, arıza) |
| ev_sim (×2) | Python | Rota, olaylar | Gerçek konum / biyomedikal / sarf değerleri |
| ue5_bridge | UE5 C++ (rosbridge) | Konum, rota, kırmızı çizgi, uyarılar | EV1 konumu (oyuncu), kask görüntüsü |
| human_model | Python/C++ | Biyomedikal, konum | Metabolik kestirim |
| consumables_estimator | Python | Sarf, metabolik kestirim | Sarf tahmini |
| localization | C++ | IMU, UWB, ufuk, güneş | Konum + kovaryans |
| skyline_matcher | Python/C++ | Kask görüntüsü | Ufuk fix'i |
| env_server | Python | SPICE, DONKI önbelleği, senaryo | `/env/sun`, `/env/dose_rate`, `/env/sep_alert` |
| planner_server | C++20 | Katmanlar, konum, tahminler | `PlanEva`, `Replan`, `/plan/route` |
| walkback_field | C++20 | İstasyonlar, tahminler | Walkback alanı, kırmızı çizgi, pay |
| science_optimizer | Python | Posterior, alanlar | `/plan/science_stops` |
| rover_placer | C++/Python | Rota, alanlar | `/rover/station_plan` |
| Nav2 yığını | C++ | İstasyon planı | Rover hız komutları |
| Gazebo | — | Hız komutları | Rover gerçek konumu |
| copilot_monitor | C99 (Ogma) | Kural girdileri | `copilot/handler<ID>` |
| safety_aggregator | Python | `copilot/*` | `/safety/violations`, güvenlik durumu |
| link_manager | Python | Konumlar, görüş alanı katmanı | `/comm/link/*`; mesaj düşürme/geciktirme |
| dtn_gateway_mars / earth | Python | Seçili topic'ler / paketler | Paketler / "earth" alanı topic'leri |
| tss_adapter (stretch) | Python/C | Sarf, konum | TSS-2025 tarzı UDP |
| rosbridge / foxglove_bridge | — | — | WebSocket |

**TSS uyumluluğu (stretch).** TSS-2025 şunlara karşılık gelen veri grupları yayınlıyor: UIA, DCU, IMU (POSX/POSY, HEADING), ROVER, SPEC (NAME, ID, DATA) ve EVA telemetrisi. `tss_adapter` bizim simülasyonumuzu bu biçimde dışa açar. Böylece bir SUITS takımının HUD'u REDLINE'a bağlanabilir, REDLINE de gerçek bir TSS sunucusunu okuyabilir.

### 6.4 Planlayıcı çekirdeği

- **Izgara deposu.** Belleğe eşlenmiş katmanlar (float16/32), 256×256'lık karolar.
- **`CostModel` arayüzü.** İnsan ve rover modelleri takılıp çıkarılabilir. Kenar maliyeti, tablo + katman okumasından anında hesaplanır; kenarlar bellekte tutulmaz.
- **Algoritmalar.**
  - Dijkstra (ikili yığın veya radix yığın)
  - Çok kaynaklı ters Dijkstra
  - D\* Lite
  - Sınırlı çok kriterli etiket ayarlama
  - HiGHS C++ adaptörü
  - Orienteering için sezgisel (ILS)
- **Determinizm.** Sabit tohumlar ve kararlı eşitlik bozma.
- **WASM (stretch).** ROS bağımlılığı olmayan çekirdek Emscripten ile derlenir. Habitat konsolu "ya şöyle olsaydı" analizlerini tarayıcıda yapar.

### 6.5 Güvenlik hattının pratik ayrıntıları

- FRET bir Electron/Node uygulaması; kurulumu H0 öncesinde test edilecek.
- Ogma ve Copilot için GHC + cabal gerekiyor. Derleme uzun sürebilir; **en riskli hazırlık kalemi** bu.
- Ogma'nın ROS örneğini uçtan uca çalıştırmak, H0 öncesi öğrenme hedefi.
- Ogma'nın ürettiği ihlal topic adları, `safety_aggregator` içinde eşlenir.

### 6.6 UE5 projesi

**Sürüm.** Cesium for Unreal ≥ 2.19.1'in desteklediği bir UE5 sürümü (IAU2015 Ay ve Mars elipsoid varlıkları bu sürümde eklendi).

**Seviye kurulumu.**

1. CesiumGeoreference'ta Ellipsoid = IAU2015_Mars, orijin = AOI merkezi.
2. Cesium Mars tileset'i (ion varlık 3644333).
3. Opsiyonel: bizim yüksek çözünürlüklü yerel karolarımız.
4. Bizim katmanlarımız raster overlay olarak tileset'in üstüne giydirilir. Böylece kırmızı çizgi ve tehlike katmanı araziye yapışık görünür (Mars elipsoidi ile davranışı teyit).

**Fizik ve hareket.**

- Dünya yerçekimi Z = −371 cm/s².
- Yürüme hızı M1'deki V\*(G) tablosundan gelir. Animasyon oynatma hızı bu hıza göre ölçeklenir.

**Piyonlar.**

- EV1 oyuncu kontrollü: canlı demoda bir takım üyesi yürür ve REDLINE tepki verir.
- EV2 ve rover vekili ROS'tan gelen konumlarla sürülür.

**HUD (UMG).**

- Çevre bölgelerde: pusula şeridi, sarf çubukları ve "kırmızı çizgiye dakika" sayacı, buddy ve rover göstergeleri, bağlantı ve DTN kuyruğu.
- Merkez boş bırakılır; arazi görüşü kapatılmaz.
- **Dünya uzayında:** rota şeridi (araziye yansıtılmış spline), kırmızı çizgi eğrisi, kaya işaretleri, SEP'te sığınak oku.
- Modlar: Navigasyon, Bilim, Acil durum.

**Köprü.**

- MVP: UE'nin yerleşik WebSockets modülüyle rosbridge v2 protokolü (subscribe/publish, throttle).
- Kask görüntüsü: SceneCapture2D → JPEG → CompressedImage, 2 Hz, 640×480.
- Stretch: UE içinde zenoh-c ile doğrudan Zenoh bağlantısı.

**Atmosfer.** SkyAtmosphere bileşeni Mars renklerine göre ayarlanır: gündüz karamel, gün batımında mavi (stretch).

**Performans.**

- Cesium'un maximum screen space error ayarı kullanılır.
- Gerekirse Lumen kapatılır.
- Hedef ≥45 fps.
- G3 kapısında yetmezse UE5 yalnızca kayıtlı video için kullanılır.

**VR.** OpenXR ile stretch.

### 6.7 Web konsolları

**Temel.** React + Vite + TypeScript, CesiumJS ≥ 1.133 (`Ellipsoid.MARS` bu sürümde eklendi) ve Cesium Mars tileset'i.

**Katman bindirme yöntemi (H0'da seçilecek, Q6):**

- (a) 3D Tiles üstüne imagery draping (sürüm desteği teyit edilecek)
- (b) Kendi arazimiz + globe
- (c) 2D yedek: OpenLayers/MapLibre ile planetosentrik derece karoları

**Karolar.** MVP'de `gdal2tiles` geodetic profiliyle statik karolar üretilir. Mars enlem/boylam dereceleri, geodetic karo şemasına doğrudan yerleştirilir (teyit).

**Görünümler.**

| Görünüm | İçerik |
|---|---|
| Habitat | Katmanlar, Pareto rotaları, ε kaydırıcısı, Monte Carlo raporu, rover istasyonları, skafander kütlesi kaydırıcısı |
| Tablet | Sonraki ara nokta, pay sayacı, mini harita |
| MCC | Gecikmeli telemetri, "tahmini şimdi", DTN kuyruğu, LMST/UTC saatleri, ışık süresi bandı |
| Bilim arka odası | Posterior grafiği, istasyon kartları, öncelikli not oluşturucu |

**Veri bağlantısı.** roslibjs (rosbridge) ya da Foxglove WebSocket.

### 6.8 Senaryo motoru

- **Senaryo dosyası şunları tanımlar:** tarih, AOI, mürettebat parametreleri, skafander profili, olay listesi (zaman, tür, parametre), tohumlar, zaman ölçeği.
- **Çalışma.** `sim_clock` ve `scenario_player` olayları zamanında enjekte eder. Her koşu MCAP olarak kaydedilir.
- **Test.** "Yeniden oynatma determinizmi": aynı senaryo + aynı tohum, aynı ihlal dizisini üretmeli.

### 6.9 Performans bütçeleri

| İşlem | Hedef | Not |
|---|---|---|
| Copilot izleyici adımı | <1 ms, 10 Hz | Sabit bellek |
| HUD veri güncellemesi | 10 Hz | rosbridge throttle |
| UE5 render | ≥45 fps | SSE ayarı |
| Walkback alanı (2 m, 3×3 km) | ≤1,5 s | C++; ROI ile daha hızlı |
| D\* Lite yeniden planlama | ≤0,5 s | Yerel |
| Bilim MILP (≤25 hedef, 50 senaryo) | ≤60 s | Sezgisel yöntem ≤1 s |
| Rover darboğaz DP | ≤1 s | Önhesap dakikalar sürer |
| Monte Carlo (1000 koşu) | ≤60 s | Paralel |
| Ufuk küpü (3×3 km, 2 m, 72 yön) | ≤10 dk | GPU/C++, süpürme algoritması |

### 6.10 Test stratejisi

**Analitik altın testler.**

- Düz düzlemde F = 1 ve W = mesafe × birim maliyet.
- Her yönde ufku h olan silindirik çukurda $F=1-\sin^{\alpha+1}h$, birebir.
- Eğimli düzlemde yokuş yukarı ve aşağı walkback asimetrisi Minetti eğrisiyle tutarlı olmalı.
- Golombek N(≥D), sayısal integral ile kapalı formun karşılaştırması.

**Özellik tabanlı testler (Hypothesis / RapidCheck).**

- W ≥ 0
- Üçgen eşitsizliği
- Küçük ızgaralarda Dijkstra = kaba kuvvet
- Darboğaz DP = kaba kuvvet (küçük K ve |C|)

**Entegrasyon (launch_testing).**

- S0 nominal senaryosunda hiçbir izleyici tetiklenmemeli.
- S1'de FR-04 sağlanmalı, ihlal topic'i boş kalmalı.

**CI.** Görsel arayüzsüz senaryo regresyonu, UE5 olmadan.

### 6.11 Gözlemlenebilirlik

- Foxglove düzenleri: planlayıcı, güvenlik ve iletişim panoları.
- Yapılandırılmış loglar.
- MCAP'ten otomatik grafik üretimi; doğrulama figürleri de buradan çıkar.

### 6.12 Eklenti mimarisi

Çekirdek, eklentilerin takıldığı sabit uzantı noktaları sunar. Bölüm 15'teki her eklenti bu noktalardan bir veya birkaçını kullanır.

| Uzantı noktası | Mekanizma | Örnek eklentiler |
|---|---|---|
| Katman sağlayıcı (LayerProvider) | Python paket giriş noktası. Çıktısı COG + STAC öğesi; bağımlılıklarını beyan eder | E-03, E-06, E-11, E-14 |
| Maliyet terimi (CostTerm) | C++ `pluginlib` eklentisi (Nav2'nin de kullandığı ROS 2 mekanizması). Kenar maliyet vektörüne bileşen ekler | E-06, E-08, E-14 |
| Kural paketi (MonitorPack) | FRET projesi + değişken veritabanı → Ogma `ros` / `cfs` / `fprime` | E-01 (FR-14), E-02, E-05 |
| Ajan (Agent) | Kendi ara katmanıyla gelen yeni bir araç ya da aktör. Mars yerel ağına zenohd veya bir köprü üzerinden katılır | E-01 (PX4), E-02 (cFS) |
| Planlayıcı stratejisi | Yeni üst seviye planlayıcı; mevcut aksiyonları çağırır | E-04, E-07, E-10 |
| HUD bileşeni | UE5 UMG widget'ı + topic aboneliği; bir veri varlığıyla kaydedilir | E-01, E-09, E-10 |
| Konsol paneli | React modülü (lazy yükleme) | E-04, E-09, E-11 |
| Senaryo olayı | scenario_player olay türü | E-01, E-12 |

**Eklenti manifesti.** Her eklentide şu bilgiler bulunur:

- ad ve sürüm,
- kullandığı uzantı noktaları,
- tükettiği ve ürettiği topic'ler ile katmanlar,
- kademe ve sahip,
- açma bayrağı.

Bayrak senaryo dosyasından okunur. Böylece her eklenti için V7 ablasyon tablosuna otomatik bir satır eklenir.

**Ara katman haritası** (tüm eklentiler açıkken):

```
            UE5 HUD ── rosbridge (WebSocket/JSON) ──┐
   Web konsolları ── roslibjs / Foxglove WS ────────┤
                                                    ▼
 PX4 (uORB) ─zenoh-pico─► zenohd ◄─rmw_zenoh─► ROS 2 Jazzy (Mars yerel ağı)
                                                    │         │          │
   cFS (cFE yazılım veri yolu) ◄─ RACS2: WebSocket + protobuf ┘          │
   F´ bileşenleri ◄─ protobuf/UDP (ros2_fprime_bridge) ───────┘          │
                                                                         ▼
                           ION (BPv7/LTP) ◄─ DTN geçidi ─► ROS 2 "earth" alanı
```

Bu şemada altı farklı haberleşme dünyası var: uORB, Zenoh, ROS 2, cFE yazılım veri yolu, F´ portları ve Bundle Protocol. Her geçişin bir sahibi ve bir entegrasyon testi olacak.

Önemli bir uyumluluk notu: Jazzy'den itibaren rmw_zenoh anahtarları mesaj tipi özetini (RIHS01) içeriyor. Bu yüzden Humble tabanlı bileşenler aynı Zenoh ağına doğrudan katılamaz (RK-17).

---

## 7. Doğrulama planı

| ID | Hipotez | Veri | Yöntem | Metrik | Başarı ölçütü | Yedek | Sahip | Kademe |
|---|---|---|---|---|---|---|---|---|
| V1 | Planlayıcı rover modunda Curiosity'nin gerçek rotasına yakın sonuç verir | D-10 (AOI-V), L-19 | Ardışık sol varış noktaları arasında planla | Ayrık Fréchet, Hausdorff, uzunluk oranı | Temel ağırlıklara göre medyan Fréchet'te iyileşme | Yalnızca görsel karşılaştırma | R2 | 1 |
| V1b | Rover sürücülerinin tercihleri maliyet ağırlıklarından çıkarılabilir | V1 | Ters optimizasyon (Maximum Margin Planning; Ratliff ve ark. 2006) | Öğrenilen ağırlıklar, geri tutulan sol'lerde hata | Yorumlanabilir ağırlıklar | Elle ayar | R2 | 3 |
| V2 | F_α modeli RAD'daki arazi doz düşüşlerini açıklar | D-08, Ehresmann 2021, Guo 2021/2026, L-10 | Ölçüm noktalarında DEM'den ufuk → tahmin | %-puan RMSE | Ölçümlerin belirsizlik bandı içinde | Yalnızca Murray Buttes | R1 | 1 |
| V3 | M1, NASA EWT/IST eğrilerini yeniden üretir | NASA TP-2009-214796, TP-2010-216115 | β, κ, η uydurması | ml·kg⁻¹·dk⁻¹ RMSE | 3/8 g skafanderli değerlerde makul hata | Tek nokta kalibrasyonu | R2/R1 | 1 |
| V4 | Seçilen varsayımlar altında planın duyarlılığı görünür | Simülasyon | Monte Carlo, N = 1000; Wilson aralığı; farklı hız ve O₂ tüketimi senaryoları | Model içi ihlal oranı ve aralığı; hangi varsayımda sınır aşılıyor | Sınır durumları ve varsayımlar açık; planlayıcı/izleyici kararları tutarlı | N = 200 | R2 | 1 |
| V5 | Yerel SEP uyarısı ile sığınağa erişim süresi karşılaştırılabilir | D-15, D-08, D-16 | Önce 20 Mayıs 2024 zaman dizisi; erişim varsa diğer 15 olay. Alarmdan tepeye ve birikmiş doza kalan süre ayrı ölçülür | Olay başına varış payı, sığınağa varana kadar alınan model dozu, başarısızlık sayısı | Başarı ve başarısızlıklar eksiksiz raporlanır; tüm olaylarda koruma iddia edilmez | Yalnızca 20 Mayıs 2024 | R4/R1 | 1 |
| V6 | Ufuk eşleştirme Gale'de çalışır | D-11 + bilinen konumlar | Panorama → profil → DEM eşleşmesi | Konum ve yönelim hatası | Onlarca metre mertebesi | Sentetik UE5 görüntüleri | R4 | 3 |
| V7 | Her modül güvenliğe ölçülebilir katkı sağlar | Simülasyon | Ablasyon: rover optimizasyonu yok / σ yok / radyasyon katmanı yok / anizotropi yok | Maks. kurtarma süresi, ihlal olasılığı, doz, EIG, EVA süresi | Her modülün katkısı tabloda | Dört yerine iki ablasyon | R2 | 2 |
| V8 | HUD hızlı anlaşılıyor | 5 kişi | Dört uyarı senaryosu, doğru tepkiye kadar geçen süre + kısa SUS anketi | Saniye, SUS | Tüm uyarılarda doğru tepki | Takım içi test | R6 | 2 |
| V9 (ops.) | MGCM sıcaklıkları REMS ile tutarlı | D-09, D-13 | Yerel saat eğrileri | K RMSE | — | — | R1 | 3 |
| V10 (E-03) | Yer–yörünge füzyonu σ_z'yi düşürür ve kaya modelini doğrular | D-20, D-02 | Navcam'den sayılan 0,2–1 m kayalar ile Golombek tahmini; füzyon DEM'i ile yörünge DEM'i | Sayım hatası, σ_z | Tahmin güven aralığında | Tek konum | R1 | E |
| V11 (E-08) | TI'li kayma modeli Curiosity'nin kum sürüşlerini açıklar | Cunningham ve ark. 2017 Tablo I, D-06 | Uydurma + çapraz doğrulama | Kayma RMSE | Yalnızca eğime dayalı modelden iyi | — | R2 | E |
| V12 (E-01) | SCOUT uçuşu kırmızı çizgiyi genişletir; VoI tahmini gerçek kazancı öngörür | Simülasyon | 3 uçuş; önce/sonra karşılaştırması | Kırmızı çizgi alanı, pay; VoI ile kazanç arasındaki korelasyon | Pozitif kazanç; anlamlı korelasyon | Tek uçuş | R2/R3 | E |

**V7 ablasyon tablosunun iskeleti.** Videonun ve proje sayfasının en ikna edici figürü bu tablo olacak. Değerler H0'dan sonra doldurulacak.

| Yapılandırma | Maks. kurtarma süresi | İhlal olasılığı | EVA dozu | Toplanan EIG |
|---|---|---|---|---|
| Tam REDLINE | — | — | — | — |
| − rover optimizasyonu | — | — | — | — |
| − DTM belirsizliği | — | — | — | — |
| − radyasyon katmanı | — | — | — | — |
| − metabolik anizotropi | — | — | — | — |
| ± her açık eklenti (6.12 manifestinden otomatik) | — | — | — | — |

---

## 8. Demo ve teslim

### 8.1 Canlı demo akışı (yerel jüri için 5–7 dakika)

| Zaman | Ekran | Anlatı | Sistem davranışı |
|---|---|---|---|
| 0:00 | Habitat konsolu | "Varsayımsal insan EVA'sı: Curiosity'nin 2025–2026'da incelediği boxwork sahası." | Gale'den AOI-E'ye yakınlaşma; katmanlar tek tek açılır |
| 0:45 | Habitat | "Üç rota, üç öncelik. Kırmızı çizgi şu an burada." | Pareto rotaları; Monte Carlo sonucu; rover istasyon planı |
| 1:30 | UE5 kask | "EV1 dışarıda. Kırmızı çizgiyi arazinin üstünde görüyorsunuz." | Oyuncu sırt tepesinde yürür; pay sayacı azalır |
| 2:30 | UE5 + bilim kartı | "İlk sırt–çukur çifti: mineraloji farkı var, kimya farkı yok." | Posterior güncellenir; 3. durak öne çıkar |
| 3:15 | UE5 tam ekran uyarı | "20 Mayıs 2024 olayını bu sahaya uygularsak ne olur?" | RAD zaman dizisi → FR-04 → sığınak rotası; varış payı ve varsayım etiketi |
| 4:15 | MCC konsolu | "Houston henüz hiçbir şey bilmiyor." | Zaman hızlanır; OWLT + kontak sonrası paket gelir; arka oda notu Mars'a gönderilir |
| 5:00 | Özet panosu | "Sonuç." | Kaçınılan doz, maks. kurtarma süresi, tamamlanan duraklar, kural durumu, kullanılan NASA verileri |
| 5:30 | Habitat kaydırıcısı | "Skafanderi 121 kg'dan 70 kg'a indirirsek…" | Kırmızı çizgi canlı olarak genişler (Impact) |

### 8.2 30 saniyelik video storyboard

Altyazılar İngilizce, rakamlar H0 sonrası gerçek sonuçlarla doldurulacak.

| Saniye | Görüntü | Altyazı fikri |
|---|---|---|
| 0–3 | Mars küresinden Gale'e yakınlaşma (Cesium Mars) | *Mars, Gale crater. Two astronauts. One walk.* |
| 3–8 | Katmanlar üst üste: eğim, kayalar, radyasyon gölgesi | *NASA orbital, rover and space-weather data → 20+ hyperlocal layers* |
| 8–12 | Pareto rotaları ve kırmızı çizgi halkası | *Every point gets a price: the cost of getting home* |
| 12–20 | UE5 kask: SEP alarmı → izleyici tetiklenir → yeni rota → rover hareket eder | *May 20, 2024: a flare Earth couldn't see* |
| 20–26 | MCC'nin olayı dakikalar sonra görmesi; arka oda notunun geri gelmesi | *Earth finds out 14 minutes later* (SPICE'tan gelen değer) |
| 26–30 | Sonuç kartı + NASA veri listesi | *Dose avoided, stops completed. REDLINE.* |

### 8.3 Alternatif: 7 slaytlık iskelet

1. Problem ve challenge boşluğu
2. Senaryo: 20 Mayıs 2024 + boxwork
3. Katmanlar ve kullanılan NASA verileri
4. Kırmızı çizgi + hareketli güvenli liman (teori)
5. Formal güvenlik ve DTN mimarisi
6. Doğrulama (V1–V7 figürleri)
7. Etki, başka sahalara taşınabilirlik, ekip

### 8.4 Proje sayfası iskeleti (İngilizce başlıklar)

1. Summary
2. The challenge gap
3. How REDLINE works
4. Space agency data used (STAC'tan üretilen tablo)
5. Validation
6. Architecture
7. Team
8. AI disclosure
9. Links (demo video, repo)

### 8.5 Teslim kontrol listesi

- [ ] 30 sn video **veya** en fazla 7 slayt; herkese açık bağlantılar; İngilizce
- [ ] En az bir NASA kaynağı açıkça listelenmiş (bizde 15+ var)
- [ ] AI beyanı: AI üretimi görsel/videoda görünür filigran; AI destekli kodun belirtilmesi; kullanılan araçların listesi
- [ ] Repo herkese açık, README'de çalıştırma adımları
- [ ] Teslim H38'de (23:00) tamam

---

## 9. Takım organizasyonu

### 9.1 Roller

| Rol | Alan | Sahip olduğu modüller | Yedek |
|---|---|---|---|
| R1 | Veri ve radyasyon bilimi | SS-01, 03, 04, 05; M2, M3, M4; V2, V9; bilim önselleri | R2 |
| R2 | Planlama ve optimizasyon | SS-02, 06, 07; M1, M5, M6, M7, M8; V1, V3, V4, V7 | R1 |
| R3 | ROS 2, rover, DTN, entegrasyon lideri | SS-08, 10, 14, 15; M10; sözleşme sahibi | R4 |
| R4 | Formal güvenlik ve lokalizasyon | SS-09, 11; M9, M11; V5, V6 | R3 |
| R5 | Unreal kask | SS-12; HUD; demo çekimleri | R6 |
| R6 | Konsollar, hikâye, video, teslim | SS-13; V8; video; proje sayfası; AI beyanı | R5 |

**Sözleşme sahipleri.** Arayüzler R3, planlayıcı API'si R2, katman şeması R1. Hikâyenin sahibi R6.

### 9.2 Sorumluluk matrisi (S = sorumlu, D = destek)

| | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| Veri hattı ve katmanlar | S | D | | | | |
| İnsan modeli | D | S | | | | |
| Planlayıcı / walkback / kırmızı çizgi | | S | D | | | |
| Rover yerleşimi + Nav2 | | S | D | | | |
| Güvenlik izleyicileri | | D | | S | | |
| DTN ve iletişim | | | S | D | | |
| Lokalizasyon | | | D | S | | |
| UE5 HUD | | | D | | S | D |
| Konsollar | | D | | | | S |
| Video ve teslim | D | D | D | D | D | S |

### 9.3 Çalışma kuralları

- **H0–H2 sözleşme dondurma.** Sözleşme sahibinin onayı olmadan değişiklik yapılmaz.
- **Trunk tabanlı geliştirme.** Küçük PR'lar ve hızlı inceleme. Ana dal her zaman çalışır durumda.
- **Entegrasyon treni.** H6, H10, H14, H18, H22, H26 ve H30'da. Trene yetişmeyen iş bir sonrakine kalır.
- **Kısa toplantılar.** Her trenden önce 10 dakika; konular: ne bitti, ne engelliyor, kesme listesi.
- **Uyku vardiyası.** Yedek çiftleri farklı vardiyalarda tutuldu, böylece her modülden biri hep uyanık.

  | Vardiya | Kişiler | Saat |
  |---|---|---|
  | A | R1, R3, R5 | H15–H19 (00:00–04:00) |
  | B | R2, R4, R6 | H19–H23 (04:00–08:00) |

---

## 10. 39 saatlik uygulama planı

**v0.4 kapsam kararı.** Aşağıdaki v0.3 blok planı kapasite üst sınırını ve teknik seçenekleri gösterir; varsayılan teslim taahhüdü değildir. Yarışmada uygulanacak dar çekirdek ve karar kapıları [JURI_DEGERLENDIRME.md](JURI_DEGERLENDIRME.md) içinde tanımlıdır. Altı rolün aynı anda sorunsuz çalışacağı, AOI verisinin hemen erişileceği ve bütün entegrasyonların ilk denemede geçeceği varsayılmamalıdır.

### 10.1 Kilometre taşları

| Taş | Zaman | Bitti sayılma ölçütü |
|---|---|---|
| K0 | H2 (11:00) | Sözleşmeler donduruldu; AOI'ler seçildi; veri edinimi başladı; senaryo şeması hazır |
| K1 | H6 (15:00) | **Yürüyen iskelet:** sahte katman → planlayıcı → rota topic'i → web haritası; UE5'te ROS'tan gelen konum; izleyici taslağı ihlal yayınlıyor; DTN Mars→Dünya ping'i çalışıyor |
| K2 | H12 (21:00) | Gerçek katmanlar v1 (eğim σ, kural tabanlı kaya, ufuk küpü, F_α); gerçek maliyetler; walkback ve kırmızı çizgi web'de; DEM'den Gazebo dünyası; en az 2 kural Ogma'dan geçmiş |
| K3 | H18 (03:00) | **Kademe 0 tamam (güvenlik ağı)**; UE5 Cesium Mars sahnesi + HUD v1 canlı veriyle |
| K4 | H24 (09:00) | Kademe 1: S1 SEP senaryosu uçtan uca; rover yerleşimi; Monte Carlo; V2 ve V3 ilk sonuçları |
| K5 | H30 (15:00) | **Özellik dondurma.** V1–V5 figürleri; demo MCAP'i kaydedildi |
| K6 | H34 (19:00) | Video son kurgu; proje sayfası; (varsa) slaytlar |
| K7 | H37 (22:00) | Teslim tamam; tampon başlar |
| — | H38:59 | Son teslim anı |

### 10.2 Rol bazında blok planı

| Blok | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| H0–H2 | AOI seçimi, veri edinimini başlatma, katman şeması | Planlayıcı API sözleşmesi, maliyet tablosu biçimi | Arayüz sözleşmeleri, repo, compose iskeleti | FR listesini FRET'e girmeye başlama | UE5 projesi, Cesium Mars, georeference | Konsol iskeleti, hikâye akışı |
| H2–H6 | DEM/ortho kırpma, eğim v0 | Sahte veriyle Dijkstra + walkback | Düğüm iskeletleri, rosbridge, sim_clock | Ogma örneğinden ilk iki kurala | rosbridge bağlantısı; EV piyonu ROS'tan | Harita + sahte katmanlar |
| **H6** | **K1 entegrasyonu: herkes** | | | | | |
| H6–H12 | σ_eğim, sırt haritası, kaya v1, ufuk küpü | M1 tabloları, kırmızı çizgi, Pareto | Gazebo DEM dünyası, Nav2 + Curiosity | FR-01/03/04/05, safety_aggregator | HUD v1: sarf, pusula, rota şeridi | Kırmızı çizgi ve rotalar web'de; habitat görünümü |
| H12–H18 | F_α, doz katmanı, gölge, görüş alanı | D\* Lite, Monte Carlo v0 | link_manager, iki DTN düğümü | EKF + UWB, FR-09; G2 kararı | Kırmızı çizgi araziye; SEP UI | MCC görünümü, tablet |
| H18–H24 (vardiyalı) | V2, V3 | Rover DP, bilim MILP | SPICE → kontak planı → ION; "earth" alanı | S1 senaryo dosyası, V5 hazırlığı | EV2, rover vekili, kamera rayları | Bilim arka odası görünümü |
| H24–H30 | V1 verisi, STAC, veri tablosu | V4, V7 | Entegrasyon lideri, MCAP kayıtları | V5; ufuk eşleştirme (stretch) | Cila, demo çekimleri | Video kurgusu, sayfa taslağı |
| **H30** | **Özellik dondurma** | | | | | |
| H30–H34 | Figürler | Tablolar | Demo kayıt tekrarları | İhlal demoları | Son çekimler | Video son kurgu, sayfa |
| H34–H38 | Kaynakça | Sayıların kontrolü | README, repo temizliği | AI beyanı kontrolü | Yedek render | **Teslim** |

### 10.3 Kademeler

| Kademe | İçerik | Ne zamana |
|---|---|---|
| 0 (olmazsa olmaz) | Veri hattı (ortho, DEM, eğim, kural tabanlı kaya, ufuk, F_α); M1 tabloları; Dijkstra, walkback, kırmızı çizgi; katmanlı web haritası; 30 sn video | H18 |
| 1 (olmalı) | UE5 HUD canlı veriyle; Copilot izleyicileri (≥4 kural); S1 SEP senaryosu; rover darboğaz DP; Monte Carlo; V1–V5 | H24–H30 |
| 2 (iyi olur) | SPICE kontak planlı DTN; MCC konsolu; EIG + MILP; EKF + UWB; Gazebo/Nav2 rover; V7, V8 | H30 |
| 3 (stretch) | ML segmentasyon; ufuk eşleştirme + V6; UE5'te zenoh-c; netem; VR; WASM; ters optimizasyon; termal ölçek küçültme; TSS adaptörü | Varsa |

**Kesme sırası** (geride kalınırsa ilk kesilen ilk sırada):

1. VR
2. zenoh-c
3. netem
4. ML segmentasyon
5. Ufuk eşleştirme
6. WASM
7. Ters optimizasyon
8. TSS adaptörü
9. MILP (yerine açgözlü sezgisel)
10. DTN (yerine gecikme kuyruğu)
11. Gazebo (yerine kinematik rover)

**Eklentiler ve kademeler.**

- Eklentiler ayrı bir "E" kademesi.
- Hangi eklentilerin yapılacağı G0 kapısında (H0) seçilir (15.2).
- E-05, E-08 ve E-12 küçük oldukları için çekirdekle paralel yürüyebilir.
- Diğer eklentiler ancak GE kapısında Kademe 0–1 yeşilse başlar.
- Geride kalınırsa eklentiler, çekirdeğin kesme listesinden **önce** kesilir.

### 10.4 Karar kapıları

| Kapı | Zaman | Soru | Hayırsa |
|---|---|---|---|
| G0 | H0 | Hangi eklenti paketi seçiliyor? | Varsayılan: 15.2'deki önerilen seçki |
| G1 | H6 | İskelet uçtan uca çalışıyor mu? | Herkes entegrasyona geçer, çalışana kadar |
| G2 | H12 | Ogma ROS hattı çalışıyor mu? | Aynı FRET formüllerinden elle yazılmış C++ izleyici |
| G3 | H18 | UE5 performansı ve köprü yeterli mi? | UE5 yalnızca video için (MCAP replay); canlı demo web'de |
| G4 | H24 | DTN kontak planı çalışıyor mu? | Geçitte simüle gecikme kuyruğu |
| GE | H24 | Kademe 0–1 yeşil mi? | Büyük eklentiler başlamaz; o kişiler çekirdeğe döner |
| G5 | H30 | Dondurma | Yeni özellik yok, yalnızca hata düzeltme |

---

## 11. Risk kaydı

| ID | Risk | Olasılık | Etki | Önlem | Tetik | Sahip |
|---|---|---|---|---|---|---|
| RK-01 | Entegrasyon gecikir | Yüksek | Yüksek | H6 iskeleti, 4 saatlik tren, sözleşme dondurma | K1 kaçarsa | R3 |
| RK-02 | Ogma ROS desteği "preliminary" | Orta | Orta | Ön öğrenme, G2 yedeği | H12 | R4 |
| RK-03 | UE5 + Cesium performansı | Orta | Orta | SSE ayarı, Lumen kapatma, G3 | fps < 30 | R5 |
| RK-04 | WSL2 ↔ Windows ağ sorunu | Orta | Orta | Mirrored mod; her şeyi localhost'ta çalıştırma yedeği | Bağlantı yok | R3 |
| RK-05 | Veri boyutu / indirme | Orta | Yüksek | `/vsicurl/` pencere okuma, renkli COG (~1 GB), AOI kırpma, mobil hotspot; ön indirme iznini sor (Q2) | H1'de indirme başlamadıysa | R1 |
| RK-06 | AOI-E'de FOM'lu DTM yok | Orta | Düşük | Birleşik DEM + EP tabanlı σ; gerekirse AOI-V | H2 | R1 |
| RK-07 | Kaya tespiti gürültülü | Orta | Düşük | Golombek uydurması gürültüye dayanıklı; ML stretch | — | R1 |
| RK-08 | α tanımı belirsiz | Düşük | Orta | İki tanımla hesapla, V2 ile seç | — | R1 |
| RK-09 | MILP yavaş | Düşük | Düşük | Sezgisel yöntem + zaman sınırı | >60 s | R2 |
| RK-10 | DTN derleme / yapılandırma | Orta | Düşük | Ön kurulum, G4 yedeği | H24 | R3 |
| RK-11 | Kapsam şişmesi | Yüksek | Yüksek | Kademe sistemi, H30 dondurma, kesme listesi | — | Herkes |
| RK-12 | Yorgunluk | Yüksek | Orta | Uyku vardiyası; kritik işler H24 öncesi | — | Herkes |
| RK-13 | Teslim / AI beyanı eksikliği | Düşük | Yüksek | H34 kontrol listesi | — | R6 |
| RK-14 | Ön çalışma kuralının ihlal edildiği algısı | Düşük | Çok yüksek | Bu belge dışında H0 öncesi hiçbir artefakt yok; belirsiz noktaları organizatöre sor | — | Herkes |
| RK-15 | Mekânın interneti / elektriği | Orta | Orta | Seyahat router'ı, çoklu priz, çevrimdışı dokümantasyon, Docker imajlarının önceden çekilmesi (araç kurulumu sayılır) | — | R3 |
| RK-16 | Eklentiler kapsamı şişirir | Yüksek | Yüksek | G0 seçimi, GE kapısı, ~40 kişi-saatlik tavan | H24'te Kademe 1 eksikse | R3 |
| RK-17 | RACS2 Humble/Jazzy uyumsuzluğu (rmw_zenoh RIHS01) | Orta | Düşük | Sunucu düğümünü Jazzy'de derlemeyi denemek; olmazsa ayrı konteyner + WebSocket ara düğümü | Derleme hatası | R4 |
| RK-18 | PX4'ün Zenoh desteği deneysel | Orta | Orta | SCOUT MVP'si PX4'süz kinematik modelle | PX4 SITL H18'de bağlanmadıysa | R3 |
| RK-19 | Gaussian splat desteği deneysel (bir UE hatasının düzeltmesi 5.8'de bekleniyor) | Orta | Düşük | Splat'ler CesiumJS'te veya kayıtlı videoda; UE5'te mesh | Çökme | R5 |
| RK-20 | LLM asistanı yanlış bilgi verir; AI beyanı eksik kalır | Orta | Orta | Yalnızca araç çağrısı, izleyici korumalı; test seti; açık beyan | Halüsinasyon oranı > %5 | R6 |
| RK-21 | Analog modunda çözünürlük farkı yanlış anlaşılır | Düşük | Orta | Sunumda açıkça "aktarılabilirlik gösterimi" olarak anlatılır | — | R6 |

---

## 12. H0 öncesi hazırlık (kurallara uygun)

Yapılacak olan yalnızca **araç kurulumu, öğrenme ve aracın kendi örnekleriyle deneme**. Proje kodu yazılmayacak ve sahaya özel veri işlenmeyecek.

**Herkes**

- [ ] WSL2 Ubuntu 24.04, Docker, Git, VS Code
- [ ] ROS 2 Jazzy temel eğitimleri
- [ ] Challenge metni, bu belge, ACR 2024 ve SUITS FY26 görev tanımı okundu

**R1: Veri ve radyasyon**

- [ ] Python ortamı: GDAL, rasterio, pyproj (IAU_2015 CRS'leri listeleniyor mu?), numba, PyTorch
- [ ] SpiceyPy + jenerik çekirdeklerle rastgele bir tarih için güneş konumu hesabı
- [ ] AmesCAP kurulumu ve kendi eğitim materyali
- [ ] Okuma: Hassler 2014, Ehresmann 2021, Guo 2026, Wimmer-Schweingruber 2015, Golombek & Rapp 1997, Kirk 2008, Siebach ve ark. LPSC 2026

**R2: Planlama**

- [ ] C++20 araç zinciri; HiGHS ve OR-Tools'un kendi örnekleri
- [ ] (Stretch) Emscripten
- [ ] Okuma: Koenig & Likhachev 2002, Rockafellar & Uryasev 2000, Vansteenwegen ve ark. 2011 (orienteering derlemesi), Krause & Guestrin 2005, Norcross EWT ve IST-1 raporları

**R3: ROS, rover, DTN**

- [ ] ROS 2 Jazzy + rmw_zenoh + Nav2 + Gazebo Harmonic
- [ ] Space ROS demoları (jazzy-2026.04.0): Curiosity demosu çalışıyor
- [ ] ION derlemesi + iki düğümle ping örneği; HDTN derlemesi
- [ ] rosbridge_server ve foxglove_bridge
- [ ] Docker imajlarının önceden çekilmesi  

**R4: Güvenlik ve lokalizasyon**

- [ ] **İlk iş:** GHC/cabal + Copilot + Ogma derlemesi. En riskli kalem bu.
- [ ] Ogma'nın ROS örneği uçtan uca çalışıyor
- [ ] FRET kurulumu + eğitimi (gerçekleştirilebilirlik analizi menüsü dahil)
- [ ] robot_localization eğitimi
- [ ] Okuma: Pérez ve ark. 2022 (Ogma ROS 2), FRET dokümantasyonu, Chiodini 2017

**R5: Unreal**

- [ ] UE5 (Cesium for Unreal ≥ 2.19.1 uyumlu sürüm) + Cesium for Unreal
- [ ] Cesium ion hesabı; Cesium Mars varlığı "Add to my assets" ile eklendi
- [ ] Cesium'un Ay/Mars eğitim seviyesi açıldı (IAU2015_Mars elipsoidi)
- [ ] UE WebSockets modülü ile basit bir echo testi
- [ ] Okuma: DUST makalesi, SUITS HUD yönergeleri

**R6: Konsol ve hikâye**

- [ ] Node, Vite, React; CesiumJS ≥ 1.133 Mars sandcastle örneği
- [ ] Video araçları (OBS, DaVinci Resolve)
- [ ] Space Apps teslim sayfası, değerlendirme kriterleri ve geçmiş kazananlar incelendi

**Eklenti hazırlıkları** (yalnızca G0'da seçilmesi muhtemel paketler için; yine yalnızca araç kurulumu ve aracın kendi örnekleri)

- [ ] **E-01:** PX4-Autopilot v1.17 SITL kurulumu. `px4_sitl_zenoh` hedefiyle Gazebo örneği çalışıyor; `rmw_zenohd` ile `ros2 topic list` çıktısında PX4 topic'leri görünüyor (R3)
- [ ] **E-02:** cFS + RACS2 köprü örneği çalışıyor; köprünün ROS 2 sunucu düğümü Jazzy'de derleniyor mu kontrol edildi (R4)
- [ ] **E-01/E-02 (opsiyonel):** F´ araçları ve ros2_fprime_bridge örneği
- [ ] **E-03:** NASA Ames Stereo Pipeline kurulumu + belgelerdeki MSL örneği (R1); Cesium for Unreal ≥2.24 Gaussian splat eğitimi (R5)
- [ ] **E-05:** Kind 2 kurulumu + Lustre eğitim örnekleri; Ogma'nın Lustre girdisi denendi (R4)
- [ ] **E-06:** Bir konformal tahmin kütüphanesi (ör. MAPIE) ve kendi eğitimi (R1)
- [ ] **E-09:** LLM API anahtarı ve araç çağrısı örneği (R6)
- [ ] **E-11:** NASA Earthdata hesabı açıldı (R1)

**Donanım ve lojistik**

- [ ] UE5 için GPU'lu dizüstü (en az bir tane)
- [ ] WSL2 + Gazebo için ≥32 GB RAM'li makine
- [ ] Seyahat router'ı, çoklu priz, uzatma kabloları
- [ ] Kurulum dosyaları için harici SSD (UE5 büyük)
- [ ] api.nasa.gov anahtarı (DONKI için; DEMO_KEY limitli)
- [ ] GitHub organizasyonu (boş)

---

## 13. Açık sorular

| ID | Soru | Kime / nasıl | Ne zamana |
|---|---|---|---|
| Q1 | Resources sekmesi hangi veri setlerini öne çıkaracak? Bu belge ona göre güncellenecek | Space Apps sitesi | 13 Kasım |
| Q2 | Ham kamu verisini H0 öncesi indirmek serbest mi? | Ankara etkinlik sorumlusu | Hemen |
| Q3 | AOI-E'de FOM'lu bir HiRISE DTM var mı? | HiRISE DTM listesi (H0'da) | H2 |
| Q4 | Wimmer-Schweingruber üssünün tanımı (yoğunluk mu, akı mı)? | Makale (H0'da) | H12 |
| Q5 | Ogma ROS backend'i Jazzy ile sorunsuz mu? | Ön deneme (araç örneğiyle) | H0 öncesi |
| Q6 | CesiumJS'te Cesium Mars 3D Tiles üstüne imagery draping destekleniyor mu? | Cesium dokümantasyonu / ön deneme | H0 öncesi |
| Q7 | TSS-2026 şeması 2025'ten farklı mı? | SUITS sayfası | H0 öncesi |
| Q8 | Mekânın ağ ve güç koşulları | Etkinlik sorumlusu | Hemen |
| Q9 | Takım üyelerinin donanımı (GPU, RAM) | Takım içi | Hemen |
| Q10 | 2026 ödül kategorileri listesi | Space Apps sitesi | H0 öncesi |
| Q11 | RACS2 köprüsünün ROS 2 tarafı Jazzy'de çalışıyor mu? | Ön deneme (aracın kendi örneğiyle) | H0 öncesi |
| Q12 | PX4 v1.17 Zenoh SITL, WSL2'de çalışıyor mu? | Ön deneme | H0 öncesi |
| Q13 | Khaksarighiri ve ark. (2025) tepki matrisleri veri olarak yayınlandı mı? | Makalenin ek materyali | H12 |
| Q14 | Salda için NASA kaynaklı en yüksek çözünürlüklü DEM hangisi? | Earthdata araması | H0 |
| Q15 | Takım hangi eklenti paketini istiyor? | Takım içi (G0) | H0 |

---

## 14. Sözlük

| Terim | Anlam |
|---|---|
| EVA | Araç dışı faaliyet; burada Mars yüzeyinde yürüyüş |
| EV1 / EV2 | Dışarıdaki iki mürettebat üyesi |
| PR | Basınçlı rover; ev ve güvenli liman |
| IV | Araç içinden EVA'yı destekleyen operatör rolü |
| Walkback alanı | Her noktadan güvenli limana dönüşün (riske göre düzeltilmiş) bedeli |
| Kırmızı çizgi | Walkback bedelinin kalan rezerve eşit olduğu sınır eğrisi |
| PNR | Dönüşü olmayan nokta |
| GCR / SEP / CME | Galaktik kozmik ışın / güneş enerjik parçacıkları / koronal kütle atımı |
| RAD | Curiosity'nin radyasyon dedektörü |
| LMST / LTST | Yerel ortalama / gerçek güneş saati (Mars) |
| OWLT | Tek yönlü ışık süresi |
| DTN / BPv7 / LTP / CGR | Gecikmeye dayanıklı ağ / Bundle Protocol 7 / Licklider Transmission Protocol / Contact Graph Routing |
| COG / STAC | Cloud Optimized GeoTIFF / SpatioTemporal Asset Catalog |
| DEM / DTM / FOM | Sayısal yükseklik / arazi modeli / Figure of Merit güven haritası |
| GSD / EP | Yer örnekleme aralığı / beklenen düşey hassasiyet |
| TI | Termal atalet |
| FRET / FRETish | NASA Ames'in biçimsel gereksinim aracı ve yapılandırılmış İngilizcesi |
| pmLTL | Geçmiş zamanlı metrik doğrusal zamansal mantık |
| Copilot / Ogma | NASA'nın akış tabanlı runtime verification dili / izleyici üretme aracı |
| CVaR | Koşullu riske maruz değer |
| EIG | Beklenen bilgi kazancı |
| OP-TW | Zaman pencereli orienteering problemi |
| D\* Lite | Artımlı yeniden planlama algoritması |
| Fréchet mesafesi | İki eğri arasındaki biçim benzerliği ölçüsü |
| Froude sayısı | $v^2/(gL)$; yürüyüş dinamiği benzerlik ölçüsü |
| ENU / TF / QoS / MCAP | Doğu-Kuzey-Yukarı çerçevesi / ROS dönüşüm ağacı / hizmet kalitesi / ROS kayıt biçimi |
| GSN | Goal Structuring Notation (güvence argümanı) |
| AOI | Çalışma alanı |
| Nowcast | Ölçüme dayalı, anlık kısa vadeli uyarı |
| VoI | Bilginin değeri: bir ölçümün plan maliyetinde sağlaması beklenen iyileşme |
| PX4 / uORB | Açık kaynak otopilot / PX4'ün iç mesaj veri yolu |
| uXRCE-DDS / zenoh-pico | PX4'ün ROS 2 köprüleri: DDS tabanlı / Zenoh tabanlı (deneysel) |
| cFS / cFE | NASA'nın uçuş yazılımı çerçevesi / çekirdek yürütücüsü (yazılım veri yolu dahil) |
| F´ (F Prime) | JPL'in bileşen tabanlı uçuş yazılımı çerçevesi; Ingenuity'de uçtu |
| RACS2 | JAXA'nın ROS 2 ↔ cFS köprüsü |
| Lustre / Kind 2 | Senkron veri akışı dili / SMT tabanlı model denetleyici |
| Konformal tahmin | Dağılım varsayımı olmadan kapsama garantisi veren tahmin kümeleri |
| GDOP | Konum doğruluğunun geometrik seyrelmesi |
| Gaussian splat | Sahneyi 3B Gauss dağılımlarıyla temsil eden fotogerçekçi görselleştirme |
| MoE | Uzmanlar karışımı modeli |
| Parker spirali | Güneş rüzgârının taşıdığı manyetik alan çizgilerinin spiral biçimi |

---

## 15. Eklentiler (E-01–E-14)

REDLINE çekirdeği (Bölüm 3–7) tek başına teslim edilebilir bir sistem. Eklentiler bu çekirdeğe 6.12'deki uzantı noktalarından takılan ve tek tek açılıp kapatılabilen modüller. Bir eklentiyi kapatmak V7 ablasyon tablosuna otomatik bir satır ekler; dolayısıyla her eklenti katkısını sayıyla kanıtlamak zorunda.

Altı kişilik bir takım 39 saatte bunların hepsini yapamaz. 15.1'deki matris ve 15.2'deki seçki, G0 kapısında (H0) hangi eklentilerin seçileceğine karar vermek için.

### 15.1 Seçim matrisi

Emek ölçeği (kaba): Düşük ≈ 5 kişi-saat · Düşük-orta ≈ 8 · Orta ≈ 12 · Orta-yüksek ≈ 16 · Yüksek ≈ 24+.

| ID | Eklenti | Ne katar | Jüri kriteri | Emek | Risk | Sahip | Yerine ne düşer |
|---|---|---|---|---|---|---|---|
| E-01 | SCOUT: helikopterle aktif algılama | Belirsizliği uçarak azaltır; kırmızı çizgi genişler | Creativity, Technology | Orta (MVP) / Yüksek (PX4) | Orta–yüksek | R3 + R2 | Ufuk eşleştirme, netem |
| E-02 | Uçuş yazılımı katmanı: cFS + RACS2 (+F´) | NASA uçuş yazılımı yığını; iki katmanlı izleme | Technology, Validity | Orta | Orta | R4 | TSS adaptörü |
| E-03 | Yer–yörünge arazi füzyonu + Gaussian splat | Santimetre ölçekli zemin; kaya modelini doğrular; fotogerçekçi UE5 | Data, Presentation | Orta–yüksek | Orta | R1 + R5 | ML segmentasyon |
| E-04 | 30 sollük kampanya planlayıcısı | Tek EVA'dan göreve geçiş; SEP olasılığı, doz bütçesi | Science, Mission Concept | Orta | Düşük | R2 | Ters optimizasyon |
| E-05 | Doğrulanmış mod yöneticisi (Lustre + Kind 2) | Mod mantığında matematiksel ispat | Validity | Düşük–orta | Düşük | R4 | — |
| E-06 | Konformal sınıflandırıcı + risk bütçesi tahsisi | Dağılımdan bağımsız garanti; ε'ların optimize bölüştürülmesi | Validity, Science | Düşük–orta | Düşük | R1 + R2 | — (ML gerektirir) |
| E-07 | Röle/işaret bırakma optimizasyonu | Bağlantı + lokalizasyon geometrisi | Creativity | Düşük | Düşük | R3 | — |
| E-08 | Rover terramekaniği (TI tabanlı kayma) | PR sürüş maliyeti Curiosity verisiyle gerçekçi | Validity | Düşük | Düşük | R2/R3 | — |
| E-09 | Doğal dil EVA asistanı (CAPCOM-AI) | Araç çağıran, kurallarla korunan sesli/yazılı asistan | Presentation, Impact | Orta | Orta | R6 | Bilim arka odası cilası |
| E-10 | Karşı-olgusal plan açıklaması | "Neden bu rota?" sorusuna cevap | Presentation, Validity | Düşük–orta | Düşük | R2 | — |
| E-11 | Analog modu: Salda Gölü ↔ Jezero | Taşınabilirlik + Türkiye'ye yerel bağ | Impact, Relevance | Orta | Düşük | R1 + R6 | MCC cilası |
| E-12 | Parker spirali bağlantı modeli | SEP olasılığı için fiziksel önsel | Science | Düşük | Düşük | R1 | — |
| E-13 | Ay portu (Artemis) | Aynı hat Ay'da | Impact | Orta | Düşük | R1 + R5 | — |
| E-14 | Gezegen koruma ve özel bölgeler katmanı | SE-7 uyumu, kirlenme kontrolü | Relevance | Düşük | Düşük | R1 | — |

### 15.2 Önerilen seçki

**v0.4 kararı:** Varsayılan eklenti seçkisi **boş**. Önce gerçek NASA verisiyle tek AOI için çalışan katmanlı harita, ortak dönüş yolu, açık varsayım kartı ve ölçülebilir SEP senaryosu teslim edilir. Ancak bu dört çıktı kaydedilip tekrar oynatılabildiğinde ve teslim materyali hazır olduğunda bir eklenti seçilir. Aşağıdaki v0.3 paketleri seçenek kataloğudur; ~40 kişi-saatin kalacağı öngörüsü güvenilir bir plan değildir.

**Önceki aday paket (~42 kişi-saat; varsayılan değil):**

1. **E-05 mod yöneticisi** (~8): R4'te, güvenlik zincirinin doğal devamı.
2. **E-08 rover terramekaniği** (~5): M8'deki rover sürüş maliyetini gerçekçi kılar.
3. **E-12 Parker spirali** (~5): SEP hikâyesine fizik ekler.
4. **E-01 SCOUT, MVP sürümü** (~12): kinematik helikopter + VoI planlayıcı. Videonun en güçlü yeni sahnesi.
5. **E-11 Salda ↔ Jezero** (~12): Ankara jürisi için yerel bağ ve CH-10'un somut kanıtı.

**Kapasite kalırsa sırayla:** E-10 → E-02 → E-07 → E-04.

**Koşullu:** E-06 yalnızca ML sınıflandırıcı yapıldıysa.

**Bu hackathon için önerilmeyenler:** E-09 (AI beyanını ve güvenlik anlatısını karmaşıklaştırır) ve E-13 (odağı dağıtır). Sunumda "gelecek iş" olarak anılır.

**Takımın güçlü yanına göre alternatif paketler:**

| Paket | İçerik | Ne zaman seçilir | Emek (kişi-saat) |
|---|---|---|---|
| P-Teori | E-05, E-06, E-08, E-10, E-12 | Takımda kontrol / optimizasyon ağırlığı varsa | ~34 |
| P-Wow | E-01 (PX4'lü tam sürüm), E-03 splat | UE5 ve simülasyon tecrübesi güçlüyse | ~40 |
| P-Uçuş yazılımı | E-02, E-05 | cFS / F´ bilen biri varsa; Best Use of Technology hedefi | ~20 |
| P-Görev | E-04, E-12, E-13 | Best Mission Concept hedefi | ~29 |

### 15.3 E-01 SCOUT: Mars helikopteriyle aktif algılama

**Gerekçe.** Kırmızı çizgiyi belirsizlik daraltıyor: σ_z (M2), kaya bolluğu k'nın güven aralığı ve sınıf belirsizliği şans kısıtlarında z·σ olarak payı yiyor. Payı artırmanın en ucuz yolu belirsizliği **ölçerek** azaltmak.

Ingenuity bunu yaptı. 72 uçuşta 128,8 dakika uçtu, 17 km yol aldı ve Perseverance için hava keşifçisi olarak kullanıldı. M2M hedefi SE-5 de tam bunu istiyor: sahayı astronotlardan önce ve onlarla eşzamanlı olarak robotik yöntemlerle incelemek.

**Araç profilleri (parametrik):**

| Profil | Kütle | Faydalı yük | Menzil | Kaynak |
|---|---|---|---|---|
| Ingenuity sınıfı | 1,8 kg | — | En uzun uçuş 704 m; maks. 10 m/s, 24 m irtifa | NASA |
| Chopper sınıfı (konsept) | ~30 kg altıgen rotor | 3 kg (3–10 kg aralığı) | Uçuş başına ~3 km | Grip ve ark. 2025; NASA NTRS 20250004293 |

**Teori: yol planlama için bilginin değeri (VoI).**

- **Sensör modeli.** Uçuş rotası ψ olsun. Helikopter, uçuş şeridi $\mathcal S(\psi)$ içindeki hücrelerde yükseklik belirsizliğini σ_heli'ye indirir (SfM ile birkaç cm; varsayım). 0,2–1 m'lik kayaları da doğrudan görür.
- **Bilginin değeri.** Ölçüm sonucu z uçuştan önce bilinmediği için beklenti alınır:

  $$\mathrm{VoI}(\psi)=\mathbb E_{z\mid\psi}\big[J^*_{önsel}-J^*(z)\big]$$

  Burada $J^*$, riske göre düzeltilmiş en iyi plan maliyetidir (ya da negatif pay).
- **Birinci dereceden yaklaşım.** Planın veya kırmızı çizginin şans kısıtının bağlayıcı olduğu hücreler "kritik" hücrelerdir. Kazanç, duyarlılık ile belirsizlik azalmasının çarpımıdır:

  $$\mathrm{VoI}(\psi)\approx\sum_{i\in\mathcal S(\psi)}\frac{\partial J^*}{\partial\sigma_i}\,(\sigma_i-\sigma_{heli})$$

  Duyarlılık, sonlu farkla ya da M6'daki kısıtların $z_{1-\varepsilon}\,\partial\sigma_s/\partial\sigma_z$ katkısından hesaplanır. Pratikte bir "kritiklik haritası" çıkar: en iyi k rotanın üzerinde ve payın küçük olduğu kırmızı çizgi kenarında yoğunlaşır.
- **Uçuş planı.** Şeritler örtüştüğünde aynı hücre bir kez sayılır, bu yüzden amaç bir kapsama fonksiyonu ve submodüler. Batarya bütçesi $L(\psi)\le L_{max}$ ve iniş pistine dönüş kısıtıyla bu bir orienteering problemine dönüşür. **M7'nin çözücüsü yeniden kullanılır.**
- **Gerçekleşen kazanç.** Ölçümden sonra posterior ile yeniden planlanır. Kırmızı çizgi alanındaki (m²) ve paydaki (dk) artış ölçülür (V12).

**Güvenlik.** FR-14 kuralı: helikopter EV'lere 30 m'den yakın uçmaz ve her an iniş noktasına rezerv bırakarak dönebilir. Bu kural Ogma ile ya `fprime` komutuyla F´ bileşeni olarak ya da `ros` komutuyla ROS 2 düğümü olarak üretilir.

**Yazılım ve ara katmanlar.**

- **MVP.** Kinematik helikopter (Python düğümü) + sensör modeli. Uçuş dinamiği yok; σ katmanını doğrudan günceller.
- **Stretch: PX4 v1.17 SITL + Gazebo.**
  - PX4'ün deneysel Zenoh desteği (`px4_sitl_zenoh` hedefi, `ZENOH_ENABLE` parametresi) uORB topic'lerini doğrudan rmw_zenoh'a açar. Helikopter Mars yerel ağına DDS köprüsü olmadan katılır.
  - uXRCE-DDS ajanı doğrudan DDS'e yayın yaptığı için rmw_zenoh ile birlikte çalışmaz; Zenoh yolunu bu yüzden seçiyoruz.
  - Mars uyarlaması: yerçekimi 3,71 m/s². Atmosfer yoğunluğu ~0,015–0,02 kg/m³, yani Dünya'nın %1–2'si; rotor itkisi yoğunlukla orantılı ölçeklenir (kaba hesap).
- **Opsiyonel F´.** Ingenuity'nin uçuş yazılımı F´ idi. Görev/yük uygulaması, Ogma `fprime` ile üretilen izleyici bileşeniyle birlikte F´ bileşeni olarak yazılır. ROS 2'ye bağlantı ros2_fprime_bridge ile (protobuf, UDP veya FIFO).
- **HUD ve konsol.** Uçuş şeridi, VoI ısı haritası, uçuş öncesi ve sonrası kırmızı çizgi.

**Demo anı.** "Planın en belirsiz üç bölgesi kırmızı. SCOUT iki dakikalık bir uçuşla oraları tarıyor; kırmızı çizgi genişliyor." Sayılar H0'dan sonra hesaplanacak.

### 15.4 E-02 Uçuş yazılımı katmanı: cFS + RACS2 (+F´)

**Gerekçe.** Gerçek uzay araçlarında esnek otonomi yazılımı ile uçuş-kritik işlevler ayrı katmanlarda çalışır. Space ROS bu iki dünyayı birleştirmeyi hedefliyor. JAXA'nın RACS2 köprüsü ROS 2 topic'leri ile cFE yazılım veri yolu mesajlarını birbirine çeviriyor ve Mayıs 2025'te ISS'teki Int-Ball2 robotunda yörüngede gösterildi.

**Tasarım: karma-kritiklik mimarisi.**

- **cFS tarafı (PR'nin uçuş bilgisayarı):** yaşam desteği ve skafander telemetrisinin toplanması, olay/telemetri sistemi, uçuş kuralı izleyicilerinin ikinci kopyası. Ogma cFS uygulaması üretebiliyor.
- **ROS 2 tarafı:** planlama, algı, HUD.
- **İki katmanlı izleme.** Aynı FRET kuralından hem ROS 2 izleyicisi hem cFS uygulaması üretilir. Biri ihlal görüp diğeri görmezse bu ayrışma başlı başına bir hata sinyalidir: veri yolu kaybı ya da zamanlama sorunu. Aynı spesifikasyonun iki farklı çalışma ortamında koşması, "N-version" fikrinin hafif bir biçimi.
- **Köprü.** cFS istemcisi ↔ WebSocket + protobuf ↔ ROS 2 sunucu düğümü (RACS2).

**Uyumluluk riski (RK-17).** RACS2'nin README'si Ubuntu 22.04, ROS 2 Humble ve cFE 6.7.0a'ya göre yazılmış. Jazzy rmw_zenoh anahtarlarındaki tip özeti yüzünden Humble düğümleri bizim Zenoh ağımıza doğrudan katılamaz.

- Plan A: RACS2'nin Python sunucu düğümünü Jazzy'de derlemek.
- Plan B: cFS ve Humble sunucusunu ayrı bir konteynerde çalıştırmak; WebSocket tarafını bizim grafiğe bağlayan küçük bir ara düğüm yazmak.

**Doğrulama.** Hata enjeksiyonu yapılır: veri yolu gecikmesi ve kaybı. İki katmanın ayrışmasının yakalandığı gösterilir.

**Demo anı.** Ekranın köşesinde iki ışık var: "ROS 2 izleyici" ve "cFS izleyici". SEP geldiğinde ikisi birlikte yanar. Hata enjeksiyonunda ise ayrışma uyarısı çıkar.

### 15.5 E-03 Yer–yörünge arazi füzyonu ve Gaussian splat

**Gerekçe.** HiRISE'ın göremediği 0,2–1 m'lik kayalar ve 10 cm'lik basamaklar yürüyen bir insan için önemli. Curiosity'nin sürüş sonu Navcam panoramaları PDS'te stereo türevleriyle birlikte duruyor: XYZ nokta bulutu, UVW yüzey normali, range, pürüzlülük ve eğim ürünleri.

Öncüller:

- JPL bu füzyonu Mars 2020 için operasyonel olarak yapıyor: "Landform contextual mesh" (Vona 2025).
- NASA Ames Stereo Pipeline'ın belgelerinde bir MSL Navcam örneği var.

**Model: belirsizlik ağırlıklı füzyon.**

- **Stereo hatası menzille büyür.** b taban çizgisi, f piksel cinsinden odak uzaklığı, σ_d alt-piksel eşleşme hatası olmak üzere:

  $$\sigma_r\approx\frac{r^2}{b\,f}\,\sigma_d$$

  b = 0,424 m, f ≈ 1236 px ve σ_d = 0,25 px varsayımıyla (teyit) 10 m'de ~5 cm, 20 m'de ~19 cm, 30 m'de ~43 cm eder (kaba hesap).
- **Önce hizalama.** Yer verisi yörüngeye ICP ya da DEM korelasyonuyla oturtulur. Başlangıç konumu PLACES ürünlerinden (D-10) alınır.
- **Hücre bazında ters-varyans (Kalman) füzyonu.** o yörünge, g yer verisi olmak üzere:

  $$\hat z=\frac{z_o/\sigma_o^2+z_g/\sigma_g^2}{1/\sigma_o^2+1/\sigma_g^2},\qquad \hat\sigma^2=\big(1/\sigma_o^2+1/\sigma_g^2\big)^{-1}$$

- **Sonuç.** Rover rotası boyunca σ_z keskin biçimde düşer. Navcam'den sayılan 0,2–1 m'lik kayalar Golombek tahminiyle karşılaştırılarak M2'nin çözünürlük altı kestirimi doğrulanır (V10).

**Görselleştirme: Gaussian splat.**

- Cesium, Nisan 2026'da 3D Tiles içinde LOD'lu Gaussian splat desteğini CesiumJS, Cesium for Unreal ve Cesium ion için duyurdu. glTF uzantıları: `KHR_gaussian_splatting` ve `KHR_gaussian_splatting_compression_spz`.
- Cesium for Unreal 2.24.0 (2 Mart 2026) bu uzantıyı yükleyebiliyor. Destek deneysel ve Niagara tabanlı; bir UE hatasının düzeltmesi UE 5.8'de bekleniyor (RK-19).
- Navcam/Mastcam görüntülerinden eğitilen splat'ler UE5'te fotogerçekçi yakın plan sağlar. Kamera pozları PDS'teki CAHV/CAHVOR modellerinden alınabilir (teyit). Eğitim GPU saati ister; stretch.

### 15.6 E-04 Kampanya planlayıcısı (30 sol)

**Gerekçe.** Tek bir EVA'yı optimize etmek yetmez. 30 günlük görevde hangi sol hangi EVA'nın yapılacağına, doz bütçesinin ve sarf malzemesinin sollara nasıl dağıtılacağına da karar vermek gerekir.

**Model: Markov karar süreci.**

- **Durum.** $s_d=(d,\ D_{küm},\ \text{stok},\ \text{yorgunluk},\ P_d(H),\ \text{PR konumu})$
- **Eylemler.** EVA (saha, süre) · rover sürüşü · dinlenme/bakım.
- **Belirsizlik.** SEP olayı, toz fırtınası mevsimi (Ls), röle temasları.
- **SEP oranı.** RAD, inişten bu yana Mars yüzeyinde 16 SEP olayı kaydetti (Löwe ve ark. 2025). Bu λ ≈ 1,3/yıl eder (güneş döngüsüne bağlı; maksimumda daha yüksek). Kaba hesapla:
  - 30 günde en az bir SEP olasılığı: $1-e^{-\lambda\cdot 30/365}\approx$ %10.
  - Tek bir 6 saatlik EVA içinde: ≈ %0,09.

  Yani SEP tek bir EVA için nadir, ama görev boyunca ~10'da 1. Tasarımda ihmal edilemez.
- **Amaç ve kısıtlar.** Beklenen toplam bilgi kazancı (EIG) en üst düzeye çıkarılır. Kısıtlar: $\mathrm{CVaR}(D_{küm})\le$ bütçe ve stok ≥ rezerv.
- **Çözüm.** Durum uzayı büyük. Bu yüzden rollout / Monte Carlo ağaç araması (MCTS) kullanılır; taban politika açgözlü EIG. EVA alt probleminin maliyetleri M6–M8'den önceden hesaplanmış tablolardan gelir.
- **İnsan faktörü.** Mars günü 24 sa 39 dk 35 s. Mars saatine kilitli bir programda mürettebatın uyku penceresi Dünya saatine göre her gün ~40 dakika kayar. Bu, planlayıcıya bir kısıt olarak girer.

**Çıktı.** Habitat ekranında kampanya Gantt şeması ve "bugün EVA yapmalı mıyız?" kartı (SEP önseli E-12'den gelir).

### 15.7 E-05 Doğrulanmış mod yöneticisi (Lustre + Kind 2)

**Modlar.** EVA mod makinesinin modları: NOMİNAL, BİLİM, DÖNÜŞ, SIĞINAK, KURTARMA, BAĞLANTI_ARAMA, LOK_KURTARMA, DURUŞ.

**Yöntem.** Makine Lustre'da senkron bir veri akışı programı olarak yazılır ve özellikler Kind 2 ile kanıtlanır.

**Kanıtlanacak örnek özellikler:**

- **P1:** SEP alarmı aktifken mod ∈ {SIĞINAK, KURTARMA}. Bu özellik FR-15 olarak çalışma zamanında da izlenir.
- **P2:** SIĞINAK modunda bilim hedefi hiçbir zaman aktif değil.
- **P3:** Hiçbir durumda iki çelişkili navigasyon hedefi aynı anda aktif değil.
- **P4:** Her moddan DURUŞ'a ulaşılabilir. Bu bir erişilebilirlik özelliği; tersinin değişmez olarak yazılmasıyla Kind 2'den bir tanık (karşı örnek) üretilerek gösterilir.

**Yeniden kullanım.** Ogma Lustre girdisini de kabul ediyor. Böylece aynı mod mantığından çalışma zamanı izleyicisi de üretilebilir.

**Çıktı.** Kanıtlanmış özellikler tablosu, güvence argümanına (M9 GSN) G1.4 olarak eklenir.

### 15.8 E-06 Konformal arazi sınıflandırıcı ve risk bütçesi tahsisi

**Bölünmüş konformal tahmin (adımlar).**

1. Kalibrasyon kümesinde uyumsuzluk skoru hesaplanır: $s_i=1-\hat p(y_i\mid x_i)$.
2. Eşik $\hat q$, bu skorların ⌈(n+1)(1−δ)⌉/n kuantili olarak alınır.
3. Tahmin kümesi: $C(x)=\{y:\hat p(y\mid x)\ge 1-\hat q\}$.
4. Garanti: veri değiştirilebilir (exchangeable) olduğu sürece $P(y\in C(x))\ge 1-\delta$; dağılım varsayımı gerekmez.

Nadir ama tehlikeli sınıflar için sınıf koşullu (Mondrian) sürüm kullanılır.

**Maliyete giriş.** İki seçenek: kümedeki en kötü sınıfın maliyetini almak (sağlam) ya da küme boyutuna göre ceza eklemek.

**Risk bütçesi tahsisi.**

- Toplam ihlal olasılığı modüller arasında bölüştürülür. Boole eşitsizliği şunu garanti eder: $\varepsilon_{eğim}+\varepsilon_{sınıf}+\varepsilon_{metab}+\ldots\le\varepsilon_{top}$.
- Bölüştürme sabit değil, optimize edilir. Ono & Williams'ın (2008) yinelemeli risk tahsisi, bağlayıcı olmayan kısıtlardan riski alıp bağlayıcı olanlara verir.
- Masahiro Ono, MTTT çalışmasının da yazarları arasında (teyit). Bu, REDLINE'ın MTTT soyuyla bağını güçlendiriyor.

**Etiket verisi.** Küçük, elle etiketlenmiş bir küme. AI beyanında belirtilir.

### 15.9 E-07 Röle/işaret bırakma optimizasyonu

- **Problem.** EV'ler k adet küçük röle / UWB işaret birimi taşır. Bunların rota üstünde ya da yakınında nereye bırakılacağı seçilir.
- **Amaç.**

  $$f(S)=\sum_{x\in\text{rota}}w_x\cdot\mathbb 1\big[\exists s\in S\cup\{PR\}:\ \mathrm{LOS}(s,x)\big]\;+\;\lambda\cdot g_{GDOP}(S)$$

  Lokalizasyon geometrisi terimi $\mathrm{GDOP}=\sqrt{\mathrm{tr}\big((H^\top H)^{-1}\big)}$ ile tanımlanır; H, UWB mesafe ölçümlerinin Jacobian'ı.
- **Çözüm.** Kapsama terimi submodüler, bu yüzden açgözlü algoritma (1−1/e) garantisi verir. GDOP terimi submodüler değil; açgözlü + yerel arama kullanılır ve sezgisel olduğu belirtilir.
- **Girdi ve çıktı.** Görüş alanı katmanını (L-15) kullanır. HUD'da "işareti buraya bırak" ipucu gösterilir. Etki V7'ye bir satır olarak girer: FR-06 ihlal olasılığındaki düşüş.

### 15.10 E-08 Rover terramekaniği

**Curiosity'nin deneyimi.**

- Sol 672, Moosilauke Valley: %77 kayma ve >20 cm tekerlek gömülmesi.
- Sol 709, Hidden Valley: ~%80 kayma.
- Sonrasında dört tekerleğin de kumda olduğu megadalga geçişlerinden kaçınıldı (Arvidson 2016).

**Literatür.** Cunningham, Nesnas & Whittaker (2017) termal ataletin kayma tahminini iyileştirdiğini gösterdi. İki uzmanlı modelde (mixture of experts) öğrenilen eşikler: yerdeki sıcaklık sensörü (GTS) için ~69, THEMIS için ~453 J m⁻² K⁻¹ s⁻½. Düşük termal atalet, gevşek ve kaygan kum anlamına geliyor.

**Model.**

- Kayma: $s(\theta,TI)=\pi(TI)\,f_1(\theta)+\big(1-\pi(TI)\big)\,f_2(\theta)$; π bir softmax kapısı.
- Efektif hız $v_{eff}=v_{cmd}(1-s)$; enerji $\propto 1/(1-s)$.
- Kayma > %40 ise hücre geçilmez kabul edilir (parametre). Curiosity'nin otomatik %60 sınırı vardı.
- PR, Curiosity'den çok daha ağır. Aynı kumda daha kötü davranır; ölçek düzeltmesi Bekker–Wong modeliyle yapılır (stretch).

**Çıktı.** Rover maliyet haritası (L-19), M8'deki $T^R$ ve Nav2 costmap. Doğrulama: V11.

### 15.11 E-09 Doğal dil EVA asistanı (CAPCOM-AI)

**Kullanım.** Örnek sorular: "Payım ne kadar?", "Neden sola dönüyoruz?", "Sıradaki istasyonu atlarsak ne kazanırız?"

**Mimari.**

- LLM yalnızca araç çağırır: QueryWalkback, QueryCost, ExplainRoute (E-10), ScienceCard, ProposeReplan.
- Önerdiği yeniden planlar planlayıcıdan ve izleyicilerden geçmeden uygulanamaz.
- LLM komut zincirinde değil, danışma katmanında durur. Güvenlik kararı her zaman FR izleyicilerindedir.

**Gerçekçilik notu.** Mars'ta internet yok.

- Hackathon demosunda model bir API üzerinden çalışır (ör. Anthropic Claude, güncel model). Uçuşta yerel bir küçük modelin gerekeceği belgede ve AI beyanında açıkça yazılır.
- Daha gerçekçi bir yerleşim: Dünya'daki bilim arka odası. Orada internet var; asistan gecikmeli not yazımına yardım eder.

**Değerlendirme.** 20 soruluk bir test seti hazırlanır. Cevapların araç çıktılarıyla tutarlılığı ölçülür (halüsinasyon oranı; RK-20).

### 15.12 E-10 Karşı-olgusal plan açıklaması

**Soru.** "Neden alternatif rota A' değil de A?"

**Yöntem.**

1. **Maliyet ayrıştırma.** $J(A')-J(A)=\sum_k w_k\big(\mu_k(A')-\mu_k(A)\big)+\lambda\,\Delta\text{Risk}$. En büyük katkıyı yapan terimler gösterilir.
2. **Kısıt tanığı.** A' hangi kuralı, nerede ve ne kadar payla ihlal ediyor (FR kimliği, konum, pay).
3. **Asgari değişiklik.** Hangi ağırlık ya da eşik ne kadar değişseydi A' optimal olurdu? Ters optimizasyon kullanılır; altyapı V1b ile ortak.
4. **Gölge fiyatlar.** MILP'in dual değerlerinden çıkan cümleler: "Rezervi 5 dk azaltsaydınız 3. durak plana girerdi."

**Çıktı.** Tek cümlelik açıklama + haritada işaret. Örnek: "Kısa rota 12 dk kazandırırdı ama 1,2 km'de pay −4 dk olurdu (FR-01)."

### 15.13 E-11 Analog modu: Salda Gölü ↔ Jezero

**Neden Salda.** NASA Earth Observatory'ye göre Salda Gölü (Burdur), Jezero'dakine benzer karbonat mineralleri ve delta yapıları içeren, Dünya'da bilinen tek göl. Kıyıdaki beyaz çökeller hidromanyezit. 2019 yazında Perseverance bilim ekibinden Briony Horgan (Purdue) ile İstanbul Teknik Üniversitesi'nden bir ekip sahada çalıştı.

**Yapılacaklar.**

1. Aynı veri hattı Dünya'da, NASA verileriyle çalışır: NASADEM (30 m), Landsat 8/9 OLI, ASTER, HLS (D-21; çözünürlük Q14 ile teyit).
2. Mars'taki ikizi Jezero: Cesium Mars'ta 6 m görüntü / 20 m arazi; CTX DTM.
3. M1, 1 g'de (Pandolf'un özgün kalibrasyonu) çalıştırılır. Böylece yerçekimi ölçeklemesinin yönü kontrol edilmiş olur.
4. Yan yana görünüm: "Salda'da 4 saatlik bir yürüyüşün kırmızı çizgisi ↔ Jezero'da aynı yürüyüş."

**Değeri.** CH-10 için somut kanıt; Ankara jürisi için yerel bağ; Türkiye'deki analog saha çalışmaları için bir araç.

**Sınır (RK-21).** 30 m ile 1 m arasındaki çözünürlük farkı açıkça söylenir. Salda modu bir aktarılabilirlik gösterimidir, metre ölçekli bir EVA planı değildir.

### 15.14 E-12 Parker spirali bağlantı modeli

**Fizik.** Güneş rüzgârının taşıdığı manyetik alan çizgileri bir Arşimet spirali çizer. Gözlemciye manyetik olarak bağlı olan kaynak boylamı, gözlemci–Güneş doğrultusuna göre batıya kayar:

$$\Delta\phi\approx\frac{\Omega_\odot\,r}{v_{sw}}$$

- $\Omega_\odot\approx 2{,}87\times10^{-6}$ rad/s (25,4 günlük yıldızıl dönme).
- $v_{sw}$ = 400 km/s için Dünya'da (1 AU) ≈ 61°, Mars'ta (1,52 AU) ≈ 93° (kaba hesap).
- Sonuç: Mars'a en iyi bağlanan bölge, Mars'tan görülen güneş diskinin batı kenarına çok daha yakın.

**Kullanım.**

1. DONKI FLR/CME kaydındaki kaynak konumu (Dünya'dan görülen boylam) alınır.
2. SPICE ile hesaplanan Dünya–Mars açısal ayrımı kullanılarak Mars'ın baktığı heliografik boylama çevrilir.
3. Kaynağın Mars'ın bağlantı ayağına uzaklığı hesaplanır.
4. Bu uzaklıktan SEP olasılığı ve şiddeti için bir önsel çıkarılır. Lojistik model kullanılır; parametreleri RAD'ın 16 olayı ve DONKI kayıtlarıyla uydurulur (stretch).

**Literatür.**

- Aran ve ark. (2007): 1989'da Phobos-2'nin gördüğü olay. Kaynak ile Mars arasındaki boylam farkı yalnızca 2–3° idi ve olay Mars'ta "merkez meridyen olayı" özelliği gösterdi.
- Khaksarighiri ve ark. (EGU 2026): 9 Ekim 2024 olayı çok sayıda noktada, Mars yüzeyi dahil, algılandı.

**Sınır.** Geniş şok cepheleri ve alanlar arası difüzyon nedeniyle iyi bağlı olmayan gözlemciler de SEP görebilir. 9 Ekim 2024 olayı bunun örneği. Bu yüzden önsel yalnızca olasılığı ayarlar; güvenlik kararı her zaman yerel nowcast'tadır (FR-04).

**Çıktı.** E-04 için SEP önseli; HUD'da "Güneş'te Mars'a bakan aktif bölge var" bilgi kartı (Dünya'dan gelirse gecikmeli).

### 15.15 E-13 Ay portu (Artemis)

Aynı çekirdek Ay'da farklı fizikle çalışır:

- **Radyasyon.** Atmosfer olmadığı için GCR'nin zenit bağımlılığı atmosferden gelmez. Görünür gökyüzü katı açı oranına yaklaşır (α → 0). M3'teki formül α parametresiyle bu durumu zaten kapsıyor.
- **Aydınlatma.** Güney kutbunda birinci derece kısıt. Ufuk küpü + SPICE olduğu gibi kullanılır.
- **Metabolizma.** 1/6 g. EWT ve IST-1'in ana konusu zaten Ay; kalibrasyon verisi doğrudan mevcut.
- **Veri.** Cesium Moon, LRO LOLA ve NAC DTM'leri (D-22).
- **İletişim.** DTN aynı kalır; ışık süresi ~1,3 s.

**Değeri.** Artemis bağlantısı (Impact) ve REDLINE'ın tek seferlik bir Mars demosu değil, bir platform olduğunun gösterimi.

### 15.16 E-14 Gezegen koruma ve özel bölgeler katmanı

- **Dayanak.** M2M SE-7: özel ilgi alanlarını korumak (Mars'ta ör. tekrarlayan yamaç çizgileri, RSL).
- **Gale'e uyarlama.** Gale'de bilinen bir RSL yok, ama katman genel tasarlanır. Kirletilmemesi gereken bölgeler (bozulmamış örnek yüzeyleri, ileride sondaj hedefleri) yasak ya da cezalı alan olarak işaretlenir. PR'nin ısı ve egzoz izleri de bu katmana girer.
- **Planlayıcıya giriş.** CostTerm eklentisi olarak: yasak bölge sert kısıt, tampon bölge yumuşak ceza.
- **Ayak izi katmanı.** EVA günlüğünden mürettebatın daha önce yürüdüğü yerler çıkarılır. Bu noktalardan örnek almaya kirlenme cezası uygulanır.

### 15.17 Eklentilerin çekirdeğe etkisi (özet)

| Eklenti | Yeni kural | Yeni doğrulama | Yeni katman / veri | Dokunduğu bölümler |
|---|---|---|---|---|
| E-01 | FR-14 | V12 | σ güncellemesi, VoI ısı haritası | M2, M6, M7, M9, HUD |
| E-02 | (FR'lerin cFS kopyası) | Hata enjeksiyonu | — | M9, 6.12 |
| E-03 | — | V10 | Füzyon DEM'i, splat tileset'i (D-20) | M2, 6.6 |
| E-04 | — | — | Kampanya tablosu | M5–M8, habitat ekranı |
| E-05 | FR-15 | Kind 2 kanıtları | — | M9 GSN |
| E-06 | — | Kapsama oranı testi | Sınıf kümeleri | M2, M6 |
| E-07 | — | V7 satırı | İşaret noktaları | M10, M11 |
| E-08 | — | V11 | L-19 güncellemesi | M8, Nav2 |
| E-09 | — | 20 soruluk test | — | HUD, konsol |
| E-10 | — | — | — | M6, M7, konsol |
| E-11 | — | — | D-21 | Veri hattı, konsol |
| E-12 | — | RAD olaylarıyla uydurma | SEP önseli | M3, E-04 |
| E-13 | — | — | D-22 | Tümü (parametrik) |
| E-14 | — | — | Yasak/ceza bölgeleri | M6 |

---

## 16. Kaynaklar

**Challenge ve görev mimarisi**

- NASA, *Mars Surface Power Decision* (ACR 2024): https://www.nasa.gov/wp-content/uploads/2024/12/acr24-mars-surface-power-decision.pdf
- NASA SUITS FY26 görev tanımı: https://www.nasa.gov/wp-content/uploads/2025/09/fy26-suits-mission-description.pdf
- SUITS TSS-2025: https://github.com/SUITS-Techteam/TSS-2025
- NASA Mars Relay Network (2026 güncel): https://science.nasa.gov/mars/mars-relay-network/
- NASA, *NASA Says Farewell to MAVEN* (3 Haziran 2026): https://www.nasa.gov/news-release/nasa-says-farewell-to-maven-mars-mission-hosts-media-call-today/

**Saha ve bilim (boxwork)**

- NASA, *Curiosity starts unpacking boxwork formations*: https://www.nasa.gov/missions/mars-science-laboratory/curiosity-rover/nasas-curiosity-mars-rover-starts-unpacking-boxwork-formations/
- NASA, *Curiosity Sees Martian 'Spiderwebs' Up Close* (Şubat 2026): https://www.nasa.gov/missions/mars-science-laboratory/curiosity-rover/nasas-curiosity-rover-sees-martian-spiderwebs-up-close/
- Curiosity Blog, Sols 4804–4811 (kampanya fazları): https://science.nasa.gov/blog/curiosity-blog-sols-4804-4811-kicking-off-the-final-phase-of-boxwork-exploration/
- Curiosity Blog, Sols 4845–4851 (boxwork'ten ayrılış): https://science.nasa.gov/blog/curiosity-blog-sols-4845-4851-bye-bye-boxwork-bye-bye/
- Siebach ve ark., *Overview of Curiosity's Exploration of the Boxwork Unit* (LPSC 2026): https://hal.science/hal-05494691

**Veri**

- Calef & Parker (2016), MSL Gale Merged Orthophoto Mosaic 25 cm: https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_orthophoto_mosaic_25cm
- Parker & Calef (2016), MSL Gale Merged DEM 1 m: https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m
- HiRISE DTM, Gale sülfat birimi: https://hirise.lpl.arizona.edu/dtm/ESP_012907_1745
- Kirk ve ark. (2008), HiRISE stereo topografyası, JGR: https://doi.org/10.1029/2007JE003000
- NASA Ames MCMC GCM çıktıları: https://www.nasa.gov/space-science-and-astrobiology-at-ames/division-overview/planetary-systems-branch-overview-stt/mars-climate-modeling-center-mcmc/mcmc-gcm-output/
- AmesCAP: https://github.com/NASA-Planetary-Science/AmesCAP
- DONKI: https://ccmc.gsfc.nasa.gov/tools/DONKI/
- Cesium Mars: https://cesium.com/platform/cesium-ion/content/cesium-mars/
- Cesium for Unreal, Ay ve Mars eğitimi: https://cesium.com/learn/unreal/unreal-moon-mars/
- Cesium, Eylül 2025 sürümleri (CesiumJS 1.133 `Ellipsoid.MARS`, Cesium for Unreal 2.19.1): https://cesium.com/blog/2025/09/02/cesium-releases-in-september-2025/

**Radyasyon ve uzay havası**

- NASA, *NASA Watches Mars Light Up During Epic Solar Storm* (8.100 µGy, X12): https://www.nasa.gov/solar-system/planets/mars/nasa-watches-mars-light-up-during-epic-solar-storm/
- ESA, *Solar Orbiter shows the Sun raging on* (uzak yüzdeki X12 patlaması): https://www.esa.int/Science_Exploration/Space_Science/Solar_Orbiter/Can_t_stop_won_t_stop_Solar_Orbiter_shows_the_Sun_raging_on
- Wimmer-Schweingruber ve ark. (2015), zenit açısı bağımlılığı, GRL: https://doi.org/10.1002/2015gl066664
- Ehresmann ve ark. (2021), RAD ile doğal korunak ölçümü, JGR Planets: https://doi.org/10.1029/2021je006851
- Guo ve ark. (2026), Mars topografyasının RAD dozuna etkisi, JGR Planets: https://elib.dlr.de/224554/1/ME-SBA-2026-Guo...Matth%C3%A4_Berger_Reitz%20Influence%20of%20Mars%20Topography%20on%20Radiation%20Dose%20Detected%20by%20the%20Mars%20Science%20Laboratory_JGR%20Planets.pdf
- Hassler ve ark. (2014), *Mars' surface radiation environment measured with MSL's Curiosity rover*, Science 343.
- Zeitlin ve ark. (2013), *Measurements of energetic particle radiation in transit to Mars on MSL*, Science 340.
- Khaksarighiri ve ark. (2025), *Radiation Transport Through the Martian Atmosphere as a Function of the Zenith Angle*, JGR Planets: https://doi.org/10.1029/2025je009352
- Löwe ve ark. (2025), *Nowcasting Solar Energetic Particle Events for Mars Missions*, Space Weather: https://arxiv.org/abs/2502.02469
- Charpentier ve ark. (2025), *Influence of Mars Topography on Neutral Surface Radiation: Modeling and MSL/RAD Observations* (ön baskı): https://doi.org/10.22541/essoar.175337668.89983018/v1
- Khaksarighiri ve ark. (EGU 2026), *Requirements for SEP Forecasting at Mars: Lessons from the 9 October 2024 CME-Driven Shock*: https://doi.org/10.5194/egusphere-egu26-10464
- Aran ve ark. (2007), *Modeling and forecasting SEP events at Mars: the event on 6 March 1989*, A&A: https://doi.org/10.1051/0004-6361:20077233

**İnsan performansı**

- Norcross ve ark., *Feasibility of Performing a Suited 10-km Ambulation on the Moon (EWT)*, NASA TP-2009-214796: https://www.lpi.usra.edu/lunar/artemis/NorcrossEtAl_NASA-TP-2009-214796_EVA%20Walkback%20Test.pdf
- Norcross ve ark., *Metabolic Costs and Biomechanics of Level Ambulation in a Planetary Suit (IST-1)*, NASA TP-2010-216115: https://www.lpi.usra.edu/lunar/artemis/NorcrossEtAl_NASA-TP-2010-216115_PlanetarySuitMetabolicCosts.pdf
- Norcross ve ark., IST serisi sonuçları: https://ntrs.nasa.gov/citations/20090007828 · IST-2: https://ntrs.nasa.gov/citations/20110003409
- Pandolf, Givoni & Goldman (1977), yük taşımada metabolik enerji tahmini, J Appl Physiol.
- Minetti ve ark. (2002), aşırı eğimlerde yürüme ve koşmanın enerji maliyeti, J Appl Physiol.
- Tobler (1993), yürüyüş hızı fonksiyonu.
- Soule & Goldman (1972), arazi katsayıları.
- Kluis ve ark. (2025), *Characterization of the effects of sex, speed, and incline on metabolic rate during partial gravity ambulation*, J Appl Physiol: https://doi.org/10.1152/japplphysiol.00627.2024

**Arazi ve robotik**

- MTTT, Mars 2020 iniş yeri geçilebilirlik analizi: https://robotics.jpl.nasa.gov/media/documents/Data-driven%20surface%20traversability%20analysis%20for%20Mars%202020%20landing%20site%20selection.pdf
- SPOC: https://nasa-jpl.github.io/SPOC/
- DUST (NASA JSC): https://ntrs.nasa.gov/citations/20220009846
- Space ROS demoları: https://github.com/space-ros/demos/
- rmw_zenoh, ROS 2 Kilted sürüm notları: https://github.com/ros2/ros2_documentation/blob/kilted/source/Releases/Release-Kilted-Kaiju.rst
- Golombek & Rapp (1997), Mars'ta kaya boyut-frekans dağılımları, JGR.
- Golombek ve ark. (2008), Phoenix iniş yeri kaya dağılımları, JGR.
- Huertas ve ark. (2006), HiRISE'ta otomatik kaya tespiti.
- Chiodini ve ark. (2017), ufuk çizgisiyle rover lokalizasyonu: https://doi.org/10.1109/metroaerospace.2017.7999600

**Planlama ve optimizasyon**

- Koenig & Likhachev (2002), D\* Lite, AAAI.
- Rockafellar & Uryasev (2000), CVaR optimizasyonu, J. Risk.
- Calafiore & Campi (2006), senaryo yaklaşımı, IEEE TAC.
- Vansteenwegen, Souffriau & Van Oudheusden (2011), orienteering problemi derlemesi, EJOR.
- Krause & Guestrin (2005), bilgi değerinin submodülerliği.
- Chekuri & Pál (2005), submodüler orienteering için özyinelemeli açgözlü algoritma.
- Hakimi (1964), graflarda merkez ve medyan problemleri.
- Ratliff, Bagnell & Zinkevich (2006), Maximum Margin Planning.
- Dozier & Frew (1990), DEM'den hızlı ufuk hesabı.
- Allison & McEwen (2000), Mars saati algoritması.

**Formal yöntemler**

- Pérez ve ark. (2022), *Monitoring ROS2: from Requirements to Autonomous Robots*: https://arxiv.org/abs/2209.14030
- NASA Ogma: https://github.com/nasa/ogma/
- Space ROS dokümantasyonunda Ogma: https://space-ros.github.io/docs/rolling/Related-Projects/Ogma.html
- Giannakopoulou ve ark., FRET ve FRETish (NASA Ames).

**İletişim**

- RFC 9171, Bundle Protocol v7: https://www.rfc-editor.org/rfc/rfc9171
- RFC 5326, Licklider Transmission Protocol: https://www.rfc-editor.org/rfc/rfc5326
- ION-DTN: https://github.com/nasa-jpl/ION-DTN/
- HDTN: https://github.com/nasa/HDTN
- Lim ve ark. (2019), BASALT analog programı, Astrobiology.

**NASA hedefleri ve mimari**

- Moon to Mars Objectives (Eylül 2022): https://www.nasa.gov/wp-content/uploads/2022/09/m2m-objectives-exec-summary.pdf
- Moon to Mars Mimari Tanım Belgesi: https://ntrs.nasa.gov/citations/20240015571
- Mars Surface Power (fisyon kararı özeti): https://www.nasa.gov/wp-content/uploads/2025/02/iparch07-wp-mars-surface-power.pdf

**Eklentiler**

- *E-01:*
  - NASA Ingenuity: https://science.nasa.gov/mission/mars-2020-perseverance/ingenuity-mars-helicopter/
  - Grip ve ark. (2025), *The Chopper Next-Generation Mars Rotorcraft*, IEEE Aerospace: https://doi.org/10.1109/aero63441.2025.11068461
  - Chopper aerodinamik yükseltmeleri: https://ntrs.nasa.gov/api/citations/20250004293/downloads/Critical_Aerodynamic_final_v4.pdf
  - PX4 Zenoh (rmw_zenoh): https://docs.px4.io/main/en/middleware/zenoh
- *E-02:*
  - JAXA RACS2 köprüsü: https://github.com/jaxa/racs2_bridge
  - RACS2 yörünge gösterimi (Int-Ball2): https://www.kenkai.jaxa.jp/research/automation/racs2.html
  - Ogma (`ros`, `fprime`, cFS): https://github.com/nasa/ogma
  - ros2_fprime_bridge: https://github.com/lulav/ros2_fprime_bridge
- *E-03:*
  - MSL Navcam RDR veri seti: https://pds.nasa.gov/ds-view/pds/viewProfile.jsp?dsid=MSL-M-NAVCAM-5-RDR-V2.0
  - Vona (2025), Landform Contextual Mesh: https://arxiv.org/abs/2509.18330
  - Ames Stereo Pipeline MSL örneği: https://stereopipeline.readthedocs.io/en/latest/examples/msl.html
  - Cesium 3D Gaussian splat duyurusu: https://cesium.com/blog/2026/04/27/3d-gaussian-splats-lod/
  - Cesium for Unreal değişiklik kaydı: https://cesium.com/learn/cesium-unreal/ref-doc/changes.html
- *E-05:* Halbwachs ve ark. (1991), Lustre; Champion ve ark. (2016), *The Kind 2 Model Checker*, CAV.
- *E-06:*
  - Angelopoulos & Bates (2021), *A Gentle Introduction to Conformal Prediction*: https://arxiv.org/abs/2107.07511
  - Ono & Williams (2008), *Iterative Risk Allocation*, IEEE CDC.
- *E-08:*
  - Cunningham, Nesnas & Whittaker (2017), *Improving Slip Prediction on Mars Using Thermal Inertia Measurements*, RSS: https://doi.org/10.15607/rss.2017.xiii.038
  - Arvidson (2016), *Crossing Martian Megaripple Fields*, LPSC: https://www-robotics.jpl.nasa.gov/media/documents/lpsc_2016_arvidson_ripple_crossing.pdf
- *E-11:*
  - NASA Earth Observatory, *Jez like Mars*: https://science.nasa.gov/earth/earth-observatory/jez-like-mars-147041/
  - *What a Lake in Turkey Can Tell Us about Mars*: https://science.nasa.gov/blogs/earth-matters/2021/02/17/what-a-lake-in-turkey-can-tell-us-about-mars/

---

*Bu belge H0'dan önce yalnızca fikir ve plan içerir. Eklentiler dahil hiçbir parça için kod, mesaj dosyası veya sahaya özel veri işleme yok. 13 Kasım'da Resources sekmesine göre, H0'da da gerçek veriyle güncellenecek.*
