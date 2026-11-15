# Hızlı yolculuk: süre ve sarf sözleşmesi

15 Kasım 2026, 11:52 (+03:00) · Kod incelemesi / uygulama önerisi.

Hızlı yolculuk henüz uygulanmadı. İlk sürüm, ROS'un hesapladığı yürüyüşü
PET üzerinde oynatmalı; Unreal bu yürüyüşün görüntüsünü kısaltabilir. Hedefe
doğrudan poz verip sonradan PET eklemek, mevcut fizyoloji modelinde yürüyüş
sarfını doğru ödemez. Bu belge DECISIONS kaydına temel olacak öneridir;
D015'in poz modunda ×1 sınırını kendiliğinden değiştirmez.

## Mevcut kodun sınırları

| Bileşen | Şu anda olan | Yolculuğa etkisi |
|---|---|---|
| `/redline/scenario/control` (`ScenarioControl`) | START/PAUSE/RESUME/STOP/LOAD var; SEEK açıkça reddediliyor. `time_scale` istekte bulunsa da handler bunu uygulamıyor. | İstemci SEEK veya isteğin scale alanına güvenemez. |
| `sim_clock` | `/redline/mission/clock` yayımlar; `time_scale` ve `running` parametrelerini kabul eder. Gazebo `/clock`'unu okumaz/yazmaz. | Parametre çağrısı yalnız saat mekanizmasıdır; güvenli yolculuk işlemi değildir. |
| `ev_sim`, `motion=pose` | Hız/eğim, UE pozlarının duvar zamanı penceresinden; sarf, PET farkından hesaplanır. | Pozu sabit tutup PET hızlandırmak dinlenme sarfı ödetir; ışınlanma da gerçek yürüyüş hızı olarak ölçülemez. |
| `ev_sim`, `motion=plan` | ROS tek poz yayıncısıdır; yol ve fizyoloji PET üzerinde yürür. İkinci poz yayıncısını reddeder. | Başsız test için uygun temel; UE'nin mevcut poz yayınıyla birlikte açılamaz. |
| Oyun kampanyası | `campaign.launch.py` saat, hücre, walkback, ekip, bilim ve scout başlatır; scenario_player/RAD/rule_monitor bu launch içinde yoktur. | Bu kampanyada alarm güvenliği hazırmış gibi hızlı yolculuk açılamaz. |
| Yeni istasyonlar | Atlas habitatı `(290,-454)` m, mevcut EVA spawn/habitatıyla aynı. | Koordinat orijini uyuşuyor. Ancak mevcut saha profili `BXW_RIDGE_A/HOLLOW_B` ve 280–430 m bölüm rotalarını kullanıyor; atlasın T01/T05/T08/T09/T10 istasyonları ayrı tasarımdır. |

Atlasın statik dönüş konturu EVA başına aittir. Canlı karar, güncel ekip
kaynakları ve walkback alanından gelmelidir. ST-H dışındaki atlas duraklarının
başlangıç Tε değeri 20 dakikalık SEP sınırını aşar. Kısa video bu durakları
güvenli yapmaz; basınçlı rover/sığınak planı yoksa insan yolculuğu reddedilir.
ST-W3 zaten yalnız robot durağıdır.

## Önerilen ilk uygulama

Donmuş bilim action'ları değişmez. Ayrı, iptal edilebilir
`TraverseCrew.action` ve `/redline/crew/traverse` uç noktası eklenir
(**önerilen adlar; şu anda mevcut değiller**). İstek `run_id`, `request_id`,
`crew_id`, `station_id`, beklenen kampanya revision ve rota/alan sürümünü taşır.
Yanıt kabul; feedback ilerleme; result tamamlanma/iptal/başarısızlık demektir.
Yolculuk bir bilim görevini tamamlamaz.

1. ROS güncel insan pozunu, PET'i, kaynakları, bilinen hücreleri ve alarm
   zincirini doğrular. İstasyon atlas kimliğiyle çözülür; istemciden serbest
   koordinat, süre veya sarf kabul edilmez. Aktif robot navigasyonu/bilim
   işlemi varsa ilk sürüm yolculuğu reddeder: robot fiziği gerçek zamanda kalır.
2. Çekirdekte `leg_path` ile güncel pozdan hedefe yol bulunur;
   `timed_path_from_cells` / `edge_cost` ile her kenarın yönlü yürüyüş süresi
   hesaplanır. Eve dönüş yolunu ters çevirmek, gidiş süresini vermez. Yolun
   tamamında kaynak rezervleri, dönüş ve SEP/sığınak koşulları denetlenir.
3. ROS bir yolculuk kimliğiyle insan kontrolünü alır. İlk teknik kabulde
   `ev_sim motion=plan` ve ROS poz sunumu kullanılır; UE `/crew/EV1/pose`
   yayınını durdurup salt okunur izlemeye geçer. Yetki devri onaylanmadan
   PET hızlandırılmaz. Aynı ekip için iki poz yayıncısına izin verilmez.
