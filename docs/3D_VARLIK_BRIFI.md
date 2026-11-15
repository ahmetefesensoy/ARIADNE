# REDLINE — Claude / Tripo için 3D varlık brifi

14 Kasım 2026 · Hedef: aynı ana varlıklardan Unreal 5.8.4 görselleri ve Gazebo Harmonic robot modelleri üretmek. Kullanıcı görsel kararları Claude/Tripo ile hazırlayacak; bu belge üretim ve teslim sözleşmesidir. Burada model üretilmedi veya Tripo kredisi harcanmadı.

## Önce hangi modeller?

Önce **astronot, keşif rover'ı ve drone**. Ardından basınçlı rover, sığınak ve bilim istasyonu. EV1/EV2 için aynı astronotun iki malzeme varyantı yeterli; ikinci insan modelini baştan üretmek gerekmiyor.

| Öncelik / kimlik | İstenen varlık | Hareket edecek parçalar | İlk hedef bütçe: Unreal LOD0 / Gazebo visual |
|---|---|---|---|
| 1 · `astronaut` → EV1/EV2 | Gerçekçi yetişkin Mars EVA astronotu; tam vücut; sırt yaşam destek ünitesi; A-pose | İskeletli insan, el/parmaklar, baş; çıkarılabilir araçlar ayrı | 60–100 bin / Gazebo kinematik kapsül + opsiyonel ≤10 bin üçgen görsel |
| 1 · `rover_1` | Altı tekerli bilim rover'ı; kamera direği; ön bilim kolu | Altı teker, direksiyon mafsalları, süspansiyon, iki eksenli direk, beş eklemli kol; hepsi ayrı parçalar | 80–150 bin / 15–35 bin üçgen |
| 1 · `scout_1` | Dört rotorlu kompakt Mars keşif drone'u; aşağı bakan kamera | Gövde, dört rotor, varsa gimbal ayrı; rotor merkezleri açık | 30–60 bin / 5–15 bin üçgen |
| 2 · `pr_1` | Basınçlı keşif rover'ı; kabin, pencere, dış tutamaklar | Teker grupları ve gerekiyorsa kapı ayrı | 100–180 bin / 15–35 bin üçgen |
| 2 · `habitat` | Küçük Mars sığınağı, hava kilidi, açık giriş noktası | Kapı ayrı; ilk teslimde iç mekân şart değil | 50–100 bin / 5–15 bin üçgen veya basit çarpışma |
| 2 · `science_station` | Açılır ayaklı bilim istasyonu; sensör kutusu; iletişim anteni | Ayaklar/anten ayrı; ilk sürüm sabit kurulabilir | 15–30 bin / 3–8 bin üçgen |
| 3 · `science_tools` | APXS benzeri temas başlığı, LIBS başlığı, matkap, nötron sensörü kutusu, multispektral kamera | Bağlantı noktaları ve matkap ucu ayrı | Araç başına 5–15 bin / 1–4 bin üçgen |
| 3 · `sample_kit` | Karot/numune tüpü, kapak, taşıma kutusu, numune önbelleği | Kapak/tüp ayrı | Parça başına 2–8 bin / 0,5–2 bin üçgen |
| 3 · `rocks` | Boyut ve silueti farklı az sayıda taş varyantı | Sabit | Varyant başına 1–5 bin / 0,2–1 bin üçgen |

Bütçeler başlangıç hedefidir; ölçülmüş performans sonucu değildir. Çok detaylı tek model yerine sade LOD'lar da teslim edilmeli. İlk malzeme bütçesi: büyük araç/insan için 2K PBR; küçük araçlar için 1K; yakın çekim gereken belirli parçada 4K sonradan değerlendirilebilir. İlk teslimde büyük varlık başına 2–4, küçük varlık başına 1–2 malzeme hedefle.

`scout_1`, spekteki dört rotorlu **SCENARIO** aracıdır; NASA Ingenuity'nin fiziksel kopyası sayılmaz. `pr_1` NASA SEV referanslı olacaksa gerçek araç referansı/ölçüsü ayrıca doğrulanmalı; görünüşten teker sayısı, kütle veya dinamik parametre çıkarılmamalı. Arazi gerçek DEM'den üretilecek; Mars zeminini Tripo ile yeniden üretme. Taş görselleri arşiv ölçümü değildir; senaryo yerleşimi ve boyutu kod tarafındaki kayıtla eşleşecek.

## Claude'a verilecek görev

