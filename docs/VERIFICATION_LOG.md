# Doğrulama günlüğü

14 Kasım 2026 · Europe/Istanbul · Yeni depo hazırlığı. Aşağıdakiler bu aktarım sırasında alınan sonuçlardır; tarihsel araştırma bulguları yeni doğrulama sayılmaz.

## Aktarım ve bütünlük

| Kontrol | Sonuç | Kanıt / sınır |
|---|---|---|
| Hedef repo | GEÇTİ | `git remote -v`: `https://github.com/ahmetefesensoy/redline.git`; `main...origin/main`. Aktarım öncesi çalışma ağacı temiz, yalnız `.git` mevcut. |
| Paket | GEÇTİ | 562 ZIP girdisi; 7.911.552 bayt açılmış içerik; manifest hariç 561 payload dosyası. |
| ZIP yol güvenliği | GEÇTİ | Hedef kökten çıkış, `.git` girdisi, Windows sürücü yolu, mevcut dosyayı ezme, case-insensitive tekrar ve symlink kontrolü. |
| Payload bütünlüğü | GEÇTİ | Manifestteki 561 dosyanın tamamında boyut ve SHA256 eşleşti; 0 sorun. |
| Proje skill bütünlüğü | GEÇTİ | `python -X utf8 tools/verify_skill_installation.py`: `Project skills checked: 18`, `Recorded files checked: 428`, `Issues: 0`; exit 0. |
| Yeni uygulama kodu | HENÜZ YOK | Paket eski ROS/web/rover uygulamasını içermiyor. `önceki deneme` altında yalnız araştırma Markdown ve provenance kayıtları var. Skill helper'ları uygulama kodu değildir. |

Kaynak arşiv: `C:\Users\USER\Desktop\space apps\output\handoff\REDLINE_V3_BASLANGIC_PAKETI.zip`.

Arşiv SHA256: `3B4554361A7CE998168B4F7AC9AF92B6A602ACC352F2DC110F4F53E523E33DAE`.

`HANDOFF_MANIFEST.json` orijinal payload'ı tanımlar. Bu günlük ve diğer yeni kayıtlar aktarım sonrasında oluşturulduğundan özgün payload manifestine eklenmedi.

## Windows envanteri

| Bileşen | Gözlenen sonuç | Doğrulamanın sınırı |
|---|---|---|
| Python | 3.12.10 | `python --version`, `py -0p`; yeni proje venv'i oluşturulmadı. |
| Node / npm | v24.22.1 / 11.19.1 | Mevcut sürümler; spekteki Node 20 [?] yerine pin seçilmedi. Open MCT engine gereksinimleri uygulama aşamasında kontrol edilecek. |
| Git / gh / uv | 2.56.0.windows.3 / 2.103.3 / 0.13.6 | Sürüm komutları çalıştı. |
| WSL | Ubuntu-24.04, WSL2, Running | `wsl --list --verbose`; docker-desktop ayrıca listede, Stopped. |
| Unreal | 5.8.4, changelist 58902052 | `C:\Users\USER\Desktop\UE_5.8\Engine\Build\Build.version` okundu; editör veya build çalıştırılmadı. |
| Visual Studio C++ | VS 2022 Community | `vswhere` ile VC.Tools.x86.x64 bileşenine sahip kurulum bulundu. UE uyumlu toolset/SDK ve gerçek derleme henüz denenmedi. |
| Yeni UE projesi | YOK | `unreal/Redline/Redline.uproject` mevcut değil. |
| Blender ortak referansları | EKSİK | `C:\Users\USER\.codex\skills\references` yok; aktarımda belirtilen eksik devam ediyor. |

## WSL temel ortamı

Ubuntu 24.04.5 LTS; kullanıcı `ahmetefesensoy`; kernel `6.18.33.2-microsoft-standard-WSL2`; Python 3.12.3.

ROS ortamı `/opt/ros/jazzy/setup.bash` ile yüklendikten sonra:

| Bileşen | Gözlenen sonuç |
|---|---|
| ROS_DISTRO / rclpy | jazzy / `/opt/ros/jazzy` |
| colcon | `/usr/bin/colcon`; common extensions 0.3.0-100 |
| ROS base | 0.11.0 |
| ros_gz_bridge | 1.0.24 |
| navigation2 / nav2_bringup | 1.3.13 / 1.3.13 |
| ros2_control / gz_ros2_control | 4.48.1 / 1.2.20 |
| Gazebo | `gz sim --version`: 8.15.0 (Harmonic); ROS vendor yolu üzerinden erişiliyor. |
| Gazebo meta paketi | `gz-harmonic` adlı paket bulunmadı. Bu, çalışan `gz sim` sürüm kontrolünü geçersiz kılmaz. |
| rosbridge / MoveIt / Foxglove | İlgili `ros-jazzy-rosbridge-server`, `ros-jazzy-moveit`, `ros-jazzy-foxglove-bridge` Debian paketleri bulunamadı. Diğer workspace'lerde source kurulumu araştırılmadı. |
| GDAL/GIS | `gdalinfo` PATH'te yok; `gdal-bin` sürüm döndürmedi. Temel Python'da `pip show` GDAL, rasterio, pyproj, pystac, spiceypy, pvl, pds4-tools bulamadı. Diğer venv'ler hakkında sonuç çıkarılmadı. |
| numpy / scipy | 1.26.4 / 1.11.4, WSL temel Python ortamı. |
| WSL GPU aygıtı | `/dev/dxg` var. GPU/sensör render testi yapılmadı. |

