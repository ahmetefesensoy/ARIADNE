# Gerçek Gale kırpımı

NASA/JPL–USGS Gale DEM v3 ve ortak kapsamadaki kayıtlı HiRISE LRGB mozaiği. Mars equirectangular, küre yarıçapı 3.396.190 m, standart paralel ve merkez meridyen 0°. Koordinat penceresi: easting 8.146.000–8.148.000 m, northing −286.000–−284.000 m.

`elevation_north_up.npy`: kuzeyden güneye satırlı 1001 × 1001 float32 yükseklik kırpımı; bilinear örnekleme. Piksel aralığı 2000/1001 m; dış piksel merkezleri arasındaki mesafe yaklaşık 1998 m. `orbital_texture.jpg`: aynı sınırların 2048 × 2048 RGB kırpımı. Kaynakların tamamı indirilmedi; HTTP range erişimi kullanıldı.

`crop.json` kaynak CRS ve sınırları tutar. ROS paketindeki [manifest](../../../ros2_ws/src/redline_mars_sim/TERRAIN_PROVENANCE.json) SHA-256, işleme çözünürlüğü, yerel başlangıç ve sınırları içerir. `ros2_ws/tools/build_gale_terrain.py` bu kayıtlardan 4 m ağ ve planlama gridini üretir.

Kaynak katalogları: [USGS DEM](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m), [USGS görüntü](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_orthophoto_mosaic_25cm). Katkı: NASA/JPL-Caltech, USGS Astrogeology, University of Arizona; Gale mozaikleri Fred Calef ve Timothy Parker.

DEM karma çözünürlüklü kaynaklardan oluşur. Kaynak grid 1 m olsa da her hücre aynı doğrulukta değildir. Dikey abartı uygulanmadı. Yaklaşık 622,54 m yükseklik farkı bu kırpımın min/max farkıdır. LRGB renkleri mineral sınıfı veya öğrenme etiketi değildir.

Kaynağı yeniden kırpmak için `ros2_ws/tools/fetch_gale_aoi.py` ayrı bir rasterio/numpy/Pillow ortamında çalıştırılır. Bu bilgisayarda ortam `/home/ahmetefesensoy/.cache/redline-geodata` içinde; ROS sistem Python'undan ayrıdır. Araç mevcut dosyaları korur; yeniden indirmek için `--refresh` gerekir. Kaynak CRS'leri eşleşmezse veya eksik yükseklik varsa işlem durur. Ardından `build_gale_terrain.py` sistem Python'unda ve ROS `build.sh` çalıştırılır.
