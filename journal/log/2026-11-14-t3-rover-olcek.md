# T3 rover ölçeği ve algı — 14 Kasım 2026

Teslim teker mesh çapları 0,4939–0,4994 m; NASA'nın 0,50 m çap / 0,40 m
genişlik bilgisiyle uyumlu. Uniform scale 1 korundu. Kol dahil 3,9447 ×
2,7772 × 2,2127 m dış kutu yalnız gövde uzunluğuna göre küçültülmedi.
[Ölçüm kaydı](../../docs/verification/ROVER_SCALE_AUDIT.json),
[NASA teker bilgisi](https://science.nasa.gov/resource/routine-inspection-of-rover-wheel-wear-and-tear/).

`stage_delivered_rover.py` kaynakları değiştirmeden ASCII önbellekte
SDF/URDF, mesh/malzeme kopyaları ve SHA-256/geometri kaydı üretir; NASA/JPL
bildirimi korunur. Altı teker pivotu iki açıklamada aynıdır. 899 kg toplam
kütlenin dağılımı, atalet ve temas silindirleri SCENARIO'dur. Yedek skid-steer
sürüşte direksiyon/süspansiyon sabittir; kol/mast collision henüz yoktur.
Navigasyon footprint'i kol dahil dış zarfı kapsar.

roversim27 salt okunur incelendi: `docs/runtime-architecture.md`,
`docs/terrain-navigation-validation.md`, `src/rover_navigation/config/`
altındaki planner/controller, kinematic_autonomy ve collision_monitor.
Kod kopyalanmadı. Referansta zemini ayrılmış PointCloud2, STVL, yerel/global
costmap, yaklaşma/yavaşlama/durma bölgeleri ve taze sensör/saat hazırlık
kapısı var. ERC footprint'i ve Dünya ayarları taşınmadı. Referans belgeleri
de tam otonomi kabulünü açık sayıyor.

RViz'e global/local costmap, LiDAR noktaları, kalın global rota, footprint
ve teslim profilinin stop/slow poligonları eklendi. Teknik gözlem ayarlarıdır.
Teslim inflation yarıçapı footprint çevrel çemberi + padding + 0,20 m'den
türetiliyor. Çalıştırma seçeneği: `scripts/run-t3.sh <workspace>
--terrain <surface-manifest> --delivered-rover`; `--obstacle-fixture`
ayrı, açık bir SCENARIO kabul hedefi ekler.

| Kanıt | Sonuç |
|---|---|
| `t3-build-Sf5IGsTj`, `ws-bfef533bf08597ff-4tyf3o0f` | 67 test kaydı: 58 case + 9 CTest wrapper, hata/başarısız/atlanan 0. |
| `t3-runtime-3Ct7Gcw9` | GUI + sensör render birlikte: Mesa D3D12 device removal / segfault, başarısız. |
| `t3-runtime-1MBQrzb8` | Düz zemin smoke: canlı sensörler geldi; Gazebo kapanışında -11 logu var. |
| `t3-runtime-1qxHz434`, 13:36:20–13:38:29 UTC | Gerçek BXW, teslim model, GUI kapalı: status 4, fiziksel hareket 9,473051 m, hedef hatası 0,503527 m, z artığı 0,015058 m. Programatik hedeftir. Inflation uyarısı sonraki değişiklikle geometriye bağlandı. |
| Aynı koşunun `perception.json` kaydı | Scan, altı wheel joint, costmap'ler ve plan canlı. Geçerli LiDAR dönüşü 0; düşük kaya algısı kanıtlanmadı. |
| `t3-runtime-qjvsuibc`, 13:42:20 UTC bitiş | 5 m ileride SCENARIO 1×1×3,5 m test engeli: hedef kabul edildi, action status 6, sürüş başarısız. Probe bitmeden kapandığından boş log algı kanıtı değildir. |

Sonraki iş: engelli koşunun planner/costmap reddini incelemek; sensör dönüşü,
işaretlenen hücre, yeniden rota, fiziksel açıklık ve durmayı ayrı ölçmek.
Yüksek tek düzlemli 2D LiDAR alçak kaya algısı/3D zemin ayrımı sağlamaz.
Eski RViz hedef kabulü bu açıkları kapatmaz.

Kullanıcının COPY MODE isteği üzerine süreçler kontrol edildi; başka etkin
uygulama işi yoktu ve test kapanmıştı. `wsl --shutdown` uygulandı;
`wsl --list --running` çalışan dağıtım olmadığını doğruladı. WSL yeniden
başlatılmadı. Git/GitHub, T2/core ve kaynak assets değişmedi; kredi harcanmadı.

## WSL yeniden açıldıktan sonra — 14 Kasım 2026

Engelli koşunun nedenleri ayrı kontrollerle incelendi. 4 m global hücreye
boyanan 1 m engel, footprint'i erken bloke ediyordu (`HNX9mTqE`: kenar 254,
merkez 0). Teslim profili 80 m / 0,2 m hareketli master kullanıyor; gerçek
statik DEM desteği 4 m olarak korunuyor. Eski 4 m dönüş yarıçapı bu kaba
hücre zorunluluğuydu; yedek profilinin v/omega oranı 1 m.