4. Yol ve metabolizma aynı PET zaman tabanında yürür. Saat ×1'den başlayıp
   yalnız doğrulanmış üst sınıra kadar hızlandırılır. İlk deney sınırı ×5 ve
   yayın başına en fazla 0,5 PET saniyesidir (10 Hz saat; **SCENARIO test
   ayarı**, ölçülmüş güvenlik limiti değildir). Daha kısa görüntü için daha
   yüksek ölçek, alarm gecikmesi/sarf hata kabulü görülmeden açılmaz. Gazebo
   `/clock`, `cmd_vel` ve robot pozları değiştirilmez; genel SEEK kullanılmaz.
5. Yolculuk bitince saat ×1'e döner; gerçek varış pozu, PET farkı, ödenen
   O₂/su/batarya, rota/hash ve güncel dönüş payı result/DecisionRecord'a
   yazılır. ROS poz sahipliğini bırakıp onay verir; UE bu son pozda manuel
   sahipliği geri alır. Video atlamak yalnız sunumu atlar, varış üretmez.

Bu ilk kabulden sonra manuel/plan poz sahipliğini çalışma anında devreden
bir mod eklenebilir. Mevcut `ev_sim` modları başlangıçta sabit olduğundan,
servis veya kontrollü durum makinesi eklenmeden düğümleri art arda açıp
kapamak yolculuk API'si sayılmaz. Kaynaklar egress başlangıcına sıfırlanamaz.

## Kesilme ve tekrar çağrı

SEP, giysi kaçağı, engellenen yol, eski telemetri veya bağlantı kaybında
hızlandırma ×1'e iner; yolculuk son doğrulanmış rota noktasında kesilir.
Geçen PET ve tüketilen kaynaklar geri verilmez. Dönüş kararı güncel alandan
yeniden hesaplanır. Bağlantı yokken güvenlik düğümleri ROS'ta çalışmayı sürdürür;
UE sonucunu tahmin edip ışınlanamaz.

Kalıcı request kaydı `(run_id, request_id)` ve istek özetine bağlanır. Aynı
istek mevcut işlemi/sonucu döndürür; farklı yük aynı kimlikle reddedilir.
Yeniden bağlantı yalnız durum sorgular, yürütmeyi tekrar başlatmaz. Saat
kontrolü tek ROS sahibinde kiralanır; çökme/lease süresi dolması ×1'e dönmeyi
sağlar. Diğer oturumun veya bağımsız scenario_player'ın saat yazması çatışma
olarak görünür ve hızlandırma başlamaz.

## Açılmadan önce kabul kanıtı

| Deney | Beklenen gözlem |
|---|---|
| Aynı eğimli rota ×1 ve ×5 | Aynı son nokta; PET ve her kaynak farkı, önceden kaydedilen sayısal tolerans içinde. |
| Gidiş/dönüş eğimi farklı rota | Süre ve sarf yönlü kenar maliyetleriyle uyuşur. |
| Rota ortasında SEP/kaçak/engel | Varış yok; kesilme konumu/ödenen PET kalıcı; hız ×1; güncel dönüş kararı. |
| UE kopması, yeniden bağlanma, kopya istek | İkinci tüketim/ikinci yolculuk yok; son doğrulanmış durum geri gelir. |
| Poz sahibi devri / gecikmiş callback | Aynı anda tek `/crew/EV1/pose` sahibi; eski callback yeni işlemi ilerletmez. |
| Saat sahibi çökmesi | Hızlandırma süresiz kalmaz; fizik `/clock` kesintisiz ve aynı hızda. |
| Atlas ST-W3 veya SEP açısından desteksiz durak | İnsan yolculuğu açık gerekçeyle reddedilir. |

Kod ve canlı kabul kaydı olmadan bu özellik tamamlandı veya aktif denmez.

## İncelenen kaynaklar

- [D015](DECISIONS.md), [proje.md §4 ve §18](proje.md), [istasyonlar ve görev kartları](BILIM_GOREVLERI.md).
- [ScenarioControl](../ros_ws/src/redline_msgs/srv/ScenarioControl.srv), [scenario_player](../ros_ws/src/redline_env/redline_env/scenario_player.py), [sim_clock](../ros_ws/src/redline_env/redline_env/sim_clock.py).
- [ev_sim](../ros_ws/src/redline_crew/redline_crew/ev_sim.py), [PET yol çizelgesi](../python/redline_core/src/redline_core/plan_follow.py), [saat aritmetiği](../python/redline_core/src/redline_core/mission_clock.py).
- [Kampanya launch](../ros_ws/src/redline_planner/launch/campaign.launch.py), [saha yerleşimi](../scripts/prepare_campaign_runtime.py), [EVA runtime](../data/engines/BXW/eva-runtime-v1.json), [atlas manifesti](../data/engines/BXW/tablet-atlas-v1/manifest.json).