İlk WSL envanter komutunda `set -u`, ROS setup dosyasındaki opsiyonel `AMENT_TRACE_SETUP_FILES` değişkeninde durdu. Envanter komutu `set -u` olmadan tekrar çalıştırıldı; ROS_DISTRO, rclpy ve Gazebo sonuçları bu ikinci çalışmadan alındı. Sistem/ROS setup dosyaları değiştirilmedi.

## Windows → WSL localhost deneyi

WSL Python `http.server` ile yalnız `127.0.0.1` üzerinde boş port seçilerek tek istek alan geçici sunucu açıldı. Windows PowerShell'den `Invoke-WebRequest` çağrısı yapıldı.

- Son test portu: 46153.
- HTTP: 200.
- Gövde: `REDLINE_T0_NETWORK_OK`.
- Doğrulama komutu exit 0; sunucu tek isteğin ardından kapanarak exit 0 verdi.
- İlk denemede HTTP 200 ve doğru byte dizisi geldi; testin byte[]/string karşılaştırması hatalıydı. Content-Type ve UTF-8 çözümü eklenerek deney tekrarlandı ve geçti.
- Bu sonuç yalnız HTTP localhost erişimini gösterir; rosbridge/WebSocket, DDS, QoS veya gerçek ROS topic testi değildir. `.wslconfig` değiştirilmedi.

Windows TCP dinleyici kontrolünde 9090, 8765, 8080, 8081 ve 8082 portlarında dinleyici görülmedi. WSL tarafındaki tüm portların boş olduğu iddia edilmez.

## Açık işler / henüz test edilmedi

- T0: yeni venv, uygulama/ROS paketleri, `redline_msgs` derlemesi, pytest, colcon test ve CI.
- Yeni Unreal C++ proje/toolset/SDK build doğrulaması; oyun ve bridge Automation testleri.
- Rosbridge WebSocket ve ROS–Unreal dönüşüm/saat/tazelik sözleşmeleri.
- Mars ürünlerinin gerçek indirilmesi, CRS/label incelemesi, piksel hizalaması ve APXS koordinat anlamı.
- GIS venv bağımlılıkları ve GDAL ≥3.8.
- Ham BXW/YKB/RAD ürünleri bu aktarım paketinde sağlanmadı.
- Spek/araştırmadaki [?] maddeler kendi uygulama aşamasında küçük deneylerle doğrulanacak.

İlk aktarım anında kaynak verisi veya yeni uygulama olmadığı için pytest/colcon sonuçları üretilmedi ve T0 yeşil işaretlenmedi. Aşağıdaki tarihli T0 kaydı bu başlangıç durumundan sonra elde edildi.

## T0 — 14 Kasım 2026, 12:52 (+03:00)

Kullanıcının uygulama başlangıcı yönlendirmesiyle `docs/proje.md` §4/5/18 esas alınarak Python paketleri, ROS arayüz paketi, bootstrap/test script'leri ve CI sıfırdan yazıldı. [Yerel sonuç kaydı](verification/T0_LOCAL_2026-11-14.json) test raporlarının hash'lerini içerir.

| Gerçek kontrol | Sonuç |
|---|---|
| Saf Python pytest | 53 geçti, 0 hata/başarısız/atlanan; Python 3.12.3, pytest 8.3.5. |
| ROS arayüz build | Jazzy `colcon build` başarılı; 22 msg, 5 srv, 11 action. |
| Üretilmiş typesupport/CDR testleri | 98 geçti; pytest 7.4.4, sistem Python. |
| Colcon/CTest toplamı | 99 test (98 pytest + CTest wrapper), 0 hata/başarısız/atlanan. |
| Kaynak kopya kökeni | Snapshot ve güncel 42 ROS paket dosyasının SHA256 değerleri eşleşti; eski overlay kullanılmadı. |
| CLI kurulumu | Gerçek venv console entrypoint: `redline-data --version` → `redline-data 0.1.0`. |

İlk denemede ROS ortamının `PYTHONPATH` değeri saf venv'e `launch_testing` eklentisini sızdırdı; yaml import hatası nedeniyle test başlamadı. Saf pip/pytest çağrılarında ROS Python yolu temizlendi, pytest otomatik eklenti yüklemesi yalnız saf test çağrısında kapatıldı. ROS test ortamı bu ayarla değiştirilmedi.

İkinci denemede 50 saf test geçti; ROS configure işlemi Windows yolundaki `İ` karakterini keserek `rosidl_generate_interfaces.cmake:234` hatası verdi. Sistem ROS'u yamalamadan, kaynak hash'i doğrulanan yeni ASCII Linux workspace yoluna geçildi. Son testte eklenen UTC taşma regresyonlarıyla 53 saf test, ROS build ve 98 ROS arayüz testi geçti.

İlk GitHub CI koşusu [43582459866](https://github.com/ahmetefesensoy/redline/actions/runs/43582459866), `rosdep: error: no such option: --yes` nedeniyle bağımlılık adımında durdu. Yerel `rosdep install --help` ile desteklenen `-y` doğrulandı ve workflow düzeltildi. Yeni CI sonucu ayrıca kaydedilecek; bu ilk koşu yeşil değildir.

Sınır: Bu kanıt saf sözleşme testleri ve arayüz build/codec testleridir (ROS skill L1 ve build kısmı L2). Çalışan bir ROS düğümü/DDS grafiği, Gazebo görevi, Unreal köprüsü veya uçtan uca görev testi yapılmadı. T1 veri QA'sı ve T2 rota/altın testleri henüz yoktur.