```text
REDLINE için Unreal 5.8.4 ve Gazebo Harmonic'te kullanılacak 3D varlık paketi hazırlıyorum.
Bu belgedeki varlık listesini ve docs/proje.md §9/10/13'ü esas al.

Önce astronaut, rover_1, scout_1 için ayrı ve ayrıntılı İngilizce Tripo promptları yaz.
Her prompt tek bir varlık için olsun. Gerçekçi bilimsel Mars keşif dili kullan;
renk, logo, yüz ve nihai sanat kararlarını benim tercihlerime göre netleştir.
Tüm varlık için tutarlı bir master, sonra motorlara ayrı export istiyorum.

Robotun teker, rotor, direk, kol ve mafsallarını tek birleşik mesh'e kaynatma.
Üretim çıktısı birleşik gelirse Tripo segmentation/Blender aşamasında parçaları ayır,
şaft/pivot merkezlerini düzelt ve kısa dönüş testiyle kontrol et.
Parçalar bir arada monte edilmiş nötr pozda ve ayrı seçilebilir olsun;
exploded view yalnız yardımcı referans olsun.

Astronot tam vücut A-pose; kollar gövdeden, parmaklar birbirinden ayrık;
ayaklar ve eller kesilmemiş, sırt çantası belirgin; sahne, taban platformu,
ışık, yazı ve logo üretme. İskelet, skin weights ve animasyon uyumu ayrıca test edilecek.

Robot asset'leri görsel üretimdir. Kütle, inertia, joint limit, motor itkisi,
sensor frame'i, ROS topic'i, URDF/SDF ve uçuş kontrolü mesh'ten otomatik doğru çıkmaz.
Bu parametreleri kaynak veya açık SCENARIO seçimiyle ayrı kaydet.

Her varlık için source.glb, düzenlenebilir master.blend, Unreal FBX+textures,
Gazebo için sade DAE/OBJ+textures ve ayrı basit collision geometrisi hazırla.
Format exporter'da yoksa master'dan Blender ile dönüştür; hazır olduğunu varsayma.
Master metre, sağ elli X ileri/Y sol/Z yukarı. UE export'una dönüşümü yalnız bir kez uygula.
1 m kalibrasyon küpüyle Gazebo'da 1 m ve Unreal'da 100 cm ölç.

SOURCE.md ve asset.json'a üretim task id'si, kullanılan prompt/sürüm, ölçüler,
parça/pivot listesi, texture/LOD bilgisi, lisans ve import test sonuçlarını yaz.
Gerçek dosya görülmeden game-ready veya iki motorda çalışıyor ilan etme.
Kod, ROS mesajları, T1 verileri, git veya GitHub üzerinde değişiklik yapma.
```

## Ortak master ve iki ayrı teslim

```text
assets/incoming/<asset_id>/
  source.glb                  # Orijinal Tripo çıktısı; korunur
  master.blend                # Temizlenen düzenlenebilir ana varlık
  textures/                   # BaseColor, Normal, Roughness, Metallic; AO isteğe bağlı
  unreal/                     # FBX, ayrı PNG texture'lar, LOD, collision
  gazebo/                     # Sade DAE/OBJ görseller, basit collision; metre
  preview/                    # Ön/yan/arka ve parça/pivot ekran görüntüleri
  asset.json                  # Birim, ölçüler, parça/joint/pivot ve export bilgisi
  SOURCE.md                   # Kaynak/üretim task id/prompt/sürüm/tarih/lisans
```

Bu bir teslim dizini önerisidir; henüz dosya oluşturulmadı. Büyük dosyaları kullanıcı GitHub planına göre yönetecek; `.gitignore` veya LFS otomatik değiştirilmez.

**Ortak master:** metre, sağ elli +X ileri/+Y sol/+Z yukarı. Montaj root'u ile görsel pivot ayrımı `asset.json` içinde olsun. Teker/rotor pivotu kendi dönme ekseninde, kapı pivotu menteşede; bütün parçaları ayrı ayrı merkezleyip montajı bozma. Nihai robot ölçüsü/inertia'sı seçilene kadar tüm sayısal ölçüleri SCENARIO olarak kaydet.

**Unreal:** astronot `SK_Astronaut` + skeleton + test animasyonları; statik parçalar `SM_Rover_*`, `SM_Drone_*`, vb. Teker/rotor dönüşleri için parçalı static mesh veya uygun skeletal mesh seçilebilir. Konveks collision `UCX_...` adlarıyla ayrı hazırlanır. Ortak X/Y/Z ve metre→santimetre dönüşümü exporter/importer ve ROS köprüsünde iki kez uygulanmamalı; poz dönüşümü ile asset'in kendi eksen düzeltmesi ayrı kayıtlı olmalı. 1 m küp, yön okları, pivot, normal map ve malzeme bağlantıları gerçek import'ta ölçülür.

