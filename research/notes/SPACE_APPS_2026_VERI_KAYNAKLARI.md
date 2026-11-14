# Space Apps 2026 kaynakları ve REDLINE veri seçimi

14 Kasım 2026 · Web kaynak incelemesi · Büyük veri, eklenti veya uygulama indirilmedi.

**Doğrulanan yayın, challenge Resources listelerinin açılacağı duyurusudur.**
NASA Space Apps GO Team'in 6 Kasım yanıtı, kaynakların 12 Kasım'da erişime
açılacağını söylüyor. Bu taramada Space Apps'in ayrıca yeni ve tek bir hazır
Mars/ROS/Unreal veri paketi yayımladığı doğrulanamadı.
[Birincil duyuru](https://github.com/nasa/spaceapps/discussions/1849).

## 1. Resmî listeye erişim ve bulunan kopya

Seçili konu **Interplanetary Survival Guide: Martian Map**.
[Resmî Resources sekmesi](https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/?tab=resources)
web aracında erişim/502 hatası verdi. Yerel HTTPS denemelerinde de sertifika
zinciri doğrulanamadı; doğrulama kapatılmadı. Dolayısıyla listeyi resmî sayfadan
doğrudan okuduğumuz söylenemez.

[HackAthlone organizatör kopyasında](https://hackathlone.com/challenges/interplanetary-survival-guide-martian-map)
beş kaynak görünüyor. Bunlar paketlenmiş tek bir veri seti yerine portal, harita,
galeri ve örnek görselleştirme bağlantılarıdır. Kopya, resmî sayfanın son söz
olduğunu da belirtiyor. Bağlantılı kaynaklar aşağıda kendi üretici sayfalarıyla
ayrıca incelendi.

| Kopyadaki kaynak | REDLINE için somut rol | Seçim |
|---|---|---|
| NASA Mars Trek | Katman keşfi; kontrol merkezi/tablet için kaynaklı harita servisi | Öncelikli |
| USGS-NASA gezegen jeoloji haritaları | Bilim hedefinin bölgesel jeoloji bağlamı | Saha/ölçek uygunluğuna göre |
| Curiosity rota görselleştirmesi | Bilim bölgelerini rota üzerinde anlatma örneği | Arayüz ve görev anlatımı referansı |
| NASA Worldview | Dünya gözleminde katman/zaman arayüzü örneği | Mars çevre verisi olarak kullanılmaz |
| Perseverance ham görüntü galerisi | Yer görünümü ve hedef inceleme | Ayrı Jezero profili veya açık görsel referans |

## 2. Harita ve rota için en yararlı kaynak

[Mars Trek açıklaması](https://trek.nasa.gov/mars/jpl/config/textAbout.html)
katmanlı ürün inceleme, indirme ve arazi analizi işlevlerini anlatıyor.
[WMTS API belgesi](https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars)
harita görüntülerinin standart tile servisiyle alınabildiğini doğruluyor.
GetCapabilities içinden ürün, kapsam, tile matrix ve dosya biçimi okunmalı.
Bu incelemede tekil WMTS ürününün sahaya uygunluğu veya gerçek tile akışı test edilmedi.

Mühendislik önerisi: habitat haritasında bir Mars Trek katmanını kaynağıyla
göstermek; robot fiziği ve eğim hesabında ise doğrulanmış sayısal DEM kullanmak.
JPEG/PNG hillshade görüntüsü yükseklik rasteri değildir. Zoom veya tile seviyesi
ölçüm çözünürlüğünü artırmaz. Çevrimdışı kullanım, veri/servis koşullarına uygun
küçük bir yerel saha paketiyle ayrıca hazırlanır.

Mevcut Gale DEM/LRGB denemesi yararlı temel olarak kalır. Yeni Yellowknife
bilim sahasında PDS hedef anlamı, koordinat, görüntü footprint/no-data ve
DEM hizalaması kapanmalıdır. [Mevcut saha QA'sı](SAHA_VE_BILIM_ISTASYONU.md).

## 3. Rover otonomisi için doğrudan veri seti: AI4Mars

[NASA Open Data AI4Mars kaydı](https://data.nasa.gov/dataset/ai4mars-a-dataset-for-terrain-aware-autonomous-driving-on-mars)
Mars arazi sınıflandırma modellerini eğitme/doğrulama amacı taşıyor. Kayıt,
rover görüntülerine ait semantik etiketler ve uzman doğrulama etiketleri
tanımlıyor. Bu kayıt yeni bir Space Apps 2026 yayını değildir; yayın/metadata
tarihleri ve veri sürümü ayrı okunmalıdır. Katalog açıklamaları arasındaki
adet farkları nedeniyle burada tek bir kesin örnek sayısı benimsenmedi.

Önerilen kullanım: görüntü → arazi sınıfı/belirsizliği → ROS harita katmanı →
geometri ve araç profiliyle birlikte geçiş değerlendirmesi. Bu bir uygulama
önerisidir; model eğitilmedi. Etiketler zemin dayanımı, teker kayması veya insan
güvenliği ölçümü yerine geçmez. Gerçek rover görüntüsünden Unreal kamerasına
aktarımı ayrıca sınamak gerekir.

NASA kataloğunun dağıtım kaydı [Zenodo 15995036](https://zenodo.org/records/15995036)
adresine yönleniyor; Zenodo içeriğine bu turda erişilemedi. Eğitim indirmesinden
önce sürüm, lisans, dosya/maskeler, uzman test ayrımı ve boyutlar doğrulanır.
Tam arşiv indirilmedi.

## 4. Unreal için ek seçenek: Cesium Mars

Bu, organizatör kopyasındaki beş kaynaktan ayrı bir bulgudur; Space Apps'in yeni
yayımladığı veri paketi olarak sunulmaz.

[Üretici sayfası](https://cesium.com/platform/cesium-ion/content/cesium-mars/)
NASA/USGS ve ESA verilerini 3D Tiles olarak birleştiriyor. Yaklaşık çözünürlükler:

| Kapsam | Arazi | Görüntü |
|---|---|---|
| Global | 200 m | 232 m |
| Jezero | 20 m | 6 m |
| Gale | 1 m | 25 cm |

Bu değerler seçilen mikro-sahanın kapsandığı veya her ayrıntının ölçüldüğü
garantisi değildir. Yerel kaynak/no-data kontrolü gerekir. Yüksek çözünürlüklü
renk görünümünün bir kısmı düşük çözünürlüklü renk ile birleştirilmiştir.

[Unreal için resmî öğretici](https://cesium.com/learn/unreal/unreal-moon-mars/)
Mars tileset'ini eklemeyi ve CesiumGeoreference üzerinde Mars elipsoidini
seçmeyi anlatıyor; ion hesabı/token ve uygun eklenti gerekiyor. Bizim 5.8.4
kurulumunda eklenti/build denenmedi, hesap veya token oluşturulmadı.

Mühendislik değerlendirmesi: geniş çevreyi Unreal'da hızlı inceleme adayı.
İlk görev alanında sabit, ortak kökenli yerel geometriyi ROS/Gazebo ile eşlemek
hâlâ gerekli. Uzak katman akışı, interneti belirsiz hackathon gösteriminin tek
dayanağı yapılmamalı; yerel paket/dağıtım koşulları ayrıca değerlendirilir.
Mevcut arazi hattını değiştiren karar henüz alınmadı.

## 5. Diğer bağlantıların doğru kullanımı

[JPL PIA23179](https://www.jpl.nasa.gov/images/pia23179-curiositys-proposed-path-up-mount-sharp/)
15 Mayıs 2019 tarihli önerilen Curiosity rotası animasyonudur. MRO HiRISE/CRISM/CTX
ve ESA HRSC verilerini bir araya getirmesi, bizim hedef–bilim–rota sunumumuza
örnek oluşturur. Güncel yürütülebilir otonom sürüş planı değildir.

[Perseverance galerisi](https://mars.nasa.gov/mars2020/multimedia/raw-images/)
yer görünümü sağlar; galeri görüntüsü tek başına kalibre geometri veya hedef
konumu sağlamaz. Gale/Yellowknife hedefinin gerçek fotoğrafı için Curiosity
kayıtları eşleştirilir; Jezero görüntüsü o konumun ölçümü gibi yerleştirilmez.

[NASA Worldview açıklaması](https://earthdata.nasa.gov/s3fs-public/2025-03/worldview-booklet.pdf?VersionId=vkMI8sbfY1WdDGqFKFSUus_orr4xsYnv)
Dünya gözlem verilerine yönelik olduğunu doğruluyor. Mars tozu/hava durumu için
REMS, MEDA veya uygun Mars arşivi/modeli gerekir; Worldview Dünya katmanı bu
eksikliği kapatmaz.

## 6. Proje için karar

Ana veri hattı korunur: **Gale/Yellowknife için doğrulanmış DEM ve yörünge
görüntüsü + Curiosity yer gözlemleri/konumları + APXS/CheMin bilim kayıtları**.
Mars Trek harita erişimi için öncelikli, AI4Mars algı deneyi için ayrı eğitim
kaynağı, Cesium Mars ise Unreal sahnesi için değerlendirilecek alternatif olur.
Numune kökeni ve cihaz sonucu haritaya bağlanır; yeni Gale pH sonucu mevcut
tasarımda açıkça simülasyon olarak kalır.

GO Team yanıtı Global Awards için challenge Resources listesinden en az bir
NASA kaynağının gerçekten kullanılmasını istiyor. Resmî listeye erişim açıldığında
seçilen ürünün o listedeki kaynakla bağı tekrar kontrol edilmelidir. Portalın
logosunu veya linkini eklemek yerine kullanılan ürün ve çıktısı belgelenir.

Bu tur kaynak incelemesidir: yeni veri seti/eklenti kurulmadı, büyük arşiv
indirilmedi, yeni ROS/Unreal deneyi yapılmadı.
