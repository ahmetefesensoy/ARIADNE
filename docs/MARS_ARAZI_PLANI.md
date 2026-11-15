# Gerçek veriden BXW arazi paketi

14 Kasım 2026, 14:50 (+03:00). Kullanıcı görünür Mars yüzeyini T1 verileriyle
hazırlamamızı ve aynı yüzeyi Gazebo/Unreal'da kullanmayı istedi. Bu çalışma
araç/astronot modellerini veya birlikte yapılacak sanat tasarımını değiştirmez.

T1 Gale v3 DEM, yerel `map` çerçevesinde 1 m yükseklik örnekleri sağlar. Merkez
1 km alan 250 m karolardan, 3 km çevre 4 m örneklenmiş halkadan oluşur. Mevcut
17 collision mesh'i korunur. Görsel türev yalnız UV ve gerçek yörünge kaplaması
ekler; ölçülmüş topoğrafyaya gürültü, kaya veya yapay yükseklik eklenmez.

Gale HiRISE LRGB kaplaması ayrı bir kaynak üründür. Kendi TIFF CRS'i, bantları,
maskesi ve üretim geçmişi doğrulanır. Yerel ENU dönüşümü T1'in aynı E0/N0/H0 ve
cos(phi0) tanımını kullanır. Sayısal dönüşüm testi mutlak saha hizası kanıtı
sayılmaz. Renkler mineral, sürtünme veya ölçülmüş PBR malzemesi değildir.

İlk paket bütçesi: merkez için en fazla 4096² RGB/alpha atlas, çevre için en
fazla 4096² atlas; 17 mesh ve mevcut yaklaşık 3 milyon üçgen. Kaynak görüntünün
gerçek örnek aralığı daha büyükse çıktı çözünürlüğü yeni ayrıntı diye sunulmaz.
PNG kaplaması, UV'li OBJ ve metre/ENU manifesti motorlardan bağımsız ana
pakettir. Unreal aktarımında metre→cm ve Y işaret dönüşümü açıkça kaydedilir.
FBX/engine import doğrulaması yapılmadan dosyalar "Unreal'da test edildi" diye
işaretlenmez. Robot dinamiğinin tek sahibi Gazebo kalır.

Kabul: üç sayısal UV/harita kontrolü, değişmeyen visual/collision geometri
imzası, kaynak/hash kayıtları ve gerçek render'da görünen arazi. Nav2 hedefe
varış T3'ün ayrıca kaydedilecek kabulüdür. Santimetrelik yüzey ayrıntısı ve
dağıtılmış taşlar ileride SIMULATED/SCENARIO sanat katmanı olarak birlikte
hazırlanır; 1 m DEM'den ölçülmüş gibi üretilmez.

`roversim27` README, ERC world tanımı ve arazi test raporu kullanıcının izniyle
referans olarak okundu. ERC, Polonya/Dünya koordinatlı bir test sahasıdır;
kod veya zemin varlığı bu uygulamaya kopyalanmadı.

Kaynak: [USGS Gale ortofoto ürün kaydı](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_orthophoto_mosaic_25cm),
[T1 veri kaynakları](DATA_SOURCES.md). Renk mozaği yazarları Timothy J. Parker
ve Fred J. Calef III; ürün metni gerçek veri paketinde ayrıca saklanacak.
