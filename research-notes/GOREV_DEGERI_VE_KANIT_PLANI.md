# REDLINE — Görevlerin değeri ve kanıt planı

14 Kasım 2026 · Tasarım kararı · Ana tanım: [Proje kılavuzu](../PROJE_KILAVUZU.md)

**Geliştirme kararı:** Büyük mühendislik kapsamı korunacak; ilk birleşik gösterim, aynı bilim alanına farklı yollardan erişen astronot ve roverın gerekçeli bir örnekleme işi yapması olacak. Keşif, örnek, analiz ve sonraki plan aynı kampanya kaydından ilerleyecek. Sondaj ve istasyon onarımı uygun görev profillerinde bu akışı genişletecek.

Bu dosya görev tasarımını ve sınama yöntemini tanımlar. Yeni ROS–Unreal köprüsü, cihaz modeli, drone veya görev uygulaması bu çalışma sırasında geliştirilmedi. Araştırma/tasarımın gücüyle çalışan ürünün başarısı ayrı değerlendirilmelidir.

## 1. Fikrin kuvveti ve çekincenin nedeni

İhtiyaç somut: yörünge haritası, yer görüntüsü, robotun güncel gözlemi ve numune analizi farklı ölçek ve zamanlarda gelir. Bir insan bilim yürüyüşünde erişim, yapılacak iş ve dönüş koşullarını bunlarla birlikte yönetmek gerekir. Unreal insanın görüşünü ve sahadaki işlemlerini deneyimletir; ROS robot işini yürütür. Bu iş bölümü amaçla uyumludur.

Henüz üstünlüğü gösterilmemiş üç nokta vardır:

| Açık | Neden önemli? | Tasarımdaki karşılığı |
|---|---|---|
| Bilinen bileşenlerin birleşimi ayırt edici bir sonuca dönüşmeyebilir | ROS, drone, kol ve güzel Mars sahnesi tek başına ürün katkısını açıklamaz | Bir hedefin kaynak, erişim, işlem, sonuç ve sonraki işinin aynı haritadan yönetilmesi |
| Beş görev ayrı teknik gösterilere dönüşebilir | Kullanıcı neden bu işleri yaptığını ve önceki kararının etkisini kaybedebilir | Ortak kampanya durumu; her görevden sonraki işe taşınan somut çıktı |
| Astronot robotların onay düğmesine dönüşebilir | İnsan ölçeğinde simülasyonun gerekçesi zayıflar | Sahada bağlam fotoğrafı/notu, örnek sınırı, farklı insan/rover erişimi ve bilim önceliği kararı |

Robotlar challenge dışı değildir. Her ölçümün rotayı değiştirmesi gerekmez. Büyük kapsam da tek başına kusur değildir. Yeni özelliğin hangi problemi çözdüğü ve bedeli açıklanabilmelidir. “Bütün NASA verilerini toplamak” yerine seçilen sahada görevle ilişkili, kaynağı açık veri birleşimi hedeflenir.

