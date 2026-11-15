# REDLINE 3D varlık paketi

14 Kasım 2026 · **30 yerel görsel varlık paketi**, EV1/EV2 malzeme varyantları ve astronot idle/walk animasyonları hazırlandı. [Toplu önizleme](preview/contact_sheet.jpg) · [Görsel katalog](catalog.html).

Tripo ile astronot rig/animasyonları, drone parçalama, bilim istasyonu ve beş bilim aracı hazırlandı. Rover için üretilen Tripo adayının teker yerleşimi brife uymadı; asıl teslimde NASA Curiosity modeli kullanıldı. Basınçlı rover/sığınak/numune tüpü NASA’dan; iki taş ve taşıma kutusu Poly Haven CC0 kaynaklarından alındı.

| Varlık | Kaynak | Üçgen: LOD0 / Gazebo visual | Parça |
|---|---|---:|---:|
| [astronaut](incoming/astronaut/SOURCE.md) | Tripo · AI üretimi | 95,000 / 7,999 | 1 |
| [rover_1](incoming/rover_1/SOURCE.md) | NASA hazır model | 48,492 / 25,003 | 82 |
| [scout_1](incoming/scout_1/SOURCE.md) | Tripo · AI üretimi | 55,000 / 11,999 | 5 |
| [pr_1](incoming/pr_1/SOURCE.md) | NASA hazır model | 149,992 / 29,988 | 15 |
| [habitat](incoming/habitat/SOURCE.md) | NASA hazır model | 2,264 / 2,264 | 2 |
| [science_station](incoming/science_station/SOURCE.md) | Tripo · AI üretimi | 23,792 / 6,493 | 14 |
| [tool_apxs](incoming/tool_apxs/SOURCE.md) | Tripo · AI üretimi | 10,896 / 1,999 | 1 |
| [tool_libs](incoming/tool_libs/SOURCE.md) | Tripo · AI üretimi | 10,639 / 3,000 | 1 |
| [tool_drill](incoming/tool_drill/SOURCE.md) | Tripo · AI üretimi | 11,103 / 2,987 | 20 |
| [tool_neutron](incoming/tool_neutron/SOURCE.md) | Tripo · AI üretimi | 6,449 / 1,999 | 1 |
| [tool_multispectral](incoming/tool_multispectral/SOURCE.md) | Tripo · AI üretimi | 10,757 / 2,999 | 1 |
| [sample_tube](incoming/sample_tube/SOURCE.md) | NASA hazır model | 6,998 / 1,498 | 2 |
| [sample_case](incoming/sample_case/SOURCE.md) | Poly Haven · CC0 | 7,118 / 1,999 | 3 |
| [rock_07](incoming/rock_07/SOURCE.md) | Poly Haven · CC0 | 4,500 / 800 | 1 |
| [rock_09](incoming/rock_09/SOURCE.md) | Poly Haven · CC0 | 4,500 / 800 | 1 |
| [station_marker](incoming/station_marker/SOURCE.md) | REDLINE prosedürel · özgün | 1,108 / 1,108 | 7 |
| [relay_mast](incoming/relay_mast/SOURCE.md) | REDLINE prosedürel · özgün | 816 / 816 | 7 |
| [equipment_cart](incoming/equipment_cart/SOURCE.md) | REDLINE prosedürel · özgün | 1,376 / 1,376 | 7 |
| [valve_panel](incoming/valve_panel/SOURCE.md) | REDLINE prosedürel · özgün | 3,104 / 3,104 | 9 |
| [drone_pad](incoming/drone_pad/SOURCE.md) | REDLINE prosedürel · özgün | 444 / 444 | 2 |
| [rover_garage](incoming/rover_garage/SOURCE.md) | REDLINE prosedürel · özgün | 3,402 / 3,402 | 4 |
| [map_table](incoming/map_table/SOURCE.md) | REDLINE prosedürel · özgün | 50 / 50 | 3 |
| [console_desk](incoming/console_desk/SOURCE.md) | REDLINE prosedürel · özgün | 842 / 842 | 6 |
| [lab_bench](incoming/lab_bench/SOURCE.md) | REDLINE prosedürel · özgün | 1,918 / 1,918 | 4 |
| [mission_wall](incoming/mission_wall/SOURCE.md) | REDLINE prosedürel · özgün | 26 / 26 | 2 |
| [storage_rack](incoming/storage_rack/SOURCE.md) | REDLINE prosedürel · özgün | 232 / 232 | 2 |
| [moon_rock_01](incoming/moon_rock_01/SOURCE.md) | Poly Haven · CC0 | 4,495 / 798 | 4 |
| [moon_rock_03](incoming/moon_rock_03/SOURCE.md) | Poly Haven · CC0 | 4,499 / 800 | 1 |
| [moon_rock_05](incoming/moon_rock_05/SOURCE.md) | Poly Haven · CC0 | 4,500 / 800 | 1 |
| [namaqualand_boulder_04](incoming/namaqualand_boulder_04/SOURCE.md) | Poly Haven · CC0 | 6,000 / 800 | 1 |

