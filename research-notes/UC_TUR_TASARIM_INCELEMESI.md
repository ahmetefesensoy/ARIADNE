# REDLINE — Üç tur eleştiri ve revizyon kaydı

13 Kasım 2026 · Araştırma ve tasarım · Uygulama kodu değiştirilmedi.

Bu kayıt, proje kılavuzu birleştirilmeden önceki üç inceleme döngüsünü izler. Bulgular mevcut araştırma belgeleri, yerel varlık/kod incelemeleri ve bağlantısı verilen kaynaklarla değerlendirilir. “Kontrol” sütunu çoğunlukla tasarım kabul koşuludur; henüz çalıştırılmamış sistem testi anlamına gelmez.

## Tur 1 — Space Apps amacı, özgünlük ve kaynaklar

İncelenen başlangıç: beş görevli Marswalk tasarımı ve görev merkezine yeni asistan isteği.

| Bulgu | Revizyon kararı | Kontrol |
|---|---|---|
| Rover, drone ve bakım görevleri insan bilim yürüyüşünü gölgeleyebilir | Her görev için astronotun hangi kararına yardım edildiği ve NASA katmanının rolü yazılacak | Görevin teknik gösteriminden önce insan ihtiyacı ve veri bağı tanımlı |
| Astronot–rover–drone birleşimi özgünlük için yeterli değil | Katkı iddiası görev için bilgi değeri, kanıt takibi ve yanılabilen asistanla karar değerlendirmesine daraltıldı | CHAPEA/BASALT önceki çalışma olarak gösterilecek |
| Ay/Mars sözcükleri karışıyor | Seçilen challenge ve ilk saha Mars; Ay ayrı gelecek profili | Mars verisi Ay'a yerleştirilmeyecek; rotorcraft Ay ortamında varsayılmayacak |
| Başlangıç öncesi araştırma ile yarışma çözümü karışabilir | Mevcut kod/varlık ve bu kılavuz hazırlık olarak kaydedilecek; etkinlik üretimi ayrı izlenecek | Önceden var olan çalışma, etkinlikte üretilmiş gibi sunulmayacak |
| NASA sitesinde bulunan her model sınırsız yeniden dağıtılabilir sanılabilir | Her varlığın üretici, kredi ve kullanım kaydı ayrı tutulacak | Üçüncü taraf kredisi/izin durumu eksik varlık otomatik onaylı sayılmayacak |
| Ücretsiz Fab içeriği açık çözüm malzemesiyle karışabilir | Dağıtım için özgün/CC0/uygun açık içerik önce; kısıtlı paketler koşullu alternatif | Varlık lisansı ile Space Apps çözüm malzemesi şartı birlikte değerlendirilecek |
| Jarvis benzeri asistan projenin ana amacı hâline gelebilir | Asistan harita/veri/görev kararını açıklayan araç olacak; gezegen veya robot gerçeğine gizli erişmeyecek | Asistan kapalıyken de temel Marswalk planı ve robot görevleri çalışabilecek |