Robot destekli Marswalk ve jeoloji simülasyonu için önceki çalışmalar vardır; [NASA CHAPEA açıklaması](https://www.nasa.gov/missions/analog-field-testing/chapea/yearlong-mars-analog-crew-to-conduct-simulated-traverses-robotics-operations/) sanal yürüyüş, saha kaydı, örnek analizi ve robot kullanımını birlikte tarif eder. REDLINE'ın değeri bu kategorileri ilk defa icat ettiği iddiasına dayanmaz. Ayırt edici katkı adayı, seçilen saha için kaynaklı harita ile insan–robot erişim ve bilim işlerini birlikte kullanabilmektir; bunun yararı aşağıdaki deneylerle sınanacak.

## 2. Beş görev nasıl derinleşiyor?

| Görev | Kullanıcının zor kararı | Gerekli kanıt | Toparlanma ve kalıcı sonuç |
|---|---|---|---|
| **1 — Geçiş ve buluşma** | Yeni gözlem mi, daha iyi gözlenmiş yol mu; insan ve rover nerede buluşacak? | Görülen geometri, kalan örtülme, profil kısıtları, poz ve model süre/enerji | Bekleme maliyeti, ortak yeni nokta veya teslim iptali; teslim edilmeyen ekipman kullanılamaz |
| **2 — Numune çifti** | Hangi karşılaştırma soruya yeter; tekrar hazırlık mı, yeniden örnek mi? | Astronot bağlam kaydı, köken, kap, prosedür, kalite ve analiz | Kalan malzeme varsa yeniden hazırlık; yoksa alım veya sınırlı rapor |
| **3 — Sondaj** | Ek derinlik örneği gerekli mi; hangi hedefte ve ne zaman durmalı? | Hedef gerekçesi, erişim/temas, bit/kap durumu ve model ilerleme/yük | Yeniden konumla, hedef değiştir veya dur; örnek ve donanım sonuçları ayrı |
| **4 — Bilim kapasitesi** | Onarıma zaman ayırmak mı, örneği koruyup analizi ertelemek mi? | Servis şeması, vana kimliği/pozu, basınç/akış, cihaz ve saklama durumu | Doğrulanmış izolasyon, alternatif cihaz veya kayıtlı erteleme |
| **5 — Birleşik yürüyüş** | Birincil işten sonra ikinci bilim işi yapılabilir mi? | Gerçekleşen süre/enerji, kanıt eksiği, kalan örnek/kap ve bağımsız dönüş planları | Ek iş, yakın alternatif veya dönüş; analizden sonra sonraki gezi/iş |

Görevlerin zorluğu farklıdır: bilgi eksikliği, karşılaştırılabilirlik, mekanik işlem, kapasite yönetimi ve sefer planı. Beşinde de aynı “batarya azaldı, dön” olayını tekrarlamak derinlik sağlamaz. Bir koşuda hiç arıza olmaması geçerli bir varyanttır.

## 3. İlk birleşik görev kartı

**Ad:** İki rota, bir bilim yürüyüşü.

**Ana ürün amacı:** NASA kaynaklı konum/rota bağlamını yeni robot gözlemleriyle birleştirerek astronotun erişimini, bilim durağını ve dönüşünü planlamak. Aşağıdaki analiz, bu yürüyüşte yapılan somut bilim işidir. Başarı iki simüle sayının farklı çıkmasına değil, kaynaklı planla ulaşılan ve kökeni/işlemi doğrulanan örneklerle açıklanabilir bir sefer yürütmeye dayanır.

**Bilim sorusu:** İnce yüzey örtüsü ve yakındaki daha iri taneli senaryo malzemesinden alınan iki örneğin, aynı hazırlık ve sıcaklık profilindeki sulu ekstrakt iletkenlikleri ayırt edilebilir mi? Birincil değişken µS/cm cinsinden iletkenlik; pH ayrı tamamlayıcı analizdir. Malzeme/ölçüm profilleri simülasyona aittir ve henüz uygulanmadı. Bu iki sınıfın gerçek mikro-sahada bulunduğu doğrulanmadan NASA hedefi olarak sunulmaz.

**Bilim sonucu:** Geçerli ölçümlerin tanımlı model aralıkları ayrılıyorsa bu örnekler/prosedür için ayırt edilebilir fark; örtüşüyorsa mevcut ölçümle ayırt edilemeyen sonuç; kimlik/hazırlık/kalibrasyon geçersizse yorumlanamaz işlem. Örtüşme eşitliği kanıtlamaz. Açık ölçüm/tekrar modeli ayrıca geliştirilecek; fiziksel kimya ve istatistiksel test doğrulanmış sayılmaz. İki örnek bütün yüzleği temsil etmiş olmaz; iletkenlik tek başına iyon türünü veya jeolojik kökeni belirlemez. Bu çalışma yaşam bulgusu veya bölgesel pH haritası vaat etmez.

**Saha:** Yellowknife Bay/Sheepbed öncelikli araştırma alanı. John Klein/Cumberland ve ilgili APXS/CheMin kayıtları tarihsel referanstır. İki deliğin yaklaşık 2,75 m yakınlığı yaklaşım yürüyüşü değildir. Yaklaşım koridorları, kesin hedefler ve mikro-hizalama henüz doğrulanmamıştır; mevcut 2×2 km Gale sahası mühendislik denemesi olarak kalır. Ayrıntı: [saha ve bilim istasyonu](SAHA_VE_BILIM_ISTASYONU.md).

**Sahne:** H01 harita masası → H02 hazırlık → S02 yaklaşım alternatifleri → S01/S03 hedef bölgesi ve buluşma → H05 kabul/analiz. Habitat, iki yerel koridor, buluşma işareti ve yeni örnek nesneleri gelecekteki görev için konsept/senaryo varlığıdır. NASA arşivindeki kesin konumlarla karıştırılmaz.

**Başlangıç bilgisi:** Kullanıcı yörünge bağlamını, mevcut yer gözlemlerini, gerçek arşiv analizlerini, araç profillerini ve gözlenmemiş alanları açabilir. Bilinen NASA sonucu kullanıcıdan saklanıp yeni bilim keşfi gibi ödül yapılmaz. Senaryo dünyasının küçük engel ve malzeme profilleri yalnız izin verilen sensör/işlem yoluyla öğrenilir.

| Gerçek kaynak/ürün | Görevdeki somut rol | Açık sınır |
|---|---|---|
| MRO HiRISE `PSP_010573_1755_RED` | Yaklaşım/hedef bölgesinin yörünge bağlamı; görülen ayrıntı ve yerel gözlem ihtiyacı | Metadata düzeyinde aday örtüşme; piksel/no-data ve DEM hizalaması tamamlanmadı |
| MSL APXS `Wernecke_Brushed` / `CumberlandNew_RP` | Tarihsel hedef, hazırlık ve element gözlemlerini konumlu kaynak kartında inceleme | Yeni örneğin kimyası veya kesin delik pozu değil |
| MSL CheMin John Klein / Cumberland ürünleri | Aynı Sheepbed bağlamındaki tarihsel mineral sonuçları ve analiz sınırları | Yeni iletkenlik/pH ölçümü yerine geçmez |
| Phoenix WCL | Numune hazırlığı ve ıslak kimya cihazı için ayrı saha/zaman referansı | Gale'de ölçülmüş pH katmanı değil |

Bu tablo görevdeki veri rolünü tanımlar; gerçek hizalamanın yerini tutmaz. Bilim sahasındaki ilk gösterim kapısı, en az bir yaklaşım/hedef bölgesinin ilgili MRO/MSL kayıtlarıyla aynı koordinat bağlamında açılabilmesidir. Ürün/etiket bağlantıları [saha notundadır](SAHA_VE_BILIM_ISTASYONU.md).

**Karar ve işlem sırası:**

1. **Bilgi açığını seç.** Kullanıcı iki yaklaşımın hangisinde hangi bilginin eksik olduğunu görür. C01/C02 etiketleri tasarım kimliğidir; onaylanmış gerçek Mars yol adları değildir.
2. **Gözlemi görevlendir.** Drone uygun açıdan görünür alanı gözler; rover yakın ölçü/zemin görüntüsü alır. Drone uçuşu görünmeyen yüzeyi veya zemin taşıma kapasitesini kendiliğinden ölçmez. Uçuş/sürüş maliyeti ayrı kaydedilir.
3. **İnsan ve rover planını ayır.** Geometri ve profiller elveriyorsa insan dar yaklaşımı, rover daha geniş dolaşımı kullanabilir. Buluşma için ekipman, varış aralığı ve poz belirsizliği görünürdür. Gecikmede bütçe içinde bekleme, karşılıklı erişilebilir yeni nokta veya teslimi iptal edip eldeki ekipmanla iş değişikliği seçilir. Bekleme kaynak harcar; yeni nokta/zaman iki tarafın kabulüyle etkinleşir. İnsan rotası rover rotasından kopyalanmaz.
4. **Astronot sahada kanıt üretsin.** Genel bağlam, yakın görüntü, yüzey örtüsü/doku notu ve alım sınırı kaydedilir. Roverın erişemediği bir gözlem noktası insan için de uygun değilse hedef reddedilir. Uygun insan alım profili geliştirilmediyse manuel alım var sayılmaz.
5. **Örneği doğrula.** Seçilen araç alımı yapar; kap ve köken kaydı oluşur. Gripper kapanması tek başına başarı değildir. Yeterli malzeme, geçerli kap ve teslim durumu kontrol edilir. Ağ onayı fiziksel teslim değildir; örnek/kap/ekipman sahipliği doğrulanmış devirden sonra değişir.
6. **İkinci işi yeniden değerlendir.** Ek örnek/kontrol/yakın inceleme veya dönüş seçilir. Tek bir toplam puan yerine bilim ihtiyacı, gerçekleşen süre, kalan araç kaynakları ve dönüş koşulları görünürdür.
7. **Dönüşleri ve analizi tamamla.** Astronot, rover ve kullanılan droneun sonucu ayrı kaydedilir. H05'te örnek kabul/hazırlık/ölçümden geçer. Gale pH sonucu açıkça simüle analizdir; Phoenix WCL ayrı yer/zaman referansıdır.
8. **Sonraki işi üret.** Geçersiz hazırlık tekrar işlem; yetersiz malzeme yeni alım; geçerli ama yetersiz karşılaştırma ek bağlam/örnek; yeterli sınırlı kayıt rapor seçeneği doğurabilir. Bu işler haritadaki kökene ve gerekli cihaza bağlanır.

**Bitiş:** Başlangıç planı → erişilebilir kanıt → karar → yapılan iş → doğrulanmış sonuç aynı merkezde açılır. Geçerli örnek sayısı, insan/robot dönüşleri ve ertelenen işler ayrı görünür. Gerekçeli iptal kalite/işlem açısından doğru olabilir; elde edilmeyen bilim işi tamamlanmış sayılmaz.

## 4. Sistemi dürüstçe zorlayacak varyantlar

Bu tablo dünya/sensör tasarımını tanımlar; henüz çalıştırılmış deney veya önceden hesaplanmış sonuç değildir. Geçiş, maliyet ve işlem sonuçları sahne/modelden türetilmelidir.

| Varyant | Değişen koşul | Beklenen karar problemi | Kontrol edilecek kusur |
|---|---|---|---|
| A — Açık ve yeterli | İlgili koridor önceden yeterince gözlenmiş | Ek keşfin bedeline değer mi? | Droneu her koşulda zorunlu tutma |
| B — Örtülü geçit | Yörünge/yer görüşünde küçük bir alan belirsiz | Hangi gözlem karar için yeterli? | Tek üstten görüntüyü her tür fiziksel güvence sayma |
| C — Ayrı erişim | İnsan ve rover profilleri aynı geometride farklı erişim verir | Ayrı yol ve buluşma mı, ortak alternatif mi? | Rover geçişini insan geçişine kopyalama |
| D — Ölçüm kalitesi | Görünüşçe uygun örneğin hazırlığı geçersiz veya karşılaştırma eksik | Tekrar hazırlık, tekrar alım veya sınırlı yorum mu? | Her yeni sayıyı geçerli bilim sonucu sayma |
| E — Destek kapasitesi | Seçili analiz modülü servis nedeniyle kapalı | Onarım mı, alternatif analiz/saklama mı? | Vana animasyonunu cihazın hazır olduğu kanıtı sayma |

Varyantlar bağımsız açılabilir. İlk canlı gösterim B/C ile bir örnek zincirini kullanabilir; D/E ayrı koşuda derinleştirilir. Kritik veri eksiği varsa sistem karar için yetersizliği açıkça gösterebilir. Bütün belirsizlikleri uydurma tek bir güven yüzdesine çevirmek gerekmez.

## 5. Faydayı üç ayrı soruyla ölç

**Önce veri bütünleştirmesi:** Aynı NASA ve sensör kayıtları, aynı görev ve aynı araç yetenekleri iki arayüzde sunulur. Birinde görüntü, harita ve örnek kayıtları ayrı açılır; diğerinde aynı hedef üzerinden bağlantılıdır. Kaynak/kalite bilgisi iki koşulda da erişilebilirdir. Değişen unsur birlikte kullanma biçimidir. Kaynak arama süresi, yanlış hedef/örnek eşleştirmesi, eksik kayıt ve görev tamamlama incelenir. Zayıf ve bilgisi eksiltilmiş bir baseline kurulmaz.

**Sonra keşif seçimi:** Aynı başlangıç dünyası, bütçe, sensör yetenekleri ve yerel durma/engel denetimleriyle yeni keşif istememe, en yakın bilgi eksiğini gözleme ve görev için gerekli eksiği gözleme stratejileri karşılaştırılır. Seçilen gözlemler farklı olacağı için yöntemlerin gördüğü bilgi de farklılaşabilir; bu fark ve maliyeti raporlanır. Keşifsiz strateji engelde körlemesine ilerlemeye zorlanmaz; durabilir veya alternatif seçebilir. Kolay varyantta ilave keşif daha kötü çıkabilmelidir.

**Sonra otonom yardım:** Aynı iş için manuel/uzaktan yönetim ve otonom yürütme karşılaştırılır. Görev, başlangıç bilgisi ve model bütçesi eşleştirilir. Veri bütünleştirme ve otonominin etkisi tek deneyde birbirine karıştırılmaz.

| Ayrı raporlanacak sonuç | Tanım |
|---|---|
| Geçerli bilim işi | Önceden tanımlanan soru/hedef–işlem çiftinin uygun kayıt ve prosedürle tamamlanması; duplikeler yeni hedef sayılmaz |
| Kayıt kalitesi | Köken, bağlam, kap, hazırlık, cihaz ve kaynak bağlantılarının tamlığı; temsil gücü ayrıca değerlendirilir |
| İnsan işi | Aktif kontrol/arama süresi, müdahale sayısı ve sahada üretilen bağlam kayıtları |
| Gözlem maliyeti | Drone/rover süresi ve model enerjisi; kapsam ve çözülmeyen eksikler |
| Plan ve dönüş | İnsan ve her araç için model kısıtı ihlalleri, dönüş sonucu, kalan kaynak ve varsayımlar |
| Toparlanma | Hatanın fark edilmesi, doğrulanmış düzeltme, korunmuş örnek ve ertelenen iş |

Başarı yalnız hız değildir; bilim kalitesini düşürerek hızlanan koşu üstün sayılmaz. Gerçek astronot/giysi modeli yokken “insan güvenliği yüzde X arttı” sonucu çıkarılmaz. Küçük ekip denemesi kullanılabilirlik bulgusu üretir. Senaryo sırası ve eşdeğer varyantlar öğrenme etkisini azaltacak biçimde planlanır; test varyantları üzerinde parametre ayarlanmaz. Yeni karşılaştırma koşusu başlangıç manifestinden yeniden çalıştırılır; rosbag tekrarı alternatif fiziksel eylemin sonucunu üretmez.

## 6. İlk geliştirme işleri ve bitiş ölçütleri

| Sıra | Somut teslim | Kabul |
|---|---|---|
| 1 | Tekil ürün/koordinat QA'sı ve hedef manifesti | Tarihsel hedef, yeni senaryo hedefi, analiz yeri ve numune kökeni ayrılmış; raster/no-data ve hizalama kontrol edilmiş |
| 2 | Mevcut deneme sahasında ROS–Unreal bağlantısı | Aynı metre/eksen/zaman, robot pozu ve hedef komutu; kesintide eski komut düşüyor |
| 3 | İnsan proxy'si, iki erişim profili ve buluşma | Robot insanın güncel/tahmini durumunu tanımlı arayüzden görüyor; farklı rotalar ve teslim doğrulanıyor |
| 4 | Bir yerel gözlem → harita → kullanıcı kararı | Gözlem yalnız izinli sensörden geliyor; kaynak kartı ve değişen/korunan plan kayıtlı |
| 5 | Bir örnek → kap → kabul → analiz → köken noktası | Alım/teslim doğrulanıyor; simüle sonuç ve arşiv referansı ayrılmış |
| 6 | İkinci iş ve debrief | Gerçekleşen süre/örnek/cihaz durumu seçenekleri değiştiriyor; tüm araçların sonucu görünür |
| 7 | Drone, sondaj ve servis profilleri | Her biri aynı kayıtlara katılıyor; uçuş, temas ve cihaz kabulü ayrıca karşılanıyor |
| 8 | Eşleştirilmiş karşılaştırma ve çevrimdışı gösterim | Varsayımlar, başarısız koşular, kaynaklar ve ölçümler erişilebilir |

Veri QA'sı ile köprü deneyi paralel ilerleyebilir; bilimsel hedefli koşu doğrulanmış manifestte birleşir. İlk bağlantı deneyi gerçek bilim sonucunu kanıtlamaz. İlk uçtan uca örnek zinciri de bütün beş görevin tamamlandığı anlamına gelmez.

İlk güçlü ürün kanıtı, bir robot gözleminden insanın planına, oradan doğrulanmış örnek/analize ve sonraki bilim işine uzanan zinciri canlı açabilmektir. Karşılaştırma fayda göstermiyorsa daha fazla efekt veya araç eklemek yerine karar ekranı, iş paylaşımı ve görev modeli düzeltilir.

## 7. Challenge ve kaynak sınırları

Seçilen challenge belirli Mars konumu/rotası için katmanlı, çoklu görev verisiyle insanın bilim yürüyüşünü desteklemeyi ister. Bu görev akışı o amaç için tasarlanmıştır. Challenge metninin erişilebilir [organizatör kopyası](https://hackathlone.com/challenges/interplanetary-survival-guide-martian-map) ile [resmî sayfası](https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/) ana referanslardır; resmî kayıt/kaynak ve yerel etkinlik koşulları son kontrolde doğrulanır. Ödül, eğitim sertifikası veya NASA tarafından kullanım sözü verilmez.

Bilim ürünleri ve pH sınırları [saha notunda](SAHA_VE_BILIM_ISTASYONU.md), mühendislik sözleşmeleri ve varlık/teslim koşulları [ana kılavuzda](../PROJE_KILAVUZU.md), edinme kaynakları [katalogda](../KAYNAK_VE_VARLIK_KATALOGU.md) tutulur. Farklılık halinde sürüm 3 görev tanımı ve açık uygulama durumu esas alınır.
