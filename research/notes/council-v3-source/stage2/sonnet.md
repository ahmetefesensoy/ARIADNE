# Stage 2 değerlendirmesi (Sonnet)

Doğrulama: yerel notlarda AOI (lat −4.825…−4.791, lon 137.428…137.462) ile John Klein hedefi (lat −4.5895, lon 137.449; HIRISE_YELLOWKNIFE_METADATA_KONTROLU.json ve APXS_HEDEF_ON_KONTROL.json) gerçekten ~0.22° (~13 km) arayla duruyor. D ve B'nin "kritik AOI kayması" bulgusu doğru ve yerel dosyalarla teyit edildi. Hassler 2014'ün sol 242 SEP olayı ve RAD'ın Eylül 2017 olayını görmesi bilinen gerçekler. Canlı arşiv iddialarını (A'nın PDS PPI blok değerleri, STAC kimlikleri) yeniden sorgulamadım.

## Response A
Güçlü yanlar: Brief'in istediği biçime en sadık yanıt. Challenge maddelerini numaralı alıntılarla (C1–C16) veriyor ve Resources'ın beşinin her birine somut işlev ve erişim yolu atıyor (Trek WMTS, SIM 3292, PIA23179, Worldview'dan A/B swipe, Perseverance raw API). Yalnız "aday" dememiş, salt-okunur sorgularla ölçüm düzeyine inmiş: sol 242 RAD blokları, Hassler ve Löwe ile çapraz kontrol, PLACES tilt ile DTM eğimi RMSE önerisi. APXS koordinatının aslında rover pozu olduğu bulgusu AGENTS.md'deki "numune kökeni ≠ analiz konumu" ilkesine doğrudan oturuyor ve özgün. Retrospektif YKB doğrulaması (Grotzinger 2014, CRISM'in kili kaçırması) önce/sonra deneyine gerçek veri ayağı veriyor; jüri için güçlü bir hikâye. Doğrulanamayanları çok dürüst ve ayrıntılı listeliyor; sayıları "hesaplanmadı" diye işaretliyor.
Zayıf yanlar: Yerel AOI'nin John Klein'dan 13 km uzak olduğunu fark etmemiş; YKB'yi "Trek DEM kapsıyor" diyerek rahat geçmiş. Metin çok uzun ve yoğun; bazı doğrulama iddiaları (örn. "tek poligon 87.031 km²") tek turda okunamayacak kadar ayrıntılı. Çift astronot (E10) görece yüzeysel. Güvenlik ve EVA operasyonu (walkback, terminate/abort, sarf sınırlayıcı) neredeyse yok.

## Response B
Güçlü yanlar: Dürüst red-team; resmî sayfa açılamadı, "at least three" zorunlu mu öneri mi çelişkisini not etmiş. AOI/hedef 13 km kaymasını doğru yakalamış (K1) ve Resources'ta "0/5 kullanılıyor" tespiti isabetli. CheMin "preliminary" uyarısı ve bbox kontrolünün hizalama olmadığı uyarısı yerinde.
Zayıf yanlar: Çoğu veri iddiasını "açılmadı, doğrulanmadı" diye bırakıyor; brief'in istediği ürün/erişim/format somutluğu zayıf (Trek, USGS, Worldview, Perseverance hiç açılmamış). K2/K3 (PLACES sorgusunda sol 182/279 tutarsızlığı) kendi itirafıyla doğrulanmamış hafızaya dayanıyor; spekülatif. Eklentiler (G1–G8) büyük ölçüde mevcut kataloğun yeniden anlatımı; yeni NASA ürünü getirmiyor. Worldview'ı "Mars kapsamı doğrulanmadı" diye geçmesi, Worldview'ın Dünya aracı olduğunu bilmemek anlamına geliyor (D ve A bunu doğru kuruyor). "SEP için canlı akış yok" doğru bir uyarı ama çözüm üretmiyor: gerçek RAD olayını yeniden oynatmayı öneriyor ama hangi olay ve hangi dosya olduğunu vermiyor. Eleştirel değeri yüksek, ekleme değeri düşük.

## Response C
Güçlü yanlar: EVA operasyon mercekten en olgun yanıt: terminate/abort ayrımı, sınırlayıcı sarf, PET zaman çizelgesi, SEXTANT/BASALT bulgusu (gerçek süre tahminden uzun) ile güven katmanını "marj" üretmeye bağlama. Radyasyonun ALARA çerçevesinde anlatılması ve gerçek verinin akut öldürücü olmadığını saklamama önerisi doğru ve A ile örtüşüyor. Giysi/insan parametresini yayımlanmış EVA verisine bağlama (madde 6) diğerlerinde zayıf kalan bir boşluğu dolduruyor. Çift astronot + röle/viewshed fikri iyi. Etiketleri [D]/[H] ile ayırması dürüst.
Zayıf yanlar: NASA veri erişimi A kadar somut değil: RAD alan adı/birimi, DONKI, Navcam türev ürünleri, Trek uç noktaları hafızada veya doğrulanmamış. Eylül 2017 olay sayıları arama özetine dayanıyor ("2–3 kat"). AOI kaymasını fark etmemiş. Yellowknife istasyon adları (Rocknest, Point Lake, Shaler) hafızadan; bunlar Glenelg/YKB yolunda doğru ama "4–5 istasyonu 2 km'lik AOI'ye sığdır" sorununu (AOI hedeften uzak) görmüyor. Jezero yerine Gale boxwork önerisi iyi (challenge örneği) ama veri kapsaması doğrulanmamış.

## Response D
Güçlü yanlar: En kısa ve odaklı; AOI kayması (E1) doğru ve en öne konmuş. "Opsiyonel e" (rover-POV görüntü) en kolay kaçan istek olarak doğru işaretlenmiş. Resources'ı adlarıyla sayıp REDLINE'ın yalnız DEM kullandığını belirtmiş; Worldview'ı Dünya aracı olarak doğru okumuş. Kimlik yeniden çerçevelemesi (yürüyüş planlama haritası, görevler kanıt motoru) ve "veri soy ağacı / NASA ürününü çıkarınca çökmeli" fikri jüri açısından değerli.
Zayıf yanlar: Ürün/erişim ayrıntısı seyrek ve çoğu "doğrulamadım". Eylül 2017 SEP'i hafızadan. E10 (Dünya analoğu/Worldview) gereksiz dağınık; kendisi de öyle diyor. PROJE_KILAVUZU ve KAPSAMLI_ARASTIRMA okunmamış. Bazı eklentiler (E6, E7) ürün ID'si vermiyor. Beş görevi kesme çağrısı yapıyor: brief "kapsam tavsiyesi verme" dedi; "vana/kaçak/eğitim hiçbir şey katmıyor" demek sınırda.

## Hepsinin kaçırdığı
- Resmî jüri kriterleri ve ağırlıkları hiçbir yanıtta birincil kaynaktan okunmadı (A bile yalnız submission guide'ın beş adını verdi); "how the winners are picked" metnine erişim yok.
- Challenge'ın "one million images" ifadesi ve Perseverance raw görüntüleri için lisans/atıf (NASA medya kullanım kuralları) hiçbir yerde ele alınmadı; UE5'te gerçek görüntü gösterimi için gerekli.
- Gale için kamu DEM'in (1 m v3) John Klein çevresini kapsadığı hiçbir yanıtta ürünle doğrulanmadı (A Trek'te kapsama gördü ama USGS ürünüyle eşitliğini bilmiyor).
- Zaman/saat sözleşmesi: tarihsel solün (örn. sol 242) UE5/Gazebo saatine ve LMST/Güneş geometrisine bağlanması (SPICE) yalnız C'de değiniliyor, sözleşmeye bağlanmıyor.
- İnsan-otonomi (fikir 7) için challenge karşılığı ve değerlendirme ölçütü hiçbir yanıtta ele alınmadı.

FINAL RANKING:
1. Response A
2. Response C
3. Response D
4. Response B
