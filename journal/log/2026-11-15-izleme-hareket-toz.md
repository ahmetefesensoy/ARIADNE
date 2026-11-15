# Aynı oturumda RViz, robot haritası ve hareket/toz sunumu

15 Kasım 2026, 10:25 (+03:00) · Durum: PARTIAL_PREVIEW.

Bu çalışma mevcut 12 adımlı EVA'ya izlenebilirlik ve sunum ekler. Uzak saha/PR
yolculuğu, yeni bina yerleşimi ve son kum görsel kalitesi bu kayıtla bitmedi.
Sonraki yerleşim ve kabul sırası [tasarım notunda](../../docs/SONRAKI_OYNANIS_DILIMI.md).

## Uygulama

- `CAMPAIGN_RVIZ=1` aynı ROS domain'i ve Gazebo dünyasına pasif RViz açar.
  `prepare_campaign_rviz.py` odağı gerçek koşu manifestindeki rover spawn'ından
  üretir. Harita/planın yalnız gösterim kopyaları Mars kotuna taşınır; Nav2
  kaynakları değişmez. SetGoal/InitialPose araçları bulunmaz.
- `CAMPAIGN_RVIZ_DRIVER=d3d12` seçilebilir; llvmpipe varsayılanı korunur.
  Yerel `glxinfo -B`, D3D12 NVIDIA GeForce RTX5080 / accelerated=yes bildirdi.
  CUA'da RViz rover modeli, footprint/costmap ve Global Status: Ok görüldü.
  İlk GPU probe'unda ve son koşuda başlangıç GLSL sampler link hatası kaydı
  mevcut; bunu çözülmüş veya bütün harita katmanları doğrulanmış saymıyoruz.
  Son WSLg pencere başlığı WARN:COPY MODE taşıyor; bunun için aktif başka
  oturum veya kullanıcının oyunu kapatılmadı.
- Robot konsolu `/redline/presentation/rover_1/odom`, `/rover_1/plan` ve gerçek
  Nav2 durumunu salt okunur alır. Metre cinsinden ENU haritası gerçek izi ve
  planı eş ölçekle çizer. Hız fizik zamanındaki poz farkıdır. Veri yaşı, eski
  plan/durum, boş plan ve henüz hedef olmaması görünürdür. Geçmişler sınırlıdır;
  frame/quaternion hatası, saat tekrarı/sıfırlaması ve sıçrama korunur.
- Astronot için native animasyon proxy'si mevcut idle/walk pozlarını harmanlar.
  Başlama/durmada klip sıfırlanmaz; kadans gözlenen hızdan yumuşak değişir.
  Gerçek koşu klibi yoktur; yürüyüş temposu koşu yakalaması olarak sunulmaz.
  Kapsül, hız sınırları ve ayak kökenli ROS pozu aynı otoritede kalır.
- İlk `ARedlineSurfaceDust` katmanı 96 havuzlanmış yumuşak düzlem kullanır.
  Toz kısa ömürlü ve düşük opaklıklıdır. Güncel robot pozu, yere yakınlık ve
  hareket denetlenir; astronotta yerde hareket, droneda düşük irtifa etkisi
  vardır. Park, yüksek uçuş, eski/reddedilen poz veya bina tabanı üretimi
  durdurur. Kaynak terrain asset kimliği kontrol edilir. Bu native SCENARIO
  sunumudur; Niagara, ölçülmüş Mars rüzgârı veya granüler zemin fiziği değildir.
  Kum taban malzemesinin son kalite geçişi ve her kaynakta ayrı görsel toz
  kabulü henüz yapılmadı.

## Kanıt

`campaign-motion-dust-final-build.log`: UE5.8.4 güncel derleme geçti.
`campaign-motion-dust-tests.json`: 27 native test geçti, üçü uyarılı başarılı.
Yeni testler gerçek varlıkla poz harmanlamasını, rota/hız/zaman korumalarını,
eş ölçeği, tozun kaynak kapılarını, sınırlı havuz/sonlanma ve yalnız terrain
temasını kapsar. `campaign-observer-guards.xml`: 22 Python testi geçti.
`surface-dust-material.json`: prosedürel malzeme kaydedildi ve projeye alındı.

İlk derleme C2487 (iki static constexpr'in aynı bildirimde DLL export'u)
nedeniyle başarısızdı; bildirimler ayrıldı. İkinci derleme sırasında eklenen
test kaynak hash korumasını tetikledi; son sabit kaynak snapshot'ı yeniden
derlendi ve test edildi. Ara hata kayıtları korunur.

`campaign-5sCXM8p0` koşusunda Nav2 map_server yaşam döngüsü servis yanıtı zaman
aşımına düştü ve read-only hazır olma kontrolü başarısız oldu. Eski koşu
korundu; yalnız kendi süreçleri durduruldu. Yeni domain145/aynı port9390
koşusu `campaign-KNsxhu6O` içinde Nav2 managed nodes active görüldü. Bu çevrim
yeniden açılışı kök nedenin çözüldüğü anlamına gelmez. Güncel fizik/duvar oranı
yaklaşık 0,48×; gerçek zaman performans hedefi açıktır.

CUA'da genişletilmiş robot paneli güncel poz/hız, boş Nav2 planı ve scout
durumuyla görüldü. Ardından gerçek oyunculu yürüyüş ve scout taraması gözlendi.
Keşif tamamlanıp 28 SIMULATED gözlem kanıtıyla saha kararı açıldı. Bu kullanıcı
oturumuna otomatik insan poz fixture'ı veya tanılama Nav2 hedefi gönderilmedi.
Hazırlanan `verify_campaign_presentation_drive.py`, yalnız boş brifingde tek
kısa simülasyon hedefi için gelecekte kullanılabilir; bu tur çalıştırılmadı.
Dolayısıyla yeni panelde hareketli rover çizgisinin uçtan uca görsel kabulü
ve tozun yakın plan görsel kabulü henüz yoktur.

Müzik/APXS/kaçak koduna ve Git/GitHub'a dokunulmadı; model kredisi kullanılmadı.
Önceki 151 ROS testi bu turun yeni test sayısı değildir; bu değişiklikler için
tam ROS paketi yeniden derlenmedi. Çalışan ROS prefix'i önceki doğrulanmış
`ws-dc2376c9106aee04-hv07atae` snapshot'ıdır.
