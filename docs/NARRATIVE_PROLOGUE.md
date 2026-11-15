# REDLINE açılışı ve plak sahnesi

15 Kasım 2026 · SCENARIO · Unreal 5.8.4

Açılış sırası: Mars'a son alçalma → plak başında dinlenme → canlı dönüş
haritası → airlock hazırlığı → oyuncunun EVA çıkış onayı. İlk kurgu 62 saniye;
ses süresi uzarsa hazırlık betiği ilgili planın süresini uzatır.

`Space` sıradaki plana, `Esc` doğrudan oynanışa geçer. Açılışın sonunda
`E`, mevcut ROS brifing onayını gönderir. Koltuğa erişilebilir mesafedeyken
`F` dinlenmeyi başlatır/bitirir. Kriz ve dönüş evrelerinde dinlenme kapalıdır.
`start-t5-eva.ps1 -SkipPrologue` giriş filmini kapatıp brifingi korur.

Oyun birinci kişi kamerasıyla açılır. `V` ile üçüncü kişiye geçilir; kaskın
içi birinci kişi görüşünü kapatmaz. Üçüncü kişi kamera kolu 2,2 m ile sınırlı
ve duvar çarpışması etkindir. Oda çarpışma proxy'leri görsel kabinin iç
sınırlarına alınmıştır. Aktif görev, ad/metre/pin ile gösterilir; hedef arkada
veya ekran dışındaysa kenardaki ok yönü belirtir.

Komuta, mürettebat dinlenme ve bilim hazırlık odaları ortak koridora açılır.
Oyuncu komuta odasında, ROS brifing noktasının yanında başlar. `J` görev
defterini açar/kapatır; kaynaklar, dönüş payı, veri yaşı ve beş prova adımı
orada görünür. Tamamlanma yalnız taze ROS evrelerinden alınır. Robot/bilim
kampanyası bu giriş provasının tamamlanmasıyla bitmiş sayılmaz.

`Shift` hareketi hızlandırır; senaryo sınırı 3 m/s'dir ve eğim/hücre hız
kısıtları korunur. Planlayıcı yürüyüş maliyetini kullanmayı sürdürür. Hızlı
hareketin tüketimi ROS'ta ayrıca etkinleştirilen senaryo modelidir; fiziksel
Mars koşusu doğrulaması değildir. Ana girişten sonra yüzeye çıkış, bağlam,
dönüş ve debrief evreleri için dört kısa, atlanabilir, sesli kamera sahnesi
vardır. Bunlar gerçek zamanlı oyun sinematikleridir; önceden render edilmiş
video dosyaları değildir. PET, görev içindeki bu sahnelerde durmaz.

İniş, toz, kapılar ve içerideki ikinci astronot yalnız sunumdur. Gerçek EV1
yerinden taşınmaz; pose yayını aynı insan konumundan sürer. Film robotları,
ROS görev evresini, PET saatini veya kaynakları değiştirmez. Canlı harita
bayatlarsa ekran karartılır ve veri bekleniyor yazısı gösterilir.

## Varlıklar ve ses

Yedi yeni Tripo görseli kullanılır: plakçalar, dinlenme modülü, kurgu iniş aracı,
airlock, ayrı komuta merkezi, laboratuvar ve bağlantı koridoru. Komuta/bilim
odaları dinlenme modülünün kopyaları değildir.
Ham dosyalar `assets/incoming/prologue_*/tripo/` altında tutulur. Ölçek, UV,
kaplama ve LOD türevleri `data/engines/prologue-tripo-v1/` altındadır. Blender
ölçüsü Unreal'da santimetre olarak geri okunur. Oda, mevcut sahneye uyması
için açıkça ölçeklenir: komuta dış zarfı 600 × 360 × 335 cm, laboratuvar
600 × 360 × 280 cm. Koridorun iç açıklığı, dış kutu boyutundan ayrı ölçülür.
Yeni iç mekânların duvar/mobilya
geometrisi yalnız insan/kamera sorgusu için üçgen çarpışması kullanır; robot
kontrolüne veya Gazebo fiziğine girmez. Basit zemin/kapı proxy'leri de korunur.
Üretim ve FBX dönüşümleri toplam **245 Tripo kredisi** kullandı; doğrulanan
kalan bakiye **380**. [İlk üç üretim](../assets/narrative/prologue_v1/tripo_manifest.json),
[airlock](../assets/narrative/prologue_v1/airlock_tripo_manifest.json),
[ayrı iç mekânlar](../assets/narrative/prologue_v1/unique_interiors_manifest.json).
Tripo airlock'un arka kapısı kapalı geldiği için ham dosya korunarak türev
mesh'te UV'leri koruyan bir geçit açıldı. İç/dış sürgüler ayrı Unreal aktörleridir.
Bu bir görsel oyun kabinidir; basınçlı kap veya hava kilidi fiziği doğrulaması değildir.
Koridorun oda bağlantıları ve merkezdeki insan açıklığı da yalnız türevde
düzeltilmiştir. Laboratuvar üretimi merkezde zemin içermediği için mevcut düz
güverte kullanılır. Ham modeller bu düzeltmelerden etkilenmez.

