# BXW gerçek Mars yüzeyi

14 Kasım 2026, 15:10 (+03:00). İlk veri tabanlı yüzey paketi hazır; Gazebo'da
dokulu 3D yüzey gözle görüldü. Unreal 5.8.4'te bir merkez karosu ve çevre halkası
import/ölçek/eksen/UV/BaseColor bağlantısı kontrollerini geçti.

16:00 güncellemesi: T3'ün RViz hedef sürüşü de geçti; fiziksel hareket 9,496 m,
hedef hatası 0,492 m. [RViz kabul kanıtı](verification/T3_RVIZ_ACCEPTANCE.json).
T4 C++ köprüsü ayrı uygulama/test akışında devam ediyor.

| Yerel çıktı | Kullanım |
|---|---|
| [Önizleme](../data/engines/BXW/surface-blender-v1/BXW_surface_overview.png) | Gerçek arazi + yörünge kaplaması; sabit teknik ışık. |
| [Blender](../data/engines/BXW/surface-blender-v1/BXW_surface.blend) | Düzenlenebilir 17 parça, metre/ENU. |
| [GLB](../data/engines/BXW/surface-blender-v1/BXW_surface.glb) | Kaplamalar dâhil ortak 3D aktarımı. |
| [FBX klasörü](../data/engines/BXW/surface-blender-v1/fbx/) | Unreal için ayrı LOD0 karoları ve halka. |
| [Manifest](../data/engines/BXW/surface-v1/manifest.json) | Tile pozları, geometri/kaplama hash'leri ve QA. |
| [Görüntü kökeni](../data/engines/BXW/surface-v1/imagery.json) | CRS, bantlar, maske, orijin, atlas dönüşümleri ve kaynak metni. |

Büyük dosyalar mevcut `data/engines/` ignore kuralıyla yerelde tutulur. GitHub'a
yüklenmedi; Git ayarları değiştirilmedi. Dışarıda hazırlanan araç modellerine
dokunulmadı, bu arazi çalışmasında Tripo kredisi harcanmadı.

## Gerçek ayrıntı ve sınırlar

Yükseklik T1 Gale v3 DEM'den gelir: merkez 1 km², 1 m post, 250 m karolar;
3 km çevre 4 m post. **17 mesh, 3.003.000 üçgen.** Görsel/collision vertex ve
triangle geometrileri aynıdır; görsel dosyaya yalnız UV/MTL eklenir. Collision
dosyaları kaynakla byte eşittir. Üç DEM→mesh farkı 0,0047 / 0,0222 / 0,0195 m;
bunlar sayısal aktarım kontrolüdür, mutlak arazi doğruluğu değildir.

Kaplama gerçek Gale HiRISE LRGB, 25 cm, RGB/JPEG COG ve dahili maskeden gelir.
İki 4096² RGBA atlası merkezde 0,244 m, çevrede 0,732 m çıktı aralığı verir;
merkezdeki küçük yeniden örnekleme yeni ayrıntı sayılmaz. Sağlayıcı maskesine
göre geçerli oranı ikisinde %100. Gri şeritler sağlayıcı mozaiğinde vardır;
otomatik boya, siyah piksel doldurma veya AI yüzey üretimi yapılmadı.

1 m post santimetrelik taş geometrisi veya 1 m mutlak doğruluk değildir.
Kaplama ışık/gölge ve yayıncı keskinleştirmesi içerir; ölçülmüş albedo/PBR,
mineral veya çekiş katmanı değildir. Mikrotaş, toz ve ayrıntı normal haritası
birlikte hazırlanacak ayrı SIMULATED/SCENARIO katmanlardır.

## Gazebo'da yeniden çalıştırma

WSL'de, bu makinede doğrulanan cache ile:

```bash
env GALLIUM_DRIVER=d3d12 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA \
  bash scripts/run-t3.sh \
  /home/ahmetefesensoy/.cache/redline/ros/ws-fc2d460433599417-xw9hhwnf \
  --terrain /home/ahmetefesensoy/.cache/redline/t3/surface-bxw-v1/manifest.json \
  --gazebo-gui
```

Bu bounded test hedef sonucunda kendi süreçlerini kapatır. Workspace değişirse
`bash scripts/build-t3.sh` çıktısındaki yeni yol kullanılır. Üretim yardımcıları
`export_t3_terrain.py`, `fetch_t3_imagery.py`, `package_t3_surface.py`'dir.
Çıktı yolları yeni olmalıdır; eski kanıtlar üstüne yazılmaz.

Kamera yaklaşık −3,6 km gerçek DEM kotuna bakar. Robot fiziği, sensör ve Nav2
Gazebo/ROS'tadır. Görsel model değişimi collision/inertia/eklem sözleşmesini
kendiliğinden değiştirmez.

## Unreal'a aktarım

FBX: metre tabanlı Blender, `FBX_SCALE_UNITS`, −Y forward / Z up. Gerçek UE
importunda 250 m kenar 25.000 cm ölçüldü. İki temsilî mesh'in üçgen sayısı,
örnek vertex `(100x, −100y, 100z)` dönüşümü, UV ve kaynak PNG→BaseColor bağlantısı
geçti. En büyük boyut farkı 0,03125 cm. Blender'da 17/17 FBX yeniden import
kontrolü geçti; max fark 0,000244 m.

Actor pozu manifestteki `pose_map_m`'den aynı ROS→Unreal dönüşümüyle verilir.
Y'yi ikinci kez ters çevirme; mesh pivotlarını sıfırlama. `H0=0` T1 kararı
korunur; kamera/başlangıç pozu da aynı yaklaşık −3,6 km kotunu kullanmalıdır.

Unreal testi `test-results/t3-unreal-probe` altındaki ayrı commandlet projesidir.
Ana REDLINE C++ projesi/T4 köprüsü oluşturulmadı. NullRHI testi GPU malzeme
render'ı, Nanite/LOD performansı, insan collision'ı veya bütün karoların görsel
kabulü değildir. FBX smoothing-group uyarısı verdi; son görünümde normal ve
smoothing politikası ayrıca kontrol edilmelidir. Test yardımcısı
`scripts/verify_t3_unreal_import.py`; [kanıt özeti](verification/T3_LOCAL_2026-11-14.json).

Kredi: Timothy J. Parker / Fred J. Calef III; NASA/JPL-Caltech, USGS Astrogeology
Science Center, University of Arizona.
[USGS ürün kaydı](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_orthophoto_mosaic_25cm),
[kaynak üretim metni](https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_HiRISE-LRGB_78quads_sharp_cog.txt).
Yayın tarihi çekim tarihi sayılmaz.
