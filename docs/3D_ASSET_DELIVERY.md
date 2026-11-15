# 3D varlık teslimi — 14 Kasım 2026

[Görsel katalog](../assets/catalog.html) · [Toplu önizleme](../assets/preview/contact_sheet.jpg) · [Varlık listesi ve kullanım](../assets/README.md).

Kullanıcının Tripo ile üretim ve diğer varlıkları internetten bulup hazırlama isteğiyle 15 görsel paket oluşturuldu. Önceki 3D bekletme kararı bu varlık hazırlığı için kaldırıldı; UI, seviye, arazi sahnesi ve malzeme sanat kararları uygulamaya eklenmedi.

Tripo: önceki astronotun 80 kemikli Unreal biped rig’i ve idle/walk animasyonları; önceki drone’un parçalanması; çevre istasyonu; APXS benzeri başlık, LIBS, matkap, nötron kutusu ve multispektral kamera. EV1/EV2 aynı mesh ve iskeleti, kırmızı/mavi vurgu dokularını kullanır.

Hazır kaynaklar: NASA [Curiosity](https://github.com/nasa/NASA-3D-Resources/tree/master/3D%20Models/Curiosity%20Rover%20(MSL)), [SEV](https://science.nasa.gov/3d-resources/space-exploration-vehicle/), [HDU](https://science.nasa.gov/3d-resources/habitat-demonstration-unit/) ve [numune tüpü](https://science.nasa.gov/3d-resources/mars-2020-sample-tube/); Poly Haven [Rock 07](https://polyhaven.com/a/rock_07), [Rock 09](https://polyhaven.com/a/rock_09) ve [industrial container](https://polyhaven.com/a/industrial_pastic_container). NASA medya koşulları ve Poly Haven CC0 kaydı her varlığın SOURCE.md/asset.json dosyasında saklanır.

Tripo rover adayının teker yerleşimi brife uymadı; orijinal çıktı korunup asıl rover NASA’nın altı tekerli modelinden hazırlandı. Native NASA Blender kaynağının 180. karesindeki açılmış poz kullanıldı. Parçalar bağımsız, montaj dönüşümleri açık; önceki parent adları metadata’dadır. Bu yapı ROS’taki link/joint otoritesinin yerine geçmez.

Her pakette master.blend, GLB sunum, üç FBX LOD, PNG dokular, sade OBJ, ayrı parça OBJ’leri, collision proxy’leri, ön/yan/arka görseller ve kaynak/ölçek kayıtları vardır. Matkap ucu, numune kapağı, habitat hava kilidi kapısı ayrıdır. Taşıma ve önbellek aynı kutu varlığını kullanabilir; numune kökeni görselin yerinden çıkarılmaz.

Yerel kontroller: 15 master yüklendi; 15 FBX ve 15 OBJ tekrar içe aktarıldı. FBX boyut farkı en fazla 0,000000239 m; sade OBJ en fazla 0,011753 m. 1 m küpün Blender FBX dönüşü geçti. 6 rover tekeri, 12 SEV tekeri ve 4 drone rotor grubunda 90° dönüş, sabit pivot ve vertex hareketi kontrol edildi. Astronotta 4’e sınırlanmış/normalize edilmiş skin ağırlıkları ve iki ayrı animasyon dosyası doğrulandı. Kanıt: [verification.json](../assets/verification.json), parça/animasyon kayıtları ve render’lar.

Motor kabulü bekler: Unreal/Gazebo içinde 100 cm/1 m ölçümü, import, normal map yönü, LOD geçişi, rig deformasyonu ve collision/kapı/giriş kontrolü yapılmadı. FBX 7400 dosyaları Blender’da yeniden açıldı; Epic importer uyumluluğu varsayılmaz. Gazebo visual.sdf statik görseldir. Robot fiziği, inertia, eklem limitleri, sensör frame’leri, Nav2, drone kontrolü ve köprü kodu bu pakette yazılmadı. Bu çalışma bir T kilometre taşını tamamlamaz.

Tripo harcaması 305 kredi; başlangıç 930, kalan 625, frozen 0. Önceki astronot 50 ve drone 20 kredi bu toplamın dışındadır. [Görev ve prompt kaydı](../assets/CREDIT_LEDGER.json). Dosyalar yereldir; Git/LFS/ignore değişikliği veya commit/push yapılmadı. Önceden var olan araştırma/skill/lisans kayıtları korundu.

## Ek teslim ve revizyonlar — 14 Kasım 2026 (Claude Code)

Kullanıcının "küçük büyük bütün 3D'leri yapalım" isteğiyle kılavuzun §8 M10 ve §19.1 listesindeki eksik nesneler tamamlandı. **Tripo kredisi kullanılmadı.** Toplam teslim 30 paket; diğer ajanın `validate_package.py` doğrulayıcısı 30/30 geçti.

- **11 prosedürel paket** (`production/procedural_assets.py`, özgün geometri, üretken AI veya üçüncü taraf mesh yok): istasyon işareti, röle direği, alet arabası, vana paneli (H06), drone pisti (H04), rover garajı (H03), harita masası, robot konsolu, görev duvarı (H01), numune laboratuvarı (H05), kap rafı. Ölçüler SCENARIO tasarım seçimidir. Ekran yüzeyleri canlı render hedefi için tam UV taşır.
- **Vana paneli ArUco:** `DICT_4X4_50`, kimlik 10 ve 11, 15 cm işaret ve 1 hücre beyaz kenar. Desenler OpenCV 5.0.0 ile üretildi ve yazılan PNG'den yeniden okunarak kimlikleri doğrulandı. Motorda dokular sıkıştırmasız ve filtresiz kullanılmalı.
- **4 ek taş** Poly Haven CC0'dan, MD5 doğrulamasıyla: Moon Rock 01/03/05 ve Namaqualand Boulder 04.
- **Paketleme:** `production/build_extra.py`, `build_package.py`'yi değiştirmeden ölçek 1 ile kullanır. Ek kontroller `verification_extra.json` içinde: 15/15 geçti. Dönen parçalar (2 teker Y ekseni, 3 vana kolu ve ibre X ekseni, anten Z ekseni) sıfır pivot kaymasıyla döndü. Önü olan 8 nesnede ön tarafın +X'e baktığı ölçüldü.
- **Revizyonlar:**
  - **Sığınak:** NASA logosu, ABD bayrakları, HAB X ve HDU amblemleri dokudan temizlendi. Kullanılan yöntem OpenCV inpaint, portlar korundu; kılavuz §8 NASA marka öğesini yasaklıyor.
  - **Taşıma kutusu:** mavi depo kasası açık griye boyandı.
  - **Astronot:** master −Y'ye bakıyordu, belgelenen +X ileri sözleşmesine döndürüldü. Klip FBX'leri ve önizlemeler mevcut betiklerle yeniden üretildi.

  Gerekçe ve hash'ler `asset.json → revisions` kayıtlarında. Orijinal kaynak dosyalar değişmedi.
- **Motor kabulü bekliyor:** Unreal/Gazebo içi import, ölçek, malzeme ve kamerayla ArUco tespiti. Ay taşları açık gri; Mars tonu motor materyalinde verilmeli. Kask vizörü açık; kapalı vizör sanat kararıdır. Habitat iç mekân kabuğu (oda) seviye tasarımıdır, üretilmedi. Kaya bloğunun 800 üçgenlik Gazebo görselinde OBJ ölçü farkı 3,7 cm; eşik 4 cm.
