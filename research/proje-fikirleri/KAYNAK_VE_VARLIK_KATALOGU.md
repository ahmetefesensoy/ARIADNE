# REDLINE — Veri, yazılım, görsel ve ses kataloğu

14 Kasım 2026 · Proje kılavuzunun kaynak eki · “Aday” girdiler indirilmiş, uyarlanmış veya çalışır kabul edilmez. Kaynak kontrollerinin tarihleri ilgili araştırma kayıtlarında korunur.

Kod, ROS–Unreal, 3D üretim ve bilim çalışmasında kullanılacak skill'ler ayrıca
[skill planında](SKILL_PLANI.md) listelenir. 17 dış kaynak skill ve 1 proje skill'i
`.agents/skills` altında mevcut; skill kurulumu editör/MCP veya runtime paketi kurulumu değildir.

[Ana kılavuz](PROJE_KILAVUZU.md) görevlerin davranışını açıklar. Bu katalog, her görev için hangi gerçek veri/araç/varlığın alınabileceğini ve hangi işi kendimizin yapacağını gösterir. Aynı görevden iki ürün kullanmak iki NASA görevi kullanmak değildir. Varlığın ücretsiz olması açık yeniden dağıtım hakkı demek değildir.

Space Apps'in yayımlanan kaynakları için [14 Kasım incelemesi](../../research-notes/SPACE_APPS_2026_VERI_KAYNAKLARI.md): kaynak listesi duyurusu doğrulandı; resmî Mars Resources sekmesine erişim hatası sürdüğü için beş bağlantı organizatör kopyasından, araç özellikleri üretici sayfalarından kontrol edildi. Yeni tek bir Mars veri paketi doğrulanmadı.

## 1. Gerçek bilim ve harita verileri

Durum kodları: **Yerel** dosya/metadata mevcut; **Aday** ürün ailesi doğrulandı, tekil ürün seçimi açık; **Referans** farklı yer/zamandan eğitim veya yöntem örneği, seçilen sahanın gerçek ölçümü değil.

