# Rover önizlemesi

14 Kasım 2026 · Unreal 5.8.4 / ROS 2 Jazzy / Gazebo Harmonic.

`/Game/VisualShowcase/BXW_Atmosphere_Autonomy`, mevcut NASA rover modelini
ve BXW arazi türevlerini kullanan bir **SCENARIO görsel önizlemesidir**.
Atmosfer, dolgu ışığı, kum mikroyapısı, teker izi ve test engelleri ölçülmüş
Mars verisi değildir. Referanslardaki kayalık sahnenin tamamı henüz yapılmadı.

## Açılış

Çalışan ROS/Gazebo, `t4_rosbridge.sh` ve `gazebo_presentation.py` gerekir.
ASCII derleme önbelleğinde içerik hazırsa:

```powershell
./scripts/start-t4-look.ps1 -RosbridgeUrl ws://<guncel-WSL-IP>:9090/
```

1280×720 pencere, %200 iç çizim çözünürlüğü ve 60 FPS üst sınırı kullanılır.
Bu ayarlar ölçülmüş bir 60 FPS garantisi değildir. `1 / 2 / 3` tuşları yalnız
SCENARIO gösterisinde Gazebo için 1× / 2× / 4× talep eder. Gerçekleşen oran
ekranda ayrıca gösterilir; görev/PET saati değiştirilmez.

İlk kurulumda C++ için `scripts/build-t4.ps1`, teknik arazi için
`t4_prepare_unreal_fixture.py`; görseller için sırasıyla
`t4_prepare_live_preview.py`, `t4_prepare_obstacle_showcase.py`,
`t4_prepare_visual_showcase.py`, `t4_prepare_atmosphere.py` kullanılır.
Python hazırlama betikleri Unreal Editor Python ortamında ve
`REDLINE_REPO` proje kökünü gösterirken çalışır. Girdi raporları ve FBX'ler
olmadan bu betikler tek başına veri indirme/kurulum yapmaz.

## Yetki ve malzemeler

- Robot fizik ve kontrolü ROS/Gazebo'dadır. Unreal çarpışma/fizik çalıştırmaz.
- Gösteri, `/redline/presentation/rover_1/odom` üzerindeki gerçek Gazebo
  model pozunu yalnız çizim için kullanır. Varsayılan teknik aktörün filtreli
  odometri sözleşmesi korunur. Fizik gerçeği Nav2/EKF girdisi değildir.
- Altı tekerin ayrı pozları ve iki hareketli SCENARIO engelinin pozları
  `/redline/presentation/scene` üzerinden gelir. Sensör/planlayıcıya gizli
  dünya nesnesi listesi verilmez.
- Mevcut 82 parçalı NASA roverı, gövde + altı teker FBX türevine ayrıldı.
  Kaynak atlas ve gövde oranları korundu; model uçuşa uygun CAD değildir.
  Teker/taşıyıcı hareketi gerçek rocker-bogie mekaniğinin tam doğrulaması değildir.
- Arazi atlasları 4096 pikselde kalır. Prosedürel normal/renk ayrıntısı yeni NASA
  ölçümü veya daha yüksek çözünürlüklü DEM sayılmaz.
- Teker izleri 90 saniyelik, en çok 800 decal ile sınırlı görseldir.
  2 cm kum çökmesi yalnız shader yer değiştirmesidir; granüler zemin fiziği değildir.
- 12.000 lux güneş için manuel fiziksel pozlama kullanılır: ISO 100,
  f/4, 1/125 s, EV100 10,97 ve +0,6 pozlama telafisi. Eski 5-lux önizlemenin
  pozlamasıyla görülen beyazlaşma bu şekilde giderilir.
- Yakın volumetrik sis kapalıdır; yükseklik sisi 100 m'den sonra başlar.
  Gün batımı yansıma küpü mevcut Unreal Engine içeriğidir. Bu sahne henüz
  T6'nın SPICE `/env/state` güneş yönüne bağlı değildir.

## Kabul ve açık işler

[T4 teknik kabulü](verification/T4_ACCEPTANCE.json) tarihli özgün kanıttır.
[Görsel güncelleme kaydı](verification/T4_VISUAL_UPDATE.json), sonraki build,
14 Unreal otomasyon sonucu, 7 Python testi ve canlı görüntü kontrolünü ayırır.
İçe aktarmanın başarılı olması tek başına görüntü kabulü değildir.

T3'ün ilk RViz hedef kabulü korunur. Daha sonra istenen alçak 3D engel algısı
ile tam hedef sürüşü, uzun rotalarda fizik/odometri farkı ve hedef hücresi
sınırındaki tek-poz plan reddi açık işlerdir. Son atmosfer gösterisindeki
ilk aksiyon status 6 ile bitti; fiziksel hedef farkı yaklaşık 0,10 m olsa da
bu başarılı otonom görev sayılmaz.

Genel uygulamada sıradaki dikey kabul T5'in EV1 + canlı kırmızı çizgi/pay
gösterimi, ardından T6'nın Unreal alarmı ve çizgi daralmasıdır. T6 ROS
altyapısının çalışması bu iki görsel kabulün tamamlandığı anlamına gelmez.
