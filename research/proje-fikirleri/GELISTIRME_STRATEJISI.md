# REDLINE — Derinleştirme stratejisi ve araştırma kararları

13 Kasım 2026 · Araştırma/tasarım raporu · Uygulanmış yeni sistem iddiası içermez.

**En güçlü yön, eksik bilgi altında bir Mars bilim seferini insan, rover ve hava aracı arasında planlamak; toplanan kanıtın kararı nasıl değiştirdiğini Unreal içinde göstermek ve ölçmektir.** Öncelik üç çekirdekte: görev için bilgi değeri, bilimsel örnekleme kalitesi ve kararların açıklanabilir sonucu. Beş ana görev bunların uygulama alanlarıdır.

Bu rapor yeni özellikleri önceki listeye eklemekten çok hangi parçayı neden derinleştireceğimizi belirler. Genel ürün [PROJE_TANIMI.md](PROJE_TANIMI.md), görevler [BES_ANA_GOREV_VE_MIMARI.md](BES_ANA_GOREV_VE_MIMARI.md), habitat ve hikâye [TASARIM_GOZDEN_GECIRME.md](TASARIM_GOZDEN_GECIRME.md) içinde bulunur.

## Önce özgünlük iddiasını doğru kurmak

Astronot + rover + drone + jeoloji görevi tek başına özgün bir birleşim değildir. NASA CHAPEA; simüle yürüyüş, habitatta jeoloji, rover/drone ile keşif ve numune görevlerini birlikte tarif ediyor. BASALT da Mars benzeri gecikme ve bant genişliğinde bilim kararlarını araştırdı. REDLINE bu çalışmalardan yararlanabilir, ancak onların tamamını yeniden icat ettiğini söylememelidir. [NASA CHAPEA](https://www.nasa.gov/missions/analog-field-testing/chapea/yearlong-mars-analog-crew-to-conduct-simulated-traverses-robotics-operations/), [BASALT karar araştırması](https://ntrs.nasa.gov/citations/20190026720).

| Önceki çalışma | Bize verdiği referans | REDLINE için ayrı araştırma sorusu |
|---|---|---|
| CHAPEA | İnsan yürüyüşü, habitat ve robotik keşif birlikte anlamlı | Yeni robot gözlemi insanın hangi hedefi seçebileceğini nasıl değiştiriyor? |
| BASALT | Bilim ekibi–saha ekibi arasında bilgi ve karar akışı | Eksik/eski/çelişkili veriyle karar neden değişti; kullanıcı bunu fark etti mi? |
| JPL'nin rover AEGIS sistemi | Bilim ekibinin önceliklerine göre görüntüden hedef seçimi | Hangi gözlemi hangi araç yapmalı; insan görevindeki faydası ne? |
| JPL NeBula | Belirsiz ortamda farklı robotlarla algı ve planlama | Sınırları tanımlı Marswalk görevinde bu yaklaşım nasıl değerlendirilebilir? |
| NASA'nın EVA planlama AEGIS aracı | Bilim amaçlarını harita, faaliyet ve sefer planına bağlama | Planı gözlemle güncelleyip insanın simülasyonda yürütmesi nasıl birleşir? |

JPL'nin **Autonomous Exploration for Gathering Increased Science** sistemi ile `nasa/aegis` deposundaki **Application for Exploration Geospatial Integration and Scheduling** aynı yazılım değildir. İkincisi Ay EVA planlama aracıdır; Mars'a hazır ROS eklentisi gibi sunulmaz. Kaynaklar mimari/iş akışı referansıdır; lisans, sürüm ve bağımlılık incelemesi olmadan ana projeye alınmaz. [JPL AEGIS](https://superintelligence.jpl.nasa.gov/public/projects/aegis/), [NeBula](https://www-robotics.jpl.nasa.gov/how-we-do-it/systems/nebula-autonomy-suite/), [NASA EVA AEGIS](https://github.com/nasa/aegis).

Savunulabilir katkı adayı: **NASA katmanlarından başlayan, farklı robotların gözlemlerini veri kökeni ve belirsizlikleriyle birleştiren, keşfi insanın bilim kararına göre seçen ve sonucu etkileşimli görev provasında karşılaştıran bir sistem.** Bunun yeni bir araştırma katkısı olduğu deneyle gösterilmeli; dünyada ilk veya NASA'nın kullanıma hazır çözümü olduğu iddia edilmez.

## 1. Keşfin değerini görev kararından hesaplamak

Bir robot bütün boş harita hücrelerini doldurmak zorunda değildir. Bilim hedefine erişimi, doğru örnek seçimini veya dönüş kararını etkileyen boşluk önce gelir. Fark şu örnekte görünür: drone geniş ama görev dışı bir alanı haritalarsa çok veri üretir; geçitteki dar bir noktaya bakması insanın ikinci bilim durağına gidip gidemeyeceğini değiştirebilir.

Görev yöneticisinin seçenekleri yalnız sürüş hedefleri olmaz: drone gözlemi, rover yakın incelemesi, kol uç kamerasıyla yeni açı, cihaz kalibrasyonu, kontrol örneği, insandan yorum veya eldeki kanıtla devam. Her seçenek süre/enerji/sarf ve görev bağımlılıklarını taşır.

İlk algoritma, aday gözlemler üzerinde kısa ufuklu bir karar hesabı olabilir:

`gözlemin değeri = gözlem sonrası beklenen en iyi görev sonucu − mevcut bilgiyle en iyi görev sonucu − gözlem maliyeti`

Bu bir tasarım tanımıdır. Başarı olasılığı veya gözlem etkisi kendiliğinden bilinmez; görüş modeli, algı başarımı, konum hatası ve cihaz kalitesiyle tahmin edilmelidir. İlk prototipte açık senaryo modelleri kullanılır; model geliştirme ve kalibrasyon senaryoları son değerlendirme senaryolarından ayrılır. Son değerlendirme sonucuna göre parametre ayarlanırsa o veri artık bağımsız test sayılmaz. Algı skoru doğrudan güvenilir olasılık kabul edilmez.

Fiziksel sınırlar ve geçersiz cihaz koşulları önce uygulanır. Yüksek bilim puanının bir mekanik sınırı satın alması veya bilim değeriyle insan hayatını keyfî ağırlıkta takas etmesi önlenir. Zaman, enerji ve bilim çıktısı mümkünse ayrı gösterilir; birleşik puan kullanılırsa ağırlıkların sonucu ne kadar değiştirdiği incelenir.

### Küçük sayısal kontrol

Yöntemin davranışını görmek için tamamen uydurulmuş bir dolambaç maliyeti örneği hesaplandı. Kısa yol açıkken maliyet 10, kapalıyken geri dönme/yeniden planlamayla 50, uzun yol 20 birimdir. Kamera gözlemi 2, daha doğru yerel inceleme 4 birimdir. Sensör duyarlılık/seçicilikleri de yalnız bu örnek için verilmiştir. Bu bir insan güvenliği modeli, Mars ölçümü veya ROS başarım testi değildir.

| Kısa yolun kapalı olmasına ilişkin örnek ön bilgi | Yeni gözlem yok | Drone kamera gözlemi | Rover yakın inceleme | En düşük beklenen maliyet |
|---|---:|---:|---:|---|
| 0,05 | 12,000 | 13,675 | 14,720 | Yeni gözlem yok |
| 0,25 | 20,000 | 16,375 | 16,800 | Drone |
| 0,50 | 20,000 | 19,750 | 19,400 | Rover |
| 0,80 | 20,000 | 22,000 | 22,520 | Yeni gözlem yok; uzun yol |

Hesap Bayes güncellemesi ve her gözlemden sonra yeniden rota seçimiyle yapıldı. Sonuç, daha doğru sensörün veya daha çok keşfin her durumda daha iyi olmadığını gösterir; gerçek sistem için avantaj kanıtlamaz. Varsayımlar ve tüm sonuçlar [örnek hesap kaydında](../notes/karar_degeri_ornek_hesap.json) bulunur.

Geliştirme çizgisi: maliyetli aday seçimi → gözlem sonrası yeniden planlama → senaryo örneklemesiyle belirsizlik hesabı → gerekirse daha uzun ufuklu görev politikası. Tam bir POMDP çözümünü başlangıç bağımlılığı yapmak gerekmez. Araçlar arasında iş paylaşımı için önce yetenek/enerji/erişim filtresi ve küçük aday kümesi; iş sayısı büyüyünce çizelgeleme optimizasyonu değerlendirilebilir.

## 2. Bilimi bir örnek sayacından araştırma sürecine taşımak

Bilim zinciri `soru → alternatif açıklamalar → gerekli gözlem → örnekleme → cihaz işlemi → kalite → yorum → sonraki karar` olmalı. Kullanıcı her sayıyı toplamak yerine hangi ölçümün sorusunu cevaplayacağını seçer. Fazladan aynı tür numune, farklı bir soruyu cevaplayan uygun numuneden daha az yararlı olabilir.

Bilim amaçlarını bir izlenebilirlik tablosuyla görev ve veriye bağlayalım:

| Bilim amacı | Gereken kanıt | İş | Tamamlanma kaydı |
|---|---|---|---|
| Numunenin yerel yüzeyi temsil etmesini değerlendirmek | Yüzey fotoğrafı, konum, tane boyu/tekstür ve alım yöntemi | Keşif + yakın fotoğraf + seçilmiş alım | Numune bağlamı ve sınırlamaları |
| İki örneğin uygun analizini karşılaştırmak | Aynı cihaz/prosedürle geçerli ölçüm, hazırlık ve kalite bilgisi | Laboratuvar | Birim/prosedür uyumlu karşılaştırma ve alternatif açıklama |
| Sondaj yerinin gerekçesini kurmak | Görüntü/jeoloji bağlamı, hedefe erişim, gerekli cihaz | Hedef inceleme + sondaj | Hedef seçimi ve örnek derinliği |

Yeni derinleştirmeler: kontrol/tanık kabı, uç takımın önceki örnek geçmişi, hazırlık adımı, ölçüm süresi, kalibrasyon durumu ve tekrar ölçüm. Bunlar kesin kontaminasyon yüzdeleri uydurmak için kullanılmaz; doğrulanmış model yoksa prosedür/kalite durumu olarak izlenir.

İlk bilim çıktısı iki açık yolla üretilebilir: gerçek kaydın kendi hedef/konum/zamanıyla açıldığı arşiv görevi; veya kaynaklı bir örnek profilinin yalnız senaryo örneğine referans olduğu simülasyon görevi. İkincisinde hedefin yeni gerçek Mars ölçümü olduğu söylenmez. Yanlış hazırlık ilk aşamada sonucu geçersiz/kullanılamaz yapabilir; gerçek spektrumu veya pH değerini uydurma bir çarpanla değiştirmez. Sayısal karışım, kontaminasyon veya cihaz hatası üretilecekse bu ayrı bir ölçüm modelidir ve bağımsız doğrulama ister. Planlayıcı, senaryo örneğinin saklı referans sonucunu okuyamaz.

### Somut bilim kampanyası A: Bagnold/Namib–Gobabeb

Önerilen soru, tane boyu ve örnek hazırlığının regolit karşılaştırmasını nasıl etkilediğidir. Curiosity'nin gerçek kampanyası görüntü, tane özellikleri, kimya, mineral ve çevre gözlemlerini birleştirdi. Gerçek çalışma, robotun gözlediği yüzey ile laboratuvara verdiği örneğin ilişkisini öğretmek için güçlü bir temel sağlar. [NASA kampanya özeti](https://science.nasa.gov/blog/recap-of-the-bagnold-dune-investigation/), [NASA arşivindeki bilim çalışması](https://ntrs.nasa.gov/api/citations/20170001747/downloads/20170001747.pdf).

Akış: yörüngeden bağlam → drone ile yüzey şekli ve erişim gözlemi → rover yakın görüntüsü → tanımlı yerlerden kontrollü regolit örnekleri → uygun fraksiyon/cihaz işlemi → sonuçların karşılaştırılması. Kullanıcı farkın yüzey biriminden mi, tane boyu/örnek seçiminden mi veya ölçüm kalitesinden mi kaynaklanabileceğini değerlendirir. Drone görüntüsünden element bileşimi çıkarıldığı iddia edilmez.

Bu kampanya, çok tür örnekleme ve keşif kararını doğal biçimde birleştirdiği için öncelikli adaydır. Sondaj burada zorunlu değildir; yalnız beş görevi doldurmak için kumula kaya karotu görevi yerleştirilmez. Uygun kaya hedefi doğrulanırsa aynı seferde ek bilim işi olabilir; aksi durumda sondaj ayrı bir kampanya profili olur.

### Somut bilim kampanyası B: Yellowknife Bay/Sheepbed

Önerilen soru, iki yakın sondaj örneğinin benzerlik/farklılıklarını hangi bağlam ve cihaz verileriyle yorumlayabileceğimizdir. John Klein ve Cumberland **aynı Sheepbed birimindedir**; birbirinden yaklaşık 2,75 m uzaktadır. Bunları iki ayrı jeolojik birim diye tanımlamayız. Yakın iki örnek üzerinden temsil gücü, görüntü bağlamı ve XRD yorumunu çalışabiliriz. [NASA hedef haritası](https://science.nasa.gov/resource/cumberland-selected-as-curiositys-second-drilling-target/), [NASA bilim özeti](https://ntrs.nasa.gov/api/citations/20140016825/downloads/20140016825.pdf).

Akış: bilim sorusu → görüntü/hedef bağlamı → erişim ve duruş → uygun örnek hazırlığı → CheMin arşiv karşılaştırması → bulguyla uyumlu ve uyumsuz açıklamalar. Bu, güncel Gale pH haritası veya yaşam bulundu iddiası üretmez. Gerçek arşiv sonucu eğitim örneğidir; simüle yeni deliğin gerçek NASA ölçümü olmaz.

### Saha seçiminin kapısı

Mevcut 2 × 2 km Gale arazisinde, önceki PLACES sorgusundaki iki tabloda rover konum örneği bulunmadı. Bu, arazide hiçbir görüntü olmadığı anlamına gelmez. Yine de gerçek bilim durağı kanıtlanmadan görev hedefleri oraya sabitlenmez. [Yerel sorgu kaydı](../notes/Gale_PLACES_AOI_KONTROLU.md).

Önce bir kampanyadan sınırlı sayıda gerçek hedef/sol ve ürün ID'si seçilir. Görüntü/ölçüm konumu ve baktığı alan doğrulanır; sonra bu noktaları kapsayan DEM/ortho ürünü seçilir. Raster örtüşmesi, no-data, çözünürlük, koordinat ve ürün sürümü kontrol edildikten sonra habitat ve senaryo nesneleri yerleştirilir. Bugünkü Gale arazisi bağlantı/performans deneyi olarak kullanılmaya devam edebilir. Yeni kampanya sahası henüz üretilmedi.

## 3. Astronot ve rover için aynı geçiş haritasını kullanmamak

Roverın geçebildiği alan insan için otomatik uygun değildir; insanın aşabildiği bir basamak da robot için uygun olmayabilir. Geometri ortak olabilir; maliyet ve kısıtlar araç/yük/görev profiline göre ayrılır. Yerel kamera görüşü, eğim, yüzey pürüzü, yük ve dönüş koşulları farklı amaçlara hizmet eder.

İnsan hareketi önce açık bir senaryo modeli olarak tanımlanır. Oksijen, yorgunluk veya takım elbise hareket sınırı için doğrulanmış model yoksa gerçek astronot fizyolojisi gibi sunulmaz. Sonuçlar birkaç makul parametre profili altında karşılaştırılır. Aynı öneri küçük parametre değişiminde tersine dönüyorsa arayüz bunu kırılgan karar olarak göstermelidir.

Keşif robotunun yardımı şu eylemlerle ölçülebilir: rota öncesi inceleme, ekipman/örnek taşıma, tanımlı mesafede refakat, insanın erişmek istemediği hedefi gözleme, veri eksikliği için yeni açı ve bağlantı desteği. Yardım, robotun sürekli insanın yanında bulunmasıyla eşitlenmez.

## 4. Haritayı veri kökeni ve geçerlilik modeliyle derinleştirmek

Her nesne/hücreye tek bir güven sayısı koymak yetersizdir. En azından uzamsal belirsizlik, ölçüm kalitesi, veri yaşı, çözünürlük, kaynağın türü ve gözlem kapsamı ayrılır. Kaynaklar çelişiyorsa neden birleştirilmediği veya hangi varsayımla kullanıldığı görünür.

Eski olan her veri geçersiz değildir. Jeoloji katmanının yıllar önce ölçülmüş olması, bir gaz sensörünün birkaç saniyelik gecikmesiyle aynı kurala tabi tutulmaz. Geçerlilik sınıfları tanımlanır: görece kararlı topoğrafya/jeoloji, zamana bağlı çevre, hareketli nesne/altyapı durumu ve işlem/kalibrasyon geçerliliği. Süre eşikleri bu sınıfa ve senaryoya göre seçilir.

Bir drone görüntüsü ve ondan türetilmiş nokta bulutu iki bağımsız kanıt gibi sayılmaz. Türetilmiş ürünlerin girdi bağlantıları korunur. Aynı kamera gözleminden üretilen iki sonuç birleştirilirken korelasyon yok sayılıp sahte kesinlik oluşturulmaz. Yörünge DEM'ini sık örneklemek yeni ayak/tekerlek ölçeği bilgisi üretmez.

Görev merkezinde yeni bir **“Bu karara ne dayanıyor?”** paneli olsun. Planın kaynakları, eksik girdileri, elenen alternatifleri ve yeni bir gözlemin neyi değiştirebileceği burada görünür. Açıklama kayıtlı veri ve hesap sonucundan üretilir; sonradan uydurulmuş bir metin değildir.

## 5. Görev motoru, fizik ve hikâyenin sorumlulukları

Görev motoru, durum ve önkoşullardan kullanılabilir işleri çıkarır. ROS action sonuçlarıyla işi ilerletir; hareket, algı ve temas sonuçlarını uydurmaz. Dünya/fizik modeli durumu üretir, tahmin katmanı gözlemleri yorumlar, kullanıcı arayüzü bu bilginin erişilebilir bölümünü sunar. Hikâye bu değişimleri anlamlı biçimde anlatır.

Üç yeni kullanıcı eylemi ekleyelim: önerinin varsayımını inceleme, alternatif için bilgi toplama isteği ve mevcut görevi başka bilim işiyle değiştirme. Hata sonrasında yalnız yeniden başlatma yerine düzeltme, erteleme, örneği saklama veya alternatif cihaz seçme yolları bulunur.

Sınavın hedefi gizli doğru cevabı buldurmak değildir. Kullanıcının karar anında erişebildiği veriye göre uygun akıl yürütmesi, işlemi doğrulaması ve gerektiğinde durdurması değerlendirilir. Sonucu şans eseri iyi olan zayıf karar ile iyi gerekçeli ama belirsizlik nedeniyle kötü sonuçlanan karar ayrı raporlanabilir; değerlendirme kuralı görev öncesinde tanımlanır.

## 6. Mevcut rover kodundan alınabilecekler ve açık eksikler

13 Kasım salt okunur incelemesinde, `C:\Users\USER\Desktop\roversim27` çalışma ağacı değiştirilmedi. Kod varlığı bütün Mars sisteminde çalıştığı anlamına gelmez; bu incelemede yeni ROS testleri çalıştırılmadı.

| Yerel parça | Yeniden kullanım adayı | Derinleştirme ihtiyacı |
|---|---|---|
| `rover_navigation/src/terrain_mapper_node.cpp` | LiDAR'dan yerel arazi ve diagnostics, hesap/yayın bütçesi | Mars sahası, çok araç hizalama, gözlem kökeni ve insan geçiş modeli |
| `rover_navigation/src/active_perception.cpp` | Erişilebilir aday gözlemi bilgi/maliyet ile sıralama | `expected_covariance_reduction` girdisini üreten gözlem modeli; görev değerine bağlama |
| `rover_navigation/src/active_perception_node.cpp` | Yerelleştirme belirsizliğinde durma ve yardım akışı | İncelenen düğümde görüş seçicisi çağrısı yok; hipotez üretici ve gözlem eylemi ayrı iş |
| `rover_world_model/src/terrain_layers.cpp` | Geometri, semantik, kayma ve belirsizlik maliyetlerini ayırma | Maliyetleri kalibre başarısızlık olasılığı sanmama; kaynak/korelasyon/çok çözünürlük |
| `rover_health` | Sağlık/komut bütünlüğü ve durdurma temeli | Her araç için yetki, sensör tazeliği ve görev sonlandırma sözleşmesi |
| `rover_interfaces/msg/DecisionRecord.msg` | Karar, aday, ret gerekçesi ve kanıt referansı | Model sürümü, karar anındaki bilgi ve görev durumuyla kalıcı ilişki |

Bir ek teknik bulgu: aktif algı düğümü x/y konum kovaryansıyla yaw kovaryansını ham maksimumda topluyor. Metrekare ve radyankare aynı birim değildir; tek eşik kullanılacaksa ölçekleme/normalizasyon veya ayrı konum/yön ölçütleri tasarlanmalıdır. Bu, araştırma sırasında saptanan yeniden kullanım riski; burada kod düzeltmesi yapılmadı.

## 7. Bütün sistemi tutacak arayüzler

| Kayıt | Asgari sorumluluk |
|---|---|
| `EvidenceRecord` | Kaynak ürün/sensör, gözlem zamanı, alım zamanı, yer/çerçeve, çözünürlük, kalite, veri profili ve türetildiği girdiler |
| `TaskSpec` | Bilim amacı, önkoşul, gerekli yetenek/cihaz, tahmini maliyet, tamamlanma kanıtı, iptal ve geri dönüş davranışı |
| `TaskOutcome` | Gerçekleşen iş/ölçüm, hata, kaynak değişimi, örnek/kap ve durum güncellemesi |
| `DecisionRecord` | Erişilebilir kanıt, adaylar, seçilen eylem, elenen gerekçeler, varsayımlar ve model sürümü |
| `RunManifest` | Saha/varlık/ürün sürümleri, koordinat/orijin, zaman modeli, senaryo tohumu, yazılım ve başlangıç durumu |

Bunlar önerilen sözleşmelerdir; ROS mesajları henüz bu raporla uygulanmış olmaz. Habitat ekranı, tablet, RViz, Open MCT ve son rapor aynı olay/ölçüm kayıtlarını kullanmalıdır. Aktif komut sahibinin değişmesi, action iptali, sıfır komut ve stale komut reddi bütün araçlar için ayrı ama ortak kurallı yönetilir.

Hedef mimaride tek dünya manifestinden Unreal görünümü ile Gazebo collision/sensör karşılığı üretilecek; bu üretim hattı henüz kurulmadı. Fizik ve görüntü farklı sahalara kayarsa doğru algoritma bile yanlış görünür. TF, metre–santimetre, eksen dönüşümü, kamera kalibrasyonu ve simülasyon zamanı ilk entegrasyon kapısıdır. Kamera akışı ile üzerindeki algı işaretleri aynı ölçüm anına bağlanır.

Numune alma ve vana çevirme gibi fiziksel işlemler için komut kimliği, onay ve sonuç durumu tutulur. Bağlantı kesilip sonucu belirsiz kalan bir komut otomatik tekrar yürütülmez; önce gerçek/model durumuyla uzlaştırılır. Aynı mesajın tekrar gelmesi ikinci numune alımı veya ikinci vana turu üretmemelidir. Görev düzenleyicisinin ilk sürümü şeması denetlenen dosya olabilir; bilim amacı, yer, cihaz prosedürü, önkoşul ve değerlendirme kuralını bağlar. İleride Unreal öğretmen panelinden düzenlenebilir.

## 8. Ekleme öncelikleri

| Öncelik | Yeni yetenek | Neden derinlik getiriyor? |
|---|---|---|
| 1 | Görev için bilgi değeri ve robot işi seçimi | Keşfin hangi insan kararını iyileştirdiğini hesaplar |
| 1 | Bilim amacı–örnek–cihaz–sonuç izlenebilirliği | Toplanan veriyi bir araştırma sorusuna bağlar |
| 1 | Kanıt ve karar paneli | Kullanıcı sistemin ne bildiğini ve neden önerdiğini görebilir |
| 2 | Zaman/enerji/sarf bütçesine duyarlılık ve dönüş seçenekleri | Önerinin hangi varsayımda değiştiğini gösterir |
| 2 | Kontrol örneği/kalite ve görevi kurtarma | Prosedür hatalarını ve yeniden bilim yapmayı öğretir |
| 2 | Bilim ekibi için görev/senaryo düzenleme | Yeni bilim amacı ve cihaz prosedürünü aynı motorla çalıştırır |
| 2 | Görüntüyle vana kimliği/poz ve müdahale doğrulaması | Algıdan fiziksel sonuca kadar bütün zinciri sınar |
| 3 | Drone rölesi ve yerelleştirme desteği | Yeni görev atama maliyetleri ve gözlemler üretir |
| 3 | Gerçek kamera/işaret/robot arayüzüyle sınırlı donanım deneyi | Simülasyon dışındaki algı/komut aktarımını sınar |

Geniş kapsam korunabilir; ancak her modül aynı deney altyapısında bir soruyu cevaplamalıdır. Çok oyuncu/VR, her cihazın tüm fiziği, ileri zemin deformasyonu, hareketli rovera iniş ve büyük serbest dil asistanı ana çekirdeğin önkoşulu yapılmamalı. İleride ayrı profiller olabilir. Birden fazla uçuş/fizik yığını aynı aracın hareketine eşzamanlı otorite olmamalıdır.

## 9. Kullanılacak mühendislik araçları

ROS 2/Nav2/MoveIt görev ve hareket tarafını; Gazebo fizik/sensörü; Unreal etkileşimi; Python bilim ve analiz modellerini; GDAL/QGIS veri hazırlığını; Open MCT operasyon telemetrisini; rosbag2/PlotJuggler kayıt incelemesini üstlenir. Yeni araç her katmana yeni bir iş yükü de getirir; yalnız tanınan bir isim olması entegrasyon gerekçesi değildir.

JPL NeBula hazır Jazzy/Windows UE paketi diye varsayılmaz; yöntem referansıdır. NASA EVA AEGIS'ten bilim izlenebilirliği ve istasyon/faaliyet modeli incelenebilir; Ay koordinat altyapısı doğrudan Mars'a taşınmaz. MATLAB/Simulink veya başka bir çok cisim/akış yazılımı ancak belirli kontrolcü, temas veya gaz modeli için karşılaştırma ihtiyacında eklenir. Çıktısı ortak veri sözleşmesine bağlanır; ayrı bir güzel demo olarak bırakılmaz.

## 10. Deneyler ürünü savunulabilir yapacak

| Soru | Karşılaştırma | Ölçüm |
|---|---|---|
| Keşfi göreve göre seçmek işe yarıyor mu? | Yeni keşif yok; en yakın bilinmeyen alan; görev odaklı keşif | Tamamlanan bilim, keşif süresi/enerji, gereksiz gözlem, hedef kabul/ret |
| Drone hangi koşulda değerli? | Rover; drone + rover; drone kullanmama seçeneği | Fayda/maliyet, bilgi kalitesi, görev kararındaki değişim |
| Belirsizlik paneli işe yarıyor mu? | Aynı veri ve farklı açıklama görünümü | Veriyi bulma, eski/çelişkili bilgiyi fark etme, yanlış karar ve müdahale |
| Algıdan vana müdahalesi çalışıyor mu? | İşaretli/etiketsiz profil; farklı yerleşim/ışık/örtülme | Yanlış vana, poz hatası, temas hatası, doğrulanmış kapanış |
| Bilim prosedürü gerçekten etkili mi? | Geçerli hazırlık; hatalı kayıt/kap/kalibrasyon | Hatanın fark edilmesi, tekrar örnekleme, yorumun kanıt kalitesi |
| Sistem kopmayı yönetiyor mu? | Akış gecikmesi, paket kaybı, duraklatma, saat sıçraması | Eski komut uygulanması, durumun eşitlenmesi, veri yaşı ve duruş |

Sensör bütçesi, başlangıç bilgisi ve kaynak varsayımları adil tutulur; farklı politikalara fazladan gerçek bilgi verilmez. Görsel/algı modelinin eğitim sahası ile değerlendirme yerleşimleri ayrılır. Gözlemin dünya gerçeğine doğrudan erişimi olan oracle yalnız iyimser değerlendirme üst sınırı olabilir; ana yöntem sayılmaz.

İlk robot deneyleri birden fazla kayıtlı senaryoyla yapılır; sonuç dağılımları ve başarısız örnekler gösterilir. İnsan arayüzü değerlendirmesinde küçük ekip içi deneme önce kullanılabilirlik bulgusu üretir; sertifikalı astronot performansına veya güçlü istatistiksel genellemeye çevrilmez. Aynı sahayı öğrenme etkisi için sıra ve eşdeğer varyantlar tasarlanır.

İlk deneyde bilim çıktısı, önceden tanımlı hedef–işlem çiftlerinden geçerli kayıtla tamamlananların sayısıdır; duplike örnekler kendiliğinden yeni bilim hedefi sayılmaz. Numune kayıt tamlığı ve geçerli işlem oranı ayrı verilir. Keşfin gereksizliği yalnız planın değişmemesiyle tanımlanmaz: gözlem öncesinde tanımlı bir bilgi/karar ihtiyacına cevap verip vermediği incelenir. Metrik ve kabul kuralları son testten önce sabitlenir. İlk görev seçimi önce geçersiz seçenekleri eler, ardından bilim hedefi kapsamını koruyarak zaman/robot enerji maliyetini karşılaştırır; birim dönüşümü tanımlanmadan tek birleşik fayda puanı üretilmez.

Replay ile alternatif karar deneyi ayrılır. Kayıt tekrar oynatma yalnız geçmişi gösterir; alternatif eylemin sonucu için başlangıç durumundan fizik/görev modeli yeniden çalıştırılır. Parametre ve sürüm kaydı olmadan sonuçlar karşılaştırılmaz. Kaynak modeli ağırlıkları değişince strateji kazananı değişiyorsa bu bulgu raporlanır.

## 11. Ekip işleri ve birleşme kapıları

| Çalışma kolu | Teslim edeceği somut parça | Bağımlılık |
|---|---|---|
| Veri ve bilim | Kaynaklı kampanya/ürün kataloğu, saha ve bilim izlenebilirliği | Nihai görev hedefleri için önce |
| Dünya ve Unreal | Ortak saha, habitat ekranları, astronot etkileşimi | Manifest ve veri/komut sözleşmesi |
| Rover otonomisi | Haritalama, yerelleştirme, rota, mod/sağlık yönetimi | TF/zaman/sensör doğrulaması |
| Drone | Tanımlı kalkış/gözlem/dönüş ve ortak harita gözlemi | Fizik varsayımı, hizalama ve kaynak modeli |
| Kol ve cihazlar | Numune/drill/vana için hareket ve sonuç doğrulaması | Yetenek ve temas arayüzü |
| Görev ve kayıt | Önkoşul/sonuç, bilgi değeri, karar kaydı ve telemetri | Ortak kayıtlar; diğer kollarla erken stub |
| Deney ve eğitim | Senaryo varyantları, gizli durum ayrımı, metrik ve debrief | İlk günden ortak kayıt |

Bunlar kişi sayısı zorunluluğu değildir; ekip üyeleri birkaç kolu üstlenebilir. Aynı dosyalarda serbestçe yarışmak yerine sözleşme ve küçük çalışır sahne üzerinden birleşilir.

Birleşme kapıları: (1) aynı araç/saha/zaman, (2) Unreal habitatından manuel/otonom görev, (3) gözlemle harita ve karar değişimi, (4) bilim işleminin geçerli sonuç üretmesi, (5) kararın sonraki işi değiştirmesi, (6) aynı koşuyu raporlama ve alternatif deney. Büyük sistem bu kapılardan geçerek derinleşir; kapsamın büyük olması her modülün aynı anda hazır olmasını gerektirmez.

## 12. Etkinlikte çalışabilirliği tasarımın parçası yapmak

Hedef çalışma düzeninde tam ROS/Gazebo/Unreal sistemi geliştirme makinesinde birlikte çalışacak; bugün bu entegrasyon henüz yok. Uzak erişim gösteriminde yerel kontrol döngüsü evdeki makinede kalacak, ağ üzerinden görüntü/komut taşınacak. Ağ kopması simülasyondaki robot komutunu süresiz yaşatmamalı. Temel NASA ürünleri, senaryolar ve araç varlıkları önceden sürümlü yerel paket hâlinde tutulacak; canlı internet API'si görev mantığının önkoşulu olmayacak.

Zayıf laptop için ayrı bir kayıt inceleme profili hazırlanabilir: önceden kaydedilmiş görev, kamera/harita/olay eşitlemesi ve etkileşimli debrief. Bu profil canlı ROS/Gazebo simülasyonu diye sunulmaz. Tam canlı deney, yerel kayıt inceleme ve kısa video birbirini tamamlar; her birinin yaptığı açık olur.

## Karar önerisi

Bir sonraki mühendislik kararı **tek bilim kampanyası ve veri örtüşmesi**, ardından ortak kayıt sözleşmesidir. En yüksek araştırma önceliği, mevcut aday seçiciye gerçekten gözlem etkisini hesaplayan model eklemek ve onun insanın bilim hedefini değiştirip değiştirmediğini ölçmektir. Unreal kontrol merkezi bu karar döngüsünü kullanıcının deneyebildiği yer olacak. Yeni sensor/araçlar bu döngüye katkı sağladıkça eklenir.

İlk teslimin sınırı: seçilmiş bir kampanyada iki aday hedef, kararı etkileyebilen bir eksik gözlem ve Unreal merkezinde kayıtlı bir karar değişikliği. Veri kolu hedeflerin örtüşmesini doğrularken entegrasyon kolu mevcut Gale deneme sahasında koordinat/zaman köprüsünü doğrulayabilir. Bu iki iş nihai bilim sahasına geçişte birleşir; biri diğerinin tamamlandığı izlenimini vermez.