**Gazebo:** sade görsel mesh + URDF/SDF link/joint yapısı. Gövde box/convex, teker cylinder, insan kapsülü gibi basit çarpışma şekilleri tercih edilir. Inertial/kütle/COM ve sensör frame'leri ayrıca tanımlanır; render mesh'ini doğrudan inertia veya karmaşık dinamik collision sayma. Matkap/kol/rotor dekoru fiziksel joint/sensör sistemi yerine geçmez. RViz robot modeli gösterebilir; fizik ve sensör yürütmesi Gazebo'dadır.

Robot hareketi ve sensörlerin otoritesi ROS/Gazebo olacak. Unreal aynı robotun odometry/joint verisini gösterir. Astronot Unreal'da oyuncu karakteridir; Gazebo'da robotların algılayabilmesi için pozla güncellenen kinematik proxy kullanılacak.

## Teslim kabulü

1. Önce 1 m küp ve eksen okları iki motor/importer'da ölçülsün; tüm araçları sonra topluca dışa aktar.
2. İnsan idle/walk animasyonunda omuz, diz, parmak ve sırt çantası deformasyonu kontrol edilsin.
3. Her teker/rotor doğru pivot çevresinde dönebilsin; kol/direk parçaları ayrı hareket edebilsin.
4. Texture'lar dosyada bulunsun; PBR kanalları, normal yönü ve UV seams gerçek ışık altında görülsün.
5. Collision'lar görsel forma ve kayıtlı boyutlara uygun olsun; küçük ayrıntılar robot fiziğini gereksiz ağırlaştırmasın.
6. Gazebo'da mesh'in yüklenmesi, URDF/SDF'nin çalışması ve Nav2/drone kontrolünün çalışması ayrı kontrollerdir. Unreal import'u da ROS köprüsünün çalıştığı anlamına gelmez.
7. Sonuçlar SOURCE.md/asset.json'a tarih/sürümle yazılsın; eksik rig, collision veya exporter açıkça belirtilsin.

## Kontrol edilen teknik kaynaklar

- [Tripo formatları](https://www.tripo3d.ai/product-doc/support/faq) ve [segmentation](https://www.tripo3d.ai/product-doc/module-post-processing/segmentation): format/parça işlemleri mevcut; tek prompt mekanik parça/pivot doğruluğunu garanti etmez. Hesaba/işleme uygun export seçeneği ayrıca kontrol edilmeli.
- [Tripo conversion](https://docs.tripo3d.ai/export/conversion.html): rig'li modelde OBJ/STL kısıtları var. Astronotun rig'li ana teslimi için bu formatlar kullanılmaz.
- [Epic FBX static mesh pipeline](https://dev.epicgames.com/documentation/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine?lang=en-US): FBX importer 2020.2, pivot ve UCX collision kuralları. Exporter'ın gerçek ürettiği sürüm ve import sonucu test edilmeli.
- [ROS REP-103](https://www.ros.org/reps/rep-0103.html): SI metre ve robot X ileri/Y sol/Z yukarı.
- [Gazebo Harmonic visual/collision ayrımı](https://gazebosim.org/api/sim/8/adding_visuals.html): karmaşık görselin yanında sade collision kullanılabilir; DAE/OBJ dosyaları model paketinde kullanılabilir. Gerçek varlıkların import'u ayrıca test edilecek.
- [NASA SEV referansı](https://science.nasa.gov/3d-resources/space-exploration-vehicle/): yüzey sürümünde 12 teker açıklaması ve indirilebilir GLB bulunur. Kullanım koşulları ve mekanik ayrıştırma kontrol edilmeden hazır robot sayılmaz.

Skill'ler: `blender-director`, `unreal-export`, `ros2-engineering-skills`; yalnız brief ve teknik sözleşme için kullanıldı. Bu belge model üretim veya oyun içi doğrulama raporu değildir.

## Yerel üretim teslimi

14 Kasım 2026’daki sonraki kullanıcı isteğiyle bu brifin varlık hazırlığı yapıldı. [Teslim ve kabul sınırları](3D_ASSET_DELIVERY.md), [görsel katalog](../assets/catalog.html), [toplu önizleme](../assets/preview/contact_sheet.jpg). Bu brifin önceki “model üretilmedi” ifadeleri yazıldığı andaki durumu anlatır; gerçek üretim ve harcama sonraki teslim kaydındadır.