Her pakette düzenlenebilir `master.blend`, sunum `presentation.glb`, ayrı FBX LOD0/1/2, PNG kaplamalar, sade Gazebo OBJ ve parça OBJ’leri, çarpışma proxy’leri, `SOURCE.md` ve `asset.json` vardır. Parça kökeni/pivotu ve kaynak→master dönüşümü kayıttadır. LOD1/2 ayrı dosyalardır; Unreal’a açıkça LOD olarak yüklenir.

Astronotun 80 kemikli iskeleti, dört etkiye sınırlanıp normalize edilmiş skin ağırlıkları, ayrı idle/walk FBX dosyaları ve dört karelik hareket önizlemeleri vardır. EV1 kırmızı; EV2 mavi vurgu dokusudur. Mesh ve iskelet ortaktır; yüz/boyun UV alanı renk değişiminden korunmuştur. EV2 için yalnız `material_variants.EV2.BaseColor` değiştirilir.

**Yerel doğrulama: 30/30 geçti.** FBX boyut farkı ≤4.77e-07 m; sade OBJ farkı ≤0.0366 m. 1 m kalibrasyon küpünün Blender FBX dönüşü 1 m’dir. Rover 6, SEV 12 ayrı teker; drone 4 ayrı rotor grubudur. 90° dönüşlerde pivotun sabit kalması ve gerçek vertex hareketi ölçüldü. [Makine raporu](verification.json), [kalibrasyon](calibration/), parça bazında `pivot_checks.json` ve karakter `animation_checks.json`.

**Unreal/Gazebo kabulü bekliyor.** Motor içinde 100 cm/1 m ölçümü, PBR/normal bağlantıları, LOD geçişleri, giriş/kapı çarpışması ve skin deformasyonu ayrıca kontrol edilir. FBX 7400 dışa aktarımı yerelde yeniden yüklendi; Epic importer uyumluluğu bu sonuçtan varsayılmaz. Görsel collision’lar taslak basit proxy’lerdir. Gazebo `visual.sdf` statiktir; robot fiziği, inertia, eklem limitleri, Nav2, drone kontrolü ve ROS köprüsü oluşturulmadı. Robot otoritesi ROS/Gazebo’da kalır.

Sığınak ilk teslimde dış görünüş ve ayrı hava kilidi kapısıdır; yürünebilir iç mekân içermez. Numune tüpü STL’si ayrı senaryo kapağına bölündü; gerçek uçuş sızdırmazlık mekanizması değildir. Taşların biçimi/rengi NASA ölçümü veya mineral kanıtı sayılmaz. Her varlığın kalan sınırları kendi kaydındadır.

Bu oturum **305 Tripo kredisi** kullandı: rover adayı 60, istasyon 40, astronot rig+iki animasyon 45, drone parçalama 40, beş bilim aracı 120. Başlangıç 930 → kalan 625; frozen 0. Önceki astronot 50 ve drone 20 kredi bu toplamın dışındadır. [Görev/harcama kaydı](CREDIT_LEDGER.json).

**Ek paketler (Claude Code oturumu):** 11 prosedürel saha/habitat nesnesi (istasyon işareti, röle direği, alet arabası, ArUco'lu vana paneli, drone pisti, rover garajı, harita masası, robot konsolu, numune laboratuvarı, görev duvarı, kap rafı) `production/procedural_assets.py` ile özgün geometri olarak; 4 ek taş Poly Haven CC0'dan hazırlandı. Tripo kredisi kullanılmadı. Dönen parçalar (teker, vana kolu, gösterge ibresi, anten) pivot ve +X ön kontrolüyle `verification_extra.json` içinde. ArUco desenleri OpenCV ile üretilip PNG'den yeniden okunarak doğrulandı.

**Revizyonlar:** Sığınak dokusundan NASA logosu, ABD bayrakları, HAB X ve HDU amblemleri temizlendi; taşıma kutusu açık griye boyandı; astronot master'ı belgelenen +X ileri sözleşmesine döndürüldü (önceki "front" önizlemesi yandan görünüyordu). Gerekçe ve hash'ler ilgili `asset.json → revisions` kayıtlarında.

Ham çıktılar korunur; NASA/Poly Haven kaynak ve lisansları varlık başına kayıtlıdır. Tripo çıktıları AI görselidir ve CC0 olarak yeniden lisanslanmaz. Git/LFS/ignore kuralları değiştirilmedi, commit/push yapılmadı. Büyük dosyaları yayınlama kararı kullanıcıya aittir. Projenin T0–T11 kilometre taşları bu varlık hazırlığıyla tamamlandı işaretlenmez.