| ID | Ürün ve erişim | Görevde kullanımı | Durum, kapsam ve işleme |
|---|---|---|---|
| D01 | [Gale DEM v3](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m), `MSL_Gale_DEM_Mosaic_1m_v3.tif` | Saha geometrisi, eğim ve görüş hesabı; Görev 1/5 | Yerel 2×2 km kırpım ve 4 m görsel/fizik ağı var. Kaynak 1 m grid karışık çözünürlüklü girdiler içerir; ayak/teker ayrıntısı değildir. HiRISE/CTX, HRSC ve MOLA kökenleri provenance'da korunur. |
| D02 | [Yerel Gale LRGB kaynağı](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_HiRISE-LRGB_78quads_sharp_cog.tif) | Yerle eşleşmiş yörünge görüntüsü; habitat haritası ve arazi dokusu | Yerel kırpım var. Renk mineral/çekiş sınıfı değildir. Ayrı [25 cm ortofoto v3](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_orthophoto_mosaic_25cm) ürünüyle aynı dosya sayılmaz. |
| D03 | [MSL PLACES](https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/), `localized_pos.csv`, `localized_interp.csv` | Rover konumu, sol/site/drive ve hedef ilişkisi | Önceki v42.0 sorgusunda mevcut AOI'de konum örneği yok. Görüntünün baktığı alan ayrıca doğrulanır. Yeni bilim AOI'si seçilmedi. |
| D04 | [MSL Navcam RDR](https://pds.nasa.gov/ds-view/pds/viewProfile.jsp?dsid=MSL-M-NAVCAM-5-RDR-V1.0) ve [Analyst's Notebook](https://an.rsl.wustl.edu/msl/mslbrowser/) | Gerçek yer görünümü, bilim durağında karşılaşılacak bağlam | Aday. Tekil ürün, kamera modeli, poz, sol ve ayak izi seçilecek. Görüntüde görülen uzak hedef çekim konumuyla eşitlenmez. |
| D05 | [Curiosity APXS](https://pds-geosciences.wustl.edu/missions/msl/apxs.htm) | Görev 2'de kaynaklı element/oksit karşılaştırması | Aday; hedefe bağlı RDR/spektrum/tablo seçilecek. RGB'den üretilmiş kimya gibi sunulmaz. |
| D06 | [Curiosity CheMin](https://pds-geosciences.wustl.edu/missions/msl/chemin.htm) | Görev 2/3 mineral/XRD incelemesi, numune hazırlığı ve yorum | Aday. John Klein/Cumberland veya Gobabeb gibi gerçek örneklerle kaynak bağı gerekir; yeni senaryo numunesi aynı gerçek ölçüm değildir. |
| D07 | [Curiosity SAM](https://pds-geosciences.wustl.edu/missions/msl/sam.htm) | Atmosfer veya ısıtılmış katı örnek için ayrı gaz/ucuçu analiz işlemi | Aday/referans. Atmosfer profili, katı ısıtma sonucu ve habitat kaçağı aynı veri değildir. |
| D08 | [MSL REMS](https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/MARS/curiosity/rems.html), `MSL-M-REMS-5-MODRDR-V1.0` ailesi | Gale çevre zaman serisi; kontrol merkezi ve Görev 5 | Aday. Kalite bayrakları, örnek zamanı ve yer bilgisi korunur; tarihsel kayıt tüm sahada canlı hava sayılmaz. |
| D09 | [MSL RAD](https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/) | Radyasyon arşivi ve açık varsayımlı senaryo karşılaştırması | Aday. Counts, doz ve insan maruziyeti farklı büyüklüklerdir; uygun alt ürün/model olmadan dönüşüm yapılmaz. |
| D10 | [THEMIS gece IR](https://mars.asu.edu/data/thm_nir_100m/), [gündüz IR](https://mars.asu.edu/data/thm_dir_100m/) | Odyssey'den bölgesel bağlam; çoklu NASA görev verisi | Aday; yaklaşık 100 m ürünler. Tile geçerliliği/no-data ve nicel ürün seçimi açık. Browse rengi sıcaklık/termal atalet değildir. |
| D11 | [MOLA MEGDR](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html) | Bölgesel topoğrafya ve veri kökeni; gerektiğinde karşılaştırma | Aday. 128 ppd yaklaşık 463 m ekvator ölçeği; yerel yürüyüş engeli katmanı değildir. |
| D12 | [Phoenix MECA/WCL](https://pds-geosciences.wustl.edu/missions/phoenix/meca.htm), [ıslak kimya işlemi](https://www.jpl.nasa.gov/images/pia10915-phoenixs-wet-chemistry-lab/) | Görev 2 pH/iyon/iletkenlik prosedürüne referans | Referans; Phoenix konumu Gale/Jezero değildir. Toprak–su hazırlığı ve laboratuvar hücresi modellenir. Global pH haritası üretilmiş sayılmaz. |
| D13 | [Mars 2020 MEDA kalibre çevre koleksiyonu](https://pds.nasa.gov/ds-view/pds/viewCollection.jsp?identifier=urn%3Anasa%3Apds%3Amars2020_meda%3Adata_calibrated_env) | Jezero alternatif kampanyası ve cihaz referansı | Referans/adaya göre. Gale'e gerçek eşzamanlı ölçüm olarak taşınmaz; solar/IR verisi RAD iyonlaştırıcı radyasyonuyla aynı değildir. |
| D14 | [Mars 2020 Sample Dossier](https://pds-geosciences.wustl.edu/missions/mars2020/returned_sample_science.htm), `urn:nasa:pds:mars2020_sample_dossier` | Numune hedefi–görüntü–bilim gerekçesi ve kayıt tasarımı | Referans/Jezero adayı. Ayrıntılar tekil rapor/sürümden alınır; hayalî örnek kabına gerçek NASA numunesi kimliği verilmez. |
| D15 | [AI4Mars NASA kataloğu](https://data.nasa.gov/dataset/ai4mars-a-dataset-for-terrain-aware-autonomous-driving-on-mars), [özgün yayın](https://openaccess.thecvf.com/content/CVPR2021W/AI4Space/papers/Swan_AI4MARS_A_Dataset_for_Terrain-Aware_Autonomous_Driving_on_Mars_CVPRW_2021_paper.pdf) | Arazi görüntü sınıflandırması eğitimi/karşılaştırması | Eğitim verisi; seçilen AOI'nin hazır risk haritası değildir. Sürüm, lisans, maskeler/test ayrımı ve Unreal görüntüsüne aktarım incelenecek. Tam arşiv indirilmedi. |
| D16 | [NAIF SPICE](https://naif.jpl.nasa.gov/naif/) | Saat/konum/aydınlanma ve gözlem geometrisi | Araç + kernel girdileri. Yerel gölge için DEM görüş hesabı ayrıca gerekir; bir kernel bütün çevreyi ölçmez. |
| D17 | [NASA Mars Trek WMTS](https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars) | Habitat/tablet haritasında kaynaklı görüntü katmanları | Servis doğrulandı; tekil ürün/kapsam ve gerçek tile akışı denenmedi. WMTS görüntüsü fizik için sayısal DEM değildir; servis ayrı bir NASA görevi sayılmaz. |
| D18 | [Cesium Mars](https://cesium.com/platform/cesium-ion/content/cesium-mars/), [Unreal öğreticisi](https://cesium.com/learn/unreal/unreal-moon-mars/) | Gerçek Mars verisiyle 3D çevre görüntüleme alternatifi | Aday; Gale için yaklaşık 1 m arazi/25 cm görüntü belirtiliyor. Mars elipsoidi, mikro-saha kapsamı, ion erişimi, dağıtım ve ortak Gazebo geometrisi kontrol edilecek. Eklenti/veri kurulmadı; Space Apps'in yeni paketi diye sunulmaz. |

İlk hedef veri birleşimi D01/D02 + D03/D04 ve kampanyaya uygun D05/D06 + uygun D10'dur. D10 ancak gerçek göreve anlam katıyorsa kullanılır; katman sayısı için eklenmez. Güncel challenge Resources listesinden en az bir NASA kaynağının gerçekten kullanıldığının teslim öncesi kontrolü ayrıca yapılır.

Yerel D01/D02 dosyaları `önceki deneme/ros2_ws/src/redline_mars_sim/models/gale_real/meshes/gale.dae` ve aynı dizindeki `orbital_texture.jpg`. Provenance (bu depoya dahil edilmedi) kaynak URL'leri, hash'leri, 2×2 km AOI sınırını, yerel orijini ve yaklaşık 4 m ağ aralığını içerir. Gale kaynak açıklaması (bu depoya dahil edilmedi) ve [AOI kesişim incelemesi](../../research-notes/Gale_PLACES_AOI_KONTROLU.md) birlikte okunur. “Yerel” bu kayıt/dosya varlığını belirtir; yeni bilim kampanyasının doğrulandığını söylemez.

Veri işleme: PDS etiket/kalibrasyonunu oku → tekil ürün seç → yer/zaman/CRS eşle → no-data ve kaliteyi koru → kırp/yeniden örnekle → türetilmiş katmanı ve kaynak zincirini kaydet → Unreal/Gazebo için paketle. Çıktı gridini sıklaştırmak yeni ölçüm ayrıntısı yaratmaz.

14 Kasım somutlaştırması: [saha ve bilim istasyonu kaydı](../../research-notes/SAHA_VE_BILIM_ISTASYONU.md) D05 için iki Yellowknife ve iki Gobabeb APXS satırını, D06 için iki CheMin ürününü ve MRO `PSP_010573_1755_RED` v2.0 label kontrolünü içerir. Yellowknife satırları ürünün sayısal kutusunda, Gobabeb satırları dışındadır; koordinat/piksel QA hâlâ gereklidir. D12 için gerçek WCL koleksiyonu `urn:nasa:pds:phx_meca:data_wcl::1.0`, parent DOI `10.17189/1518770` doğrulandı. Gale pH çıktısı gerçek arşiv yerine tanımlı simülasyon analizi olacaktır.

## 2. Hazır 3B varlıklar ve kendi üreteceklerimiz

| ID / kaynak | Kullanım | Hazır olmayan iş / hak durumu |
|---|---|---|
| A01 · [NASA Perseverance](https://science.nasa.gov/3d-resources/mars-2020-perseverance-rover/) | Rover görünümü, cihaz/kol yerleşimi referansı | GLB/Blender dosyası robot description değildir. Eklem, rig, collision, kütle/atalet ve denetleyici ayrıca hazırlanır; NASA/JPL kredisi korunur. |
| A02 · [NASA Ingenuity](https://science.nasa.gov/3d-resources/ingenuity-mars-helicopter/) | Scout görünümü veya tasarım referansı | NASA/Brian E. Kumanchik kredisi. Rover üstü geri iniş, şarj ve uçuş aerodinamiğini sağlamaz. |
| A03 · [NASA Astronaut](https://science.nasa.gov/3d-resources/astronaut/) | Astronot/kıyafet referansı veya izin uygunsa görünüm | DigitalSpace Corporation kaynaklıdır; NASA sitesinde olması otomatik public-domain/rigli/Mars giysisi geçerliliği sağlamaz. Kullanım koşulu netleşmeden ana dağıtıma alınmaz. |
| A04 · [Poly Haven](https://polyhaven.com/license) | Kaya, taş/metal yüzeyleri ve laboratuvar/garaj malzeme adayları | Varlıklar CC0; tekil seçimi/hash kaydedilir. Dünya taraması, Mars'taki gerçek taş konumu değildir. HDRI gerçek Mars göğü sayılmaz. |
| A05 · [Kenney Space Kit](https://kenney.nl/assets/space-kit) | Habitat, iniş/araç blokları ve erken görev nesneleri | CC0; stilize bloklama. Bilimsel habitat veya fotogerçekçi bitmiş iç mekân kabul edilmez. |
| A06 · [Quixel Megascans](https://quixel.com/news/update-megascans-are-going-free-again), [Fab koşulları](https://www.fab.com/eula) | Koşullu yüksek kalite kaya/zemin alternatifi | 5 Kasım duyurusu ücretsiz erişimi bildiriyor; Standard lisans ham varlığın bağımsız açık dağıtımını sağlamaz. Fiyat ile lisans farklıdır. Public çözüm uygunluğu ayrıca açık kalır. |
| A07 · [Epic Third Person Template](https://dev.epicgames.com/documentation/en-us/unreal-engine/third-person-template-in-unreal-engine) | Giriş/hareket/kamera ve örnek animasyon altyapısı | Epic lisansı; açık CC0 karakter paketi değildir. Giysi ve Mars hareket modeli ayrıca tasarlanır. |
| A08 · [Epic IK Retargeting](https://dev.epicgames.com/documentation/unreal-engine/ik-rig-animation-retargeting-in-unreal-engine?lang=en-US) | Uygun rigden astronot animasyon aktarımı | Rig/kemik eşleme gerekir; dönüşüm başarı ve ölçek kontrolü yapılmadan hazır sayılmaz. |
| A09 · Kendi modüler Blender habitat kiti | Duvar, zemin, ekran çerçevesi, kapı/airlock, boru, garaj pad'i | Ana açık görsel paket için öneri. Ölçüler konsept tasarımdır; gerçek habitat mimarisi doğrulaması iddiası kurulmaz. |
| A10 · Kendi görev nesneleri | Vana/kol/çark, drill/bit, kepçe/gripper, numune kabı, kontrol işareti | Her işlevsel parçanın pivotu, hareket sınırı ve Gazebo counterpart'ı gerekir. |

NASA varlıklarında sayfa kredisi ve üçüncü taraf durumu ayrı kontrol edilir. [NASA medya kullanım rehberi](https://www.nasa.gov/nasa-brand-center/images-and-media/). NASA onayı veya resmî eğitim ürünü izlenimi verilmez. AI üretim varlığı kullanılacaksa marka ve AI açıklama kuralları ayrıca uygulanır.

### Üretim brief'i ve aktarım

Hedef PC masaüstü görev simülasyonu; görsel dil okunabilir, gerçekçi malzeme ve bilimsel bağlamdır. Öğretim ekranlarında okunurluk sinematik efektin önündedir. Ana varlıklar rover/kol, drone, astronot ve vana; standart varlıklar habitat, kaplar ve cihazlar; arka plan varlıkları kaya/dekordur.

İlk üretim bütçesi bir tasarım hedefidir: ana robot görselinde yaklaşık 50–150 bin üçgen, standart işlevsel prop'ta 2–15 bin, kaya örneğinde 1–10 bin; basit collision çok daha düşük olur. Ana varlıkta 2K–4K, küçük nesnelerde 1K–2K doku başlangıç aralığıdır. Bunlar ölçülmüş optimum değildir; hedef kare süresine göre değişir. Nanite bu fizik/eklem/bellek işlerini ortadan kaldırmaz.

Blender: metre ve ölçü referansı → silhouette/modüler blockout → doğru pivot/eklem → malzeme/UV → geometri/LOD/material bütçesi → collision proxy → statik/skeletal export → Unreal'da bilinen kenarı cm olarak ölç → Gazebo pozu/eklemiyle eşleştir. FBX/GLB seçimi varlığa göre yapılır; motor ayarını körlemesine sabitlemek yerine bir metre test küpü ve dönüş yönleriyle doğrulanır.

İsim önerileri: `SM_` statik, `SK_` skeletal, `M_` malzeme, `T_` doku, `BP_` aktör, `WBP_` ekran, `UCX_` collision. `BP_ValveStation`, `BP_SampleCabinet` gibi adlar planlanan Unreal varlıklarıdır; bugün dosya olarak mevcut değiller.

## 3. Unreal özelliklerini hangi işte kullanacağız?

| Özellik | REDLINE işi | Sınır |
|---|---|---|
| [UMG / Widget Components](https://dev.epicgames.com/documentation/unreal-engine/widget-components-in-unreal-engine?lang=en-US) | Habitat ekranları, tablet, plan/ölçüm karşılaştırması ve odak 2B görünüm | Aynı veri modellerini kullanır; ekran görüntüsü kopyası değildir. |
| Enhanced Input | Astronot, rover, drone kontrol profilleri | ROS kontrol sahipliği ayrıca yönetilir. |
| Anim Blueprint / IK / Control Rig | Astronot yürüme/etkileşim ve uygun mekanik görseller | Robotun fiziksel eklem gerçeği ROS'tan gelir; iki otorite kurulmaz. |
| [PCG](https://dev.epicgames.com/documentation/en-us/unreal-engine/procedural-content-generation-overview) / instancing | Kaya/dekor yerleşimi | Görevi etkileyen nesne manifestle Gazebo'ya da aktarılır; dekor ölçüm sayılmaz. |
| Statik mesh / Landscape | Doğrulanmış DEM tabanlı saha | İlk tercih ortak geometrinin eşleşmesini kolaylaştırır; tüm gezegen fizik ağına yüklenmez. |
| Nanite / LOD | Görsel yük yönetimi | Uygun statik varlıkta; collision, animasyon ve VRAM bütçesini ayrıca yönetiriz. |
| Niagara | Düşük yoğunluklu toz ve araç etkileri | Bir gaz kaçağını görünür renkli bulut çizmek fiziksel doğrulama değildir. |
| [MetaSounds](https://dev.epicgames.com/documentation/unreal-engine/metasounds-the-next-generation-sound-sources-in-unreal-engine?lang=en-US) | Drill yükü, motor, fan ve alarmdan veri güdümlü ses | Ham kayıtların hakkı ve ses modelinin temsili ayrıca tutulur. |
| Sequencer | Kısa açılış ve görev sonrası kayıt sunumu | Canlı simülasyon sonucu önceden hazırlanmış sinematikle değiştirilmez. |
| Data Assets / Data Tables | Görev, örnek, cihaz ve ekran tanımları | Gerçek görev otoritesi ve ROS sonucu ayrı; veri sürümleri eşleşir. |

Dokümanlar güncel varsayılanda UE 5.9'a yönlenebilir; uygulanacak API/özellik 5.8.4 kurulumunda kontrol edilir. Çalışan ürün içinde Python için Editor Script Plugin'e dayanılmaz.

## 4. Ses kaynakları ve görev sesleri

- [NASA Sounds of Mars](https://science.nasa.gov/mission/mars-2020-perseverance/sounds-of-mars/) ve [Perseverance mikrofon kaydı](https://science.nasa.gov/resource/nasas-perseverance-rover-microphone-captures-sounds-from-mars/): kaynaklı arşiv dinleme ve referans. Kayıt yeri/tarihi/cihazı korunur; loop/edit işlenmiş ambiyans diye belirtilir.
- Habitat fanı, vana, gripper, drill ve UI sesleri: kendi kayıtlarımız veya lisansı açıkça uygun ham sesler. MetaSounds hız/yük/bağlantı durumuna göre bunları işler.
- Görev durumu ve alarmlar metin/görsel karşılık taşır; ses tek bilgi kanalı değildir. Konuşmalı danışman ve TTS/ASR bağımlılığı kapsamda bulunmaz.
- Arşiv, fizik temsili, telsiz efekti ve eğitim uyarısı sesleri farklı içerik türleri olarak kayıtlanır. Dünya fırtınası veya patlama sesi gerçek Mars ortamı diye sunulmaz.

## 5. Repo ve mühendislik araçları

| Kaynak | Ne için alınabilir? | Uyumluluk/lisans notu |
|---|---|---|
| [rosbridge_suite](https://github.com/RobotWebTools/rosbridge_suite) | ROS topic/service ile Windows UE arasında ilk WebSocket/JSON köprü | BSD-3-Clause; Jazzy `ros2` dalı. UE istemcisi bizim işimiz; yüksek hacimli sensör için ayrı strateji gerekir. |
| [Nav2 Jazzy](https://github.com/ros-navigation/navigation2/tree/jazzy) | Planlama, kontrol, BT ve Collision Monitor | Paket lisansları ayrı kontrol edilir; depo tümüyle tek Apache diye etiketlenmez. Mars arazi/çok araç görev planı kendiliğinden hazır değildir. |
| [MoveIt 2](https://github.com/moveit/moveit2) | Kol planlama, sahne ve Servo | Ana lisans BSD-3-Clause; Jazzy/config sabitlenir. Temas/tork/delme modeli ayrıca gerekir. |
| [gz_ros2_control](https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html) | Gazebo eklemlerini ros2_control ile bağlama | Jazzy/Harmonic yolu belgeli; mevcut native diff-drive çalışan demosunu zorunlu olarak hemen değiştirmeyiz. |
| [JPL Open Source Rover](https://github.com/nasa-jpl/open-source-rover), [OSR kodu](https://github.com/nasa-jpl/osr-rover-code) | Mekanik/kinematik referans ve gerçek rover deneyine yol | Model/hardware ve code hakları ayrı kaydedilir. Kodun Foxy/Classic geçmişi var; Jazzy/Harmonic'e doğrudan takılmaz. |
| [space-ros/demos](https://github.com/space-ros/demos) | Curiosity arazi ve Ogma runtime monitor referansı | Kök Apache-2.0; alt model hakları ayrıca. Mevcut sistemle hazır sürüm uyumu varsayılmaz. |
| [Open MCT](https://github.com/nasa/openmct) | Canlı/geçmiş telemetri ve bilim operasyon görünümü | Apache-2.0; ROS veri provider'ı ve Unreal bağlantısı ayrı geliştirilecek. |
| [Foxglove ROS 2 bridge](https://github.com/foxglove/foxglove-sdk/blob/main/ros/src/foxglove_bridge/README.md) | Mühendislik gözlemi için isteğe bağlı alternatif | Güncel SDK'daki köprü MIT ve Jazzy build yolu bildiriyor. Eski ROS1 deposuyla karıştırılmaz; aynı işi yapan her aracı birlikte eklemek gerekmez. |
| [PlotJuggler](https://github.com/PlotJuggler/PlotJuggler), [rosbag2](https://github.com/ros2/rosbag2) | Zaman serisi ve görev/sensör kayıt inceleme | Seçilen sürüm ve eklenti lisansları korunur; replay alternatif fizik sonucu üretmez. |
| [OpenCV ArUco](https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html) | İşaretli vana/pad kimliği ve poz tahmini | Kamera kalibrasyonu, fiziksel boyut ve görüntü gerekir; işaret kapalı vana/kaçak kanıtı değildir. |
| [rclUE](https://github.com/rapyuta-robotics/rclUE) | Gelecekte native/Linux entegrasyon araştırması | README Windows desteklenmiyor diyor; Windows UE 5.8.4 ana yolunun bağımlılığı yapılmaz. |
| [GDAL PDS](https://gdal.org/en/stable/drivers/raster/pds.html), [QGIS](https://qgis.org/) | Gezegensel veri okuma, kırpma, hizalama ve QA | Mars CRS ve ürün etiketleri bilinçli seçilir; Earth varsayılanı kullanılmaz. |
| [Project Chrono](https://api.projectchrono.org/vehicle_terrain.html), [ns-3](https://www.nsnam.org/) | Ayrı zemin ve ağ deneyleri | Aynı rover için ikinci fizik otoritesi olmaz. Ayrı model çıktısının geçerliliği/arayüzü tanımlanır. |
| [NASA FRET](https://github.com/NASA-SW-VnV/fret), [Ogma](https://github.com/nasa/ogma) | Görev kurallarını açıklaştırma ve runtime monitor araştırması | İsim kullanmak güvence sağlamaz; küçük kuralın doğru bağlanması deneyle gösterilir. |

Mevcut `roversim27` ayrı bir çalışma ağacıdır; kirli dosyalar korunur. Yeniden kullanılacak parça, commit/yerel değişiklik ve lisans durumu kaydedilmeden yeni projeye toptan kopyalanmaz. Kaynak anahtarları kılavuzdaki modüllerle eşleşir; bu katalog hiçbir paketin şu anda kurulmuş olduğunu söylemez.

## 6. Varlık ve veri kaydı

Her girdide asgari alanlar: `id`, kaynak URL/ürün kimliği, sürüm/commit, edinme tarihi, hash, üretici/kredi, lisans/izin, değişiklikler, görev/ekran kullanımı, gerçek/senaryo/türetilmiş türü, görsel/fizik rolü ve yeniden dağıtım durumu. İndirilecek değilse neden ve alternatif kayıtlanır.

Dağıtım planı: özgün kod/görev/varlıklar uygun açık lisansla; NASA/üçüncü taraf girdiler kendi haklarıyla; kısıtlı içerik otomatik yeniden lisanslanmadan. Engine'in yazar aracı/runtime bağımlılığı ile sunulan özgün çözüm malzemesi ayrı açıklanır. Fab varlığına edinme talimatı yazmak Space Apps uygunluğunu kendiliğinden garanti etmez; resmî şartlarla açık kalan uyum konusu olarak izlenir.
