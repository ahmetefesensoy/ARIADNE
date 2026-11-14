# REDLINE — Saha eşleştirme ve bilim istasyonu kararı

14 Kasım 2026 · Arşiv/metadata araştırması ve tasarım geliştirmesi · Yeni arazi veya uygulama üretilmedi.

**Numuneler haritadaki görev noktalarından alınacak; pH gibi numune analizleri uygun cihaz/hazırlıkla laboratuvarda veya tanımlı mobil cihazda yapılacak.** Sonuç, numunenin köken noktasına ve işlem geçmişine bağlanacak. Arşivde gerçekten ölçülmüş sonuç ile yeni simülasyon sonucu ayrı veri türleri olacak.

## 1. Ana saha için somut seçim

Öncelikli çalışma sahası **Yellowknife Bay/Sheepbed, John Klein ve Cumberland çevresi** olsun. İki belgeli hedef, yakın görüntü, APXS ve CheMin ürünleri bu kampanyayı veri eşleştirme ve sondaj/numune akışı için güçlü aday yapıyor. Bu karar saha araştırmasının önceliğidir; yeni fiziksel AOI'nin tamamlandığı anlamına gelmez.

Yedek **Bagnold/Namib–Gobabeb**: regolit/tane fraksiyonu karşılaştırması ve drone keşfi için uygun. İki bölge aynı yürüyüşte yan yana gösterilmez. Sondaj ve regolit kampanyaları ortak motorla farklı saha profillerinde çalışabilir.