Dayanaklar: [challenge'ın organizatör kopyası](https://hackathlone.com/challenges/interplanetary-survival-guide-martian-map), [CHAPEA](https://www.nasa.gov/missions/analog-field-testing/chapea/yearlong-mars-analog-crew-to-conduct-simulated-traverses-robotics-operations/), [BASALT](https://ntrs.nasa.gov/citations/20190026720), [GO Team başlangıç/kaynak açıklaması](https://github.com/nasa/spaceapps/discussions/1827), [2026 katılımcı koşulları](https://www.spaceappschallenge.org/legal/).

Bu tur sonunda ürün yönü: NASA katmanlı haritası üzerinde insan bilim yürüyüşü; otonom robot yardımı ve asistan eleştirisi bunun karar deneyidir. Resmî challenge sayfası ve legal sayfasının doğrudan açılışı 502 verdi; legal'in 7 Ağustos 2026 güncel metni resmî alan adının arama indeksinde okunabildi. Takımın kayıt hesabı veya etkinliğin özel yönergeleri incelenmedi.

## Tur 2 — Bilim, otonomi ve yanılabilen asistan

Bu tur ilk revizyonu temel alır: bilim yürüyüşü ana amaç, robotlar ve asistan karar araçlarıdır.

| Bulgu | İkinci revizyon | Kontrol |
|---|---|---|
| Asistanın rastgele yanılması sınavı tekrarlanamaz yapar | Normal danışman ile kayıtlı hata reçeteli eğitim/sınav profili ayrıldı | Hata türü ve kullanılan kanıt sürümü öğretmen kaydında; normal profilde enjeksiyon yok |
| Kaynak gösteren her yanıt doğru sanılabilir | Öneri kartında olgu, çıkarım, varsayım, kapsam ve karşı kanıt ayrı | Kaynak iddiayı/konumu/zamanı destekliyor mu kullanıcı inceleyebilir |
| Asistanın büyük resmi bilmemesi keyfî yazılabilir | Yerel araç amacı, veri kapsamı ve görev sürümü açık modeldir | Ret gerekçesi veya yeni gözlem isteği planı gerçekten değiştirebilir |
| Dil modeli fiziksel robot komutuna karışabilir | Danışman yalnız yüksek seviyeli teklif üretir; task manager güncel koşulları denetler | Sınav hatası kontrol limitlerini, komut sahibini veya sensor watchdog'unu devre dışı bırakmaz |
| NASA sonuçları farklı örneklerde uydurma sayılara dönüşebilir | Arşiv tekrarı, referans profilli senaryo ve sayısal cihaz modeli ayrıldı | Gerçek kayıt yeri/zamanı değiştirilmez; bilinmeyen saha kimyası gerçek ölçüm gibi gösterilmez |
| Beş görev tek sahaya bilimsel gerekçe olmadan sıkıştırılabilir | Ortak eğitim motoru ve kampanya profilleri; uygun veri yoksa farklı saha/alternatif hedef | Bagnold kumuna sırf görev sayısı için kaya karotu konmaz; sondaj kampanyası ayrıca doğrulanır |
| Çok araç haritası otomatik kusursuz hizalanmış varsayılabilir | Ortak haritaya ölçüm zamanındaki tahmini poz ve belirsizlikle bağlanma | TF, eksen/birim, clock, kaynak korelasyonu ve gizli gerçek ayrımı kabul kapısı |
| Kolun hareketi işlem başarısı sayılabilir | Numune/sondaj/vana için temas ve ölçümsel sonuç ayrı | Kapta doğru nesne, kayıtlı derinlik veya doğrulanmış hat değişimi gerekir |

Sonuç: asistanın rolü kanıtı tartışmaya açmak; astronotun rolü bilim hedefi ve görev bütününü yönetmek. Bilgi eksikliği/öneri hatası yalnız tavsiye katmanındadır. Dünya gerçeği, sensör gözlemi ve tahmini bilgi üç ayrı düzeydir. Ölçüm hatasını, cihaz kalitesini veya algı skorunu kalibre olasılık gibi sunmama kararı korundu.

## Tur 3 — Kullanıcı deneyimi, varlık üretimi ve sınanabilirlik

Bu tur ikinci revizyondaki görev/kanıt/asistan modelini astronotun yaşayacağı mekânlara, varlık üretimine ve deneylere uygular.

| Bulgu | Üçüncü revizyon | Kontrol |
|---|---|---|
| Ayrı tarayıcı ve RViz görüntüsü ürünün kontrol merkezi yerine geçebilir | Habitat, garaj, laboratuvar ve saha tabletinin bütün görev kararlarını Unreal içinde sunması şart | Beş görevde temel kararlar dış pencereye geçmeden verilebilir |
| Ekranlar dolu ama bilgiye erişim zor olabilir | Ortak ölçüm/örnek/konum seçimi; odak 2B görünüm, altyazı ve birim/yaş/kalite | Kullanıcı bir grafikten ilgili numuneye ve haritaya ulaşır |
| Her kaya gerçek saha nesnesi gibi görünebilir | Arşiv geometri/doku, senaryo engeli, dekor ve örnek hedefi ayrı varlık rolleri | Navigasyonu etkileyen nesne iki simülasyonda aynı; örneklenebilirlik açık |
| NASA modeli hazır rig/fizik demek sanılabilir | Görsel mesh, eklemler/rig, collision, inertial ve sensör ayrı üretim işleri | Bilinen boyutla ölçek, eklem/pivot ve Gazebo karşılığı kontrol edilir |
| Ücretsiz kısıtlı varlıklar public teslimi zorlaştırabilir | Açık/özgün varlık paketi ana dağıtım yolu; Fab/Quixel yalnız koşullu alternatif | Kaynak/lisans/credit ve dağıtım hakkı kaydı; engine lisansı ayrı bağımlılık |
| Çok kamera/ekran ve uzaktan kullanım akıcılığı bozabilir | Paylaşılan görüntü dokusu, görünürlük/rate bütçesi; kontrol döngüsü UI'dan bağımsız | Kare süresi, sim RTF, sensör gecikmesi ve komut yanıtı ayrı ölçülür |
| Sınav yalnız asistana inanmamayı ödüllendirebilir | Doğru öneri kabulü ve gereksiz ret de değerlendirilir | Asistansız/normal/hata profili karşılaştırması, karar anındaki kanıtla puanlama |
| Kapsam büyük ama ekip birleşmesi belirsiz | Modül teslimleri ve ortak kayıtlar; kampanya seçimi ile köprü deneyi paralel | Saha/koordinat → görev → gözlem → karar → fiziksel sonuç → debrief zinciri |
| İnternet gidince gösterim durabilir | Yerel veri ve kurallı asistan; canlı, kayıtlı inceleme ve kısa video ayrı profiller | Ağsız kayıt inceleme gerçek zamanlı robot deneyi diye sunulmaz |

Üçüncü tur sonunda nihai kılavuzun gereksinimi: her görev için mekân/varlık, insan kararı, robot akışı, bilim verisi, asistanın yararı/hatası, değişen sonuç, teknik sorumlu ve kabul ölçütü birlikte yazılacak. Asistanla yeni robot görseli karıştırılmayacak; aynı yazılım kimliği habitat/tablet/rover arayüzlerinde çalışabilir. Üç başlangıç profili ve başarısızlıktan toparlanma yolları korunacak.

## Kapanmayan belirsizlikler

- Nihai bilim AOI'si ve tekil görüntü/ölçüm ürünlerinin gerçek örtüşmesi.
- Resmî challenge Resources listesinin erişim açılınca son kontrolü; takım kaydı ve yerel etkinlik ayrıntıları.
- Unreal/üçüncü taraf bağımlılıkları ile 2026 Solution Materials koşullarının teslim özelinde uyumu; engine kaynağını açık lisansla yeniden dağıtma hakkı varsayılmıyor.
- Windows UE 5.8.4 köprüsünün derleme/çalışma doğrulaması; drone aerodinamiği ve temas/cihaz modellerinin geçerliği.
- İnsan kaynak modeli ve eğitim değerlendirmesinin gerçek astronotlara genellenebilirliği.

Bu belirsizlikler gizlenmeden ana kılavuza aktarıldı. Üç tur tamamlandı; sonuçlar [PROJE_KILAVUZU.md](../PROJE_KILAVUZU.md) içinde birleştirildi.

## Birleştirme sonrası belge kontrolü

Bağımsız soğuk okumada çıkan yedi konu işlendi: mevcut demo/devralma yolları; yerel veri/provenance ve eski test kayıtları; zorunlu astronot proxy'si; bağlantı deneyi/ilk oynanabilir/tam görev kabulü ayrımı; sonuç doğruluğu ile kanıta uygun kararın ayrı puanlanması; ilk alternatif deneyin koşu başından yeniden yürütme olması; ilk action'ların goal/feedback/result ve iptal/tekrar sözleşmesi. Yeni bilgisayar kurulumu, derlenmiş bridge ve tam state restore yapılmış gibi yazılmadı.

Bu kontrol doküman tutarlılığı ve bağlantılar içindir. Yeni ROS/Unreal sistem testleri veya varlık içe aktarma deneyi çalıştırılmadı. Mevcut ROS README'sindeki taşınmadan kalan iki açılış/derleme yolu güncel depo düzenine göre düzeltildi.