Chet Baker kılıfı ve merkez etiketi özgün SVG/PNG çizimleridir: fotoğraf,
resmî albüm kapağı veya plak şirketi logosu kopyalanmadı. Ad, koleksiyon
dekorunda görünür. Bu kapak bir resmî albüm ya da müzik kaydı lisansı değildir.
Sahnede çalan **Vardiya Arası**, yerel olarak bestelenip sentezlenen özgün bir
caz taslağıdır; Chet Baker kaydı içermez. Oyunculuk ve son miks dinleme
incelemesi ayrıca yapılmalıdır.

Türkçe ses için yerel Chatterbox Multilingual V3 ile beş klip üretildi ve
Unreal'a alındı. Beş klip ve script hash'i doğrulanmadan import betiği bunları seçmez. Microsoft Tolga
klipleri yerel yedektir. Hiçbir oyuncunun veya sanatçının sesi referans olarak
yüklenmedi. Ses ve müzik üretiminde ücretli servis kullanılmadı.

## Yüz animasyonu

[MetaHuman Animator Audio Driven](https://dev.epicgames.com/documentation/en-us/metahuman/audio-driven-animation)
UE 5.6 ve sonrasında SoundWave'den mimik, göz kırpma ve baş hareketi üretebilir.
MetaHuman yüz mesh'i gerekir. Yerel Unreal kurulumunda ilgili eklenti dosyaları
var; REDLINE karakteri bir MetaHuman değildir. Ücret koşulları
[MetaHuman lisansında](https://www.metahuman.com/license) açıklanır.

Mevcut Tripo astronotun 80 kemikli gövde rig'inde çene/dudak/göz kemikleri veya
yüz blendshape'leri bulunmuyor. Bu yüzden seslendirme çalışsa bile yüz henüz
konuşmaz. Baş uyarlama veya ayrı bir yüz rig'i gerekir; eklentiyi açmak tek
başına bu sorunu çözmez. Anlatıcı mevcut açılışta telsiz/görev sesi olarak
kullanılır.

[Chatterbox](https://github.com/resemble-ai/chatterbox) Türkçe destekli MIT
lisanslı yerel araştırma seçeneğidir; proje kendi README'sinde bakım durumunu
belirtir. [NVIDIA Audio2Face-3D](https://github.com/NVIDIA/Audio2Face-3D) başka
bir yüz çözümü sunar; SDK ve model lisansları ayrıdır. UE 5.8 hazır paket
uyumluluğu burada doğrulanmadı. XTTS-v2 modelinin ticari kullanım sınırlaması
nedeniyle onu genel oyun ses hattının varsayılanı yapmadık.

## Yeniden hazırlama

Önce Blender ile `prepare_tripo_prologue_assets.py`, ardından
`probe_prologue_geometry.py` çalıştırılır. Sonra derlenmiş projede
`prepare_prologue_scene.py` Unreal Python betiği çalıştırılır (`REDLINE_REPO`
depo kökü). Ham model ve onaylı idle/walk dosyaları değiştirilmez. Oturma
klibi kaynak idle'dan yeniden türetilir; tekrar çalıştırma kökü aşağı kaydırmaz.

Türkçe sesi yeniden üretmek için WSL'deki ayrı Chatterbox venv'i ile
`scripts/generate_chatterbox_prologue.py all` çalıştırılır. Model, kaynak
revizyonu, bağımlılık dökümü ve RTX 5080 CUDA kontrolü
`assets/narrative/prologue_v1/chatterbox/runtime/` altında kayıtlıdır. Büyük
model ağırlıkları depo dışında, kullanıcı cache'inde kalır.

Bu açılış, T6 kabulünün yerine geçmez. S1 alarmı, çizginin daralması,
SpaceWeather ve tamamlanmış hikâye/oyunculuk ayrı işlerdir.