Ara rota denetimi footprint kenarındaki 253 maliyetini gerçek engel sayıp
inflation'ı iki kez uyguluyordu (`61bayQFq`). Kurulu Nav2 sürümüyle aynı
anlam düzeltildi: merkez >=253, kenar >=254; bilinmeyen ve harita dışı hâlâ
reddediliyor. Ayrımı koruyan C++ regresyon testi eklendi.

Düz zemin ile gerçek DEM birbirinin kabulü olarak kullanılmadı. Torku
tek başına artıran ilk deneme dönüşü düzeltmedi; o nedensel açıklama yeterli
değildi. Yönlü sürtünme, gerçek gövde frame'i ve tekerlerin temasını ayrı
inceledik. Sanat pivotlarındaki yaklaşık 3 mm yükseklik farkı katı yedekte
istenmeyen yük dağılımı yaratabiliyor; teker dönmesi, gövde dönüşü kanıtı değil.

Son fizik yedeği 6 pasif düşey taşıyıcı kullanıyor; yay 10.000 N/m, sönüm
1.000 Ns/m, hareket -0,08 / +0,12 m, her taşıyıcı 1 kg. Toplam 899 kg
korundu. Frame orta aks üzerinde; nominal CG ve collision kutusu buna göre
ofsetlendi. Yanal/boyuna mu 0,5 / 1,0 ve tork tavanı 444,697 Nm SCENARIO'dur.
Bunlar NASA mekanik ölçümü veya gerçek rocker-bogie portu değildir.

- `t3-runtime-TiSy4OGe`, 14:44:06 UTC: gerçek DEM, yerleşme sonrası 8 s
  dönüş komutu; **1,507443 rad fiziksel dönüş / 0,026251 m merkez kayması**,
  kabul geçti. 12 joint state içinde 6 taşıyıcının gerçek hareketi var.
- `t3-runtime-xtX5PGr2`, 14:47:38 UTC bitiş: gerçek engelli Nav2 sürüşü
  ilerleme denetiminde başarısız. Bu sonuç başarılı dönüşle örtülmedi.
- Sonraki profil: ölçülen dönüşü ilerleme sayan PoseProgressChecker ve önce
  rotaya hizalanıp MPPI'ye geçen RotationShimController. BT'ye Spin/BackUp
  eklenmedi; komut zinciri tek controller_server üzerinden korunuyor.
- `t3-build-O4OveYkh`: 70 test kaydı (61 case + 9 CTest wrapper), 0 hata,
  başarısız veya atlanan. Testler domain 78 / ayrı partition, canlı koşu 77.
- `scripts/tests/test_t3_clearance_analysis.py`: 3 analitik geometri kontrolü
  geçti. Planar örnek analizi sürekli çarpışmasızlık veya donanım güvenliği
  kanıtı değildir.

`QQWvOR9I` sırasında test yayıncısı canlı domain'e karıştığından o koşu
geçersiz sayıldı (`VALIDITY.json`). Test domain'i ayrıldı; başarısız test ve
ham sürüş dosyaları korundu. COPY MODE uyarısı restart sonrası da göründü;
CUA yanlış yüzeyi yakaladığı için yeni RViz görsel kabulü verilmedi. Gazebo
sensor/physical verisi doğrudan kaydedildi. Bazı kapanışlarda D3D12/Gazebo
-11 veya bounded -9 logu var; parent exit 0 temiz Gazebo kapanışı anlamına
getirilmiyor.

## 20:45 (+03:00) son kayıt

T4 teknik kabulü son ana ajan doğrulamasıyla tamamlandı; son C++ kaynak
üzerinde 9 otomasyon, 72 canlı aktör ve 65 offline eşleşme geçti. Kaynak
snapshot durumunun invalid gelmesi artık aktörü durdurur; gerçek ROS ve UE
regresyonu vardır. [T4 kabul](../../docs/verification/T4_ACCEPTANCE.json).

T3'e isteğe bağlı 3D LiDAR eklendi. Saf core ground.py; hash doğrulanmış
ASCII kopya; ROS adapter frame/damga/tekrar kontrolü yapar. İlk tek düzlem
sürümünde doğal araziyi yanlış işaretleyen sonuçlar saklandı. Yerel yüzey
uyarlaması sonrası sabit alçak kutudan 44 dönüş / 18 geçerli bulut görüldü;
2D tarama bu koşuda sıfır dönüş verdi. [3D sonuç](../../docs/verification/T3_3D_PERCEPTION.json).
Alçak engelli tam rota hâlâ geçmedi; başarısız sonuç örtülmedi. Varsayılan
MPPI yüksek-engel kabulü korunur, 3D seçenek deneysel kalır. Son ROS build
76 kayıt; son tüm core regresyonu 263 test hatasız. Gazebo kapanışında -9/-11
sorunu ayrı açık; kullanıcıdan tekrar WSL kapatma talebi gelmedi, WSL açık.