Bilim sorusu: yakın örneklerdeki gözlenen farkı hangi yerel bağlam, hazırlık ve cihaz kaydıyla yorumlayabiliriz? Aynı Sheepbed birimindeki iki hedef iki farklı jeolojik birim diye adlandırılmaz. NASA iki sondaj hedefinin yaklaşık 2,75 m ayrıldığını açıklıyor. [JPL hedef bağlamı](https://www.jpl.nasa.gov/news/nasa-curiosity-rover-team-selects-second-drilling-target-on-mars/), [yer görünümü PIA17595](https://science.nasa.gov/photojournal/view-of-yellowknife-bay-formation-with-drilling-sites/).

## 2. Bu turda doğrulanan somut ürünler

| Kayıt | Doğrulanan içerik | Kullanım ve sınır |
|---|---|---|
| APXS supplement `ds01_2020je006536rr.csv` | 712 satır; hedef, site, hazırlık, zaman, koordinat ve oksit/hata alanları | Genel cihaz adı yerine gerçek hedef kayıtları; tablo koordinatı kesin sondaj deliği pozu sayılmaz |
| Sol 169 `Wernecke_Brushed`, site `John_Klein` | APXS hedef satırı ve hazırlık kodu `RB` | John Klein çevresinde kaynaklı yer ölçümü; hedef, delikle aynı nesne gibi gösterilmez |
| Sol 276 `CumberlandNew_RP`, site `Cumberland` | APXS hedef satırı ve hazırlık kodu `RU` | Hazırlık ve gözlem zamanını dikkate alan bilim karşılaştırması |
| `CMA_414856883MIN01960060000CH12240P1` | John Klein drill sample için CheMin mineral bolluğu CSV'si ve label | Ön/tarihsel analiz; label'da kristal, kil ve amorf yorumları/analitik hata ayrı. Güncel en iyi sonuç olduğu varsayılmaz |
| `CMB_422579177MIN02830060082CH12350P1` | Label açıkça Cumberland drill sample diyor | Örnek ve cihaz sonucu bağlantısı doğrulandı; bilimsel karşılaştırmada label/sürüm/normalizasyon ayrıca okunur |
| `PSP_010573_1755_RED` v2.0 | MRO HiRISE map-projected ürün; label grid 0,25 m | Yörünge bağlamı; gerçek çözünürlük, koordinat ve boş piksel kontrolü ayrıca gerekir |
| Gobabeb sol 1226/1242 | `Gobabeb_DumpA_APXS` ve `Gobabeb_DumpC_corrected` satırları | Yedek regolit kampanyasında farklı hazırlık/fraksiyonlar; aynı yeni örneğin iki kusursuz ölçümü gibi ele alınmaz |

Kaynaklar: [APXS CSV](https://pds-geosciences.wustl.edu/msl/urn-nasa-pds-msl_apxs_supplement_sols_0_2301/data/ds01_2020je006536rr.csv), [APXS ürün etiketi](https://pds-geosciences.wustl.edu/msl/urn-nasa-pds-msl_apxs_supplement_sols_0_2301/data/ds01_2020je006536rr.xml), [John Klein CheMin etiketi](https://pds-geosciences.wustl.edu/msl/msl-m-chemin-4-rdr-v1/mslcmn_1xxx/data/rdr5/cma_414856883min01960060000ch12240p1.lbl), [Cumberland CheMin etiketi](https://pds-geosciences.wustl.edu/msl/msl-m-chemin-4-rdr-v1/mslcmn_1xxx/data/rdr5/cmb_422579177min02830060082ch12350p1.lbl), [HiRISE ürün sayfası](https://hirise.lpl.arizona.edu/PSP_010573_1755), [HiRISE label](https://hirise-pds.lpl.arizona.edu/PDS/RDR/PSP/ORB_010500_010599/PSP_010573_1755/PSP_010573_1755_RED.LBL).

## 3. Eşleşmede gerçekten ne ilerledi?

HiRISE label'ının sayısal sınırları −4,645359…−4,340801° enlem, 137,325432…137,465012° doğu boylamıdır. APXS'deki iki Yellowknife hedef satırının sayısal lat/lon'u bu kutuda kalıyor. Gobabeb satırları bu ürünün kutusunda değil; ona aynı görüntü otomatik atanmayacak.

Bu, **metadata düzeyinde aday örtüşmedir**. APXS koordinat anlamı/enlem türü, görüntü gerçek footprint/no-data ve DEM/ortho hizalaması henüz kapanmadı. HiRISE merkez koordinatının hedef koordinatı olması gerekmez; label sınırları kullanıldı. JP2 indirilip piksel örneklemesi veya yeni arazi üretimi yapılmadı.

Ek QA: APXS'nin John Klein çevresi ve Cumberland satır konumları yaklaşık 1 m ayrılırken NASA delik haritası yaklaşık 2,75 m ilişki veriyor. Bunlar farklı hedef/kayıt referanslarıdır; aynı kesin delik pozunu verdiği varsayılmaz. Görüntü/araç pozu/pointing ve koordinat sistemiyle mikro-konum kontrolü gerekir. Numune alma yeri ile analiz/target konumunun ayrımı da satır/prosedür bazında doğrulanır.

PLACES tablosunda seçilen dört sol için tam `frame=ROVER` eşleşmesi bulunmaması, o günlerde konum bilgisi olmadığı sonucunu vermez; tablonun örnekleme/yerelleştirme semantiği incelenmelidir. Bu nedenle konumu yalnız sol eşitliğiyle bağlamayacağız.

Makinece okunur araştırma kayıtları: [APXS seçili satırlar ve hash](APXS_HEDEF_ON_KONTROL.json), [HiRISE label/kutu kontrolü](HIRISE_YELLOWKNIFE_METADATA_KONTROLU.json), [John Klein ve PLACES sorgusu](SAHA_OLCUM_METADATA_KONTROLU.json), [Cumberland label kaydı](CUMBERLAND_CHEMIN_URUN_KONTROLU.json).

## 4. pH nerede olacak?

Gale görevindeki oyun akışı: **saha hedefi → regolit numunesi → kap/konum kaydı → H05 laboratuvarı → uygun hazırlık/kalibrasyon → pH/iletkenlik sonucu → numunenin köken noktasına bağlı harita kaydı.** Mobil analiz seçilirse cihazın gerçek konumu ve işlem profili de ayrıca kaydedilir. Numune kökeni değişmez.

Phoenix'in WCL sistemi pH, iletkenlik ve ilgili ıslak kimya ölçümleri için gerçek referanstır. PDS koleksiyonu `urn:nasa:pds:phx_meca:data_wcl::1.0`, parent DOI `10.17189/1518770`; gözlem bağlamı Phoenix'in 2008 kaydıdır. [PDS koleksiyonu](https://pds.nasa.gov/ds-view/pds/viewCollection.jsp?identifier=urn%3Anasa%3Apds%3Aphx_meca%3Adata_wcl&version=1.0), [WCL cihaz/prosedür açıklaması](https://an.rsl.wustl.edu/help/Content/About%20the%20mission/PHX/Instruments/PHX%20WCL.htm).

**Gale'deki yeni pH sonucu gerçek NASA ölçümü değil, tanımlı bir simülasyon analizi olacak.** Phoenix kaydı prosedür/referans olarak açılır. Sayısal model henüz kurulmadı; minerallerden veya görüntü renginden otomatik pH türetilmeyecek. İlk prosedür prototipinde senaryo örnek profili ve açık kalite/ölçüm durumu kullanılabilir; fiziksel kimya modeli olduğu iddia edilmez. Gerçek pH'ı doğrudan gerçek örnekleme yerine bağlamak istenirse ayrı Phoenix saha profili hazırlanır.

Laboratuvar, yalnız grafik duvarı değildir: kap kabul/kimlik, uygun cihaza yönlendirme, hazırlık/kalibrasyon durumu, ölçüm ilerlemesi, kalite kontrolü, karşılaştırma ve saklama işleri bulunur. Kullanıcı tekrar ölçüm veya başka örnek kararı verebilir. Sayısal analiz modelinin geliştirilmesi ile arşiv kaydı görüntüleme ayrı iş paketleridir.

## 5. Veri modeli ve Unreal görünümü

| Kayıt | Saklanan yer/zaman | Anlam |
|---|---|---|
| Saha gözlemi | Gözlem yeri, gördüğü bölge ve zaman | Görüntü/yerel engel/çevre gözlemi |
| Numune | Köken noktası/derinlik, alım zamanı, kap/araç/işlem | Malzemenin nereden geldiği |
| Analiz | Numune ID, cihaz konumu, hazırlık ve ölçüm zamanı | Numuneye hangi işlemin uygulandığı |
| Arşiv referansı | Özgün görev/ürün/yer/zaman | Karşılaştırmanın kaynağı; yeni yerel ölçüm değil |

Haritada numune noktası seçildiğinde alım fotoğrafı, konum belirsizliği, kap, analiz ve kalite açılır. Laboratuvar noktasında cihaz işleri görünür; bütün pH noktaları laboratuvar koordinatına yığılmaz. Sonuç numunenin özelliği olarak gösterilir; aradaki boş alana sürekli pH alanı boyanmaz. Zaman serileri ve örnekler arası karşılaştırma farklı grafik türleridir.

## 6. Diğer açıkları aynı akışta geliştirmek

- **İnsan/rover geçişi:** ortak geometri, ayrı footprint/kısıt/yük profili. Yerel gözlemden iki kullanıcı için uygun çıktı üret; rover geçişini insan güvenliği garantisi yapma.
- **Otonomi:** keşif/numune taşıma/inceleme işinde aynı başlangıç ve kaynakla manuel–otonom koşuları karşılaştır. Bilim/harita çıktısı, operatör zamanı ve yardım sayısını birlikte ölç.
- **Harita–Unreal:** hedef ve örnek ID'si aynı kayıttan gelsin; yanlışlıkla aynı isimli dekor taşa işlem yapılmasın. Robot pozu ve sensör görünümü ortak zaman/frame kullansın.
- **Kaynak sınırları:** veri yaşı, çözünürlük, koordinat anlamı ve kalite arayüzde açılsın. Geçersiz/gözlenmemiş noktalar ölçülmüş gibi görünmesin.
- **Vana:** bilim istasyonunun servis görevi olarak bağla; çalışır/arıza durumu analiz erişimini değiştirsin. Ana sahaya ait doğal gaz gözlemi diye sunma.
- **Görev sonucu:** her ölçüm rota değiştirmek zorunda değil; bilim sorusunu, örnek kalitesini veya sonraki cihaz/örnek kararını destekleyebilir.

## 7. Sonraki somut teslim

Önce iki Yellowknife hedefinin koordinat/ürün semantiği ve gerçek görüntü/DEM kapsaması kapatılacak. Sonra yeni küçük saha kırpımı ve hedef manifesti hazırlanacak. Ardından bir örnek için köken→kap→laboratuvar→analiz→harita akışı bağlanacak. pH simülasyon modülü bu kayıt hattına katılacak; sahte Gale arşiv sonucu oluşturulmayacak.

Bu turdaki ilerleme arşiv verisi/metadata düzeyindedir. Yeni arazi, laboratuvar, cihaz modeli veya ROS–Unreal uygulaması henüz yapılmadı.
