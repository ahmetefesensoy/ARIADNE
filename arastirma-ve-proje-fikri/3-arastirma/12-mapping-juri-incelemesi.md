# REDLINE — Sert Space Apps mapping incelemesi

> **Araştırma 12 / 16** · Aşama 3 — Eleştiri turları ve v2 kılavuzu · Dosya oluşturulma: 13 Kasım 2026 23:49 · [← 11](11-proje-kilavuzu-v2.md) · [Dizin](README.md) · [13 →](13-saha-ve-bilim-istasyonu.md)
>
> Bu bir araştırma/fikir kaydıdır; güncel proje [nihai proje](../2-nihai-proje/README.md) bölümündedir.

13 Kasım 2026 · Varsayımsal jüri eleştirisi · Resmî değerlendirme veya puan değildir.

**14 Kasım düzeltmesi:** Bu sert eleştirinin bazı testleri gereksinim gibi fazla katı ifade edilmişti. Aşağıdaki §8 güncel değerlendirmeyi belirtir; uygulama kapsamı [ana kılavuzun sürüm 2'sidir](11-proje-kilavuzu-v2.md).

**Hüküm:** Tasarım challenge'ı kavramsal olarak içeriyor; ana ürün kimliği ise harita/karar aracından geniş bir robotik eğitim oyununa kaymış. Çalışan çoklu NASA veri entegrasyonu henüz gösterilmedi. Araştırma dokümantasyonu güçlü, yarışma katkısının kanıtı açık. Bu ayrım “henüz tasarım” notuyla dürüstçe açıklanabilir ama o not uygulama kanıtının yerine geçmez.

Bu inceleme yeni kapsam önerisidir; ana kılavuz bu turda otomatik yeniden yazılmadı.

## 1. Challenge'ı hangi ölçüte göre okuyoruz?

Kullanıcının sağladığı metnin çekirdeği: Mars'ta belirli bir konum/rota, birden çok NASA görevinin verileri, katmanlı bütünleşik görünüm ve insanın bilim yürüyüşüne yardım. Başlıktaki survival bunu genel bir hayatta kalma oyununa dönüştürmez. Amaç harita, araç veya arayüz olabilir; 2B olmak zorunda değildir. Habitat ekranı, tablet ve robot desteği olası biçimlerdir. “Üç veri türü” öneridir; ayrı zorunluluk gibi sunulmaz. Güvenlik bağlamı, doğrulanmış bir yaşam destek modeli yazma mecburiyeti oluşturmaz.

[Resmî sayfa](https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/) bu incelemede yine 502 verdi. Ayrıntılar [yerel organizatörün challenge kopyasıyla](https://hackathlone.com/challenges/interplanetary-survival-guide-martian-map) karşılaştırıldı; resmî metin nihai kaynaktır.

## 2. En sert sekiz itiraz

| İtiraz | Mevcut açık | Yarışma odağına dönüş |
|---|---|---|
| “NASA verisini çıkarınca oyun neden değişmiyor?” | Vana, kap, kol ve bazı hikâye işleri sentetik başka bir gezegende de çalışabilir | NASA ürününün erişim, bilim durağı veya rota kararındaki etkisini göster |
| “Birleşen veriyi gösterin; cihaz adlarını değil.” | Yerel DEM/LRGB var; bağımsız sahaya eşlenmiş yer bilimi/diğer görev ürünleri çoğunlukla aday | Ürün ID/sürüm → yer/zaman → katman → insan kararı zinciri |
| “Astronot gerçekten nerede, neden yürüyor?” | Nihai bilim AOI'si seçilmedi | Belgeli hedef/ölçümden başlayıp sahneyi onun çevresinde kur |
| “Haritanızın bilmediği yer nerede?” | 4 m ağ, yerel ayak/teker engeli çözmez; senaryo taşları NASA ölçümü değil | Yörünge ön bilgisi, simüle yerel gözlem ve eksik alan ayrı |
| “Güvenli rota sözünü neyle doğruladınız?” | İnsan kaynak/çevre etkisi parametreleri varsayımlı | Açık model altında rota/dönüş seçenekleri ve duyarlılık; kesin güvence yok |
| “Yanlış asistanı yakalama bu challenge'a ne katıyor?” | AI güveni eğitimi bağımsız ürün olabilir | Normal danışman kaynak/harita açıklasın; hata profili ek eğitim modu |
| “pH, gaz, mineral listesi neden gerekli?” | Ölçüm çeşitliliği bilim amacının önüne geçebilir | Tek araştırma sorusu ve o soruya gerekli örnek/cihaz/konum |
| “Basit bir haritadan daha iyi olduğunuzu nereden bilelim?” | Bilgi etkisini tahmin eden model ve adil karşılaştırma henüz yok | Keşifsiz/genel keşif/görev odaklı keşif koşuları; sonuç ve maliyet |

Yerel [AOI incelemesi](02-gale-aoi-ve-places-kontrolu.md), sorgulanan iki tabloda konum örneği bulamadı. Bu görüntü yokluğunu kanıtlamaz; fakat hedef–yer gözlemi–arazi bağı henüz tamamlanmadı. [Katalogdaki](10-kaynak-ve-varlik-katalogu.md) adayları uygulanmış veri birleşimi gibi sunmamak gerekir.

## 3. Survival'ı somut karara çevirmek

Savunulabilir sorular: Bu hedefe gidilmeli mi? Hangi koridor hangi kanıtla tercih ediliyor? Nereyi önce gözlemek gerekiyor? Yeni veri dönüş planını değiştiriyor mu? Bilim durağında ne kadar iş yapılabilir? Veri yetersizse hangi hedef ertelenir?

Bağımsız kolonizasyon, habitat ekonomisi, ayrıntılı yaşam desteği, her cihazın tam fiziği ve çok sayıda dramatik arıza bu sorulara katkısı gösterilmedikçe ana gösterimi büyütür. Robotlar astronota yardım edebilir; bu yardımın challenge karşılığı, harita ve insan görevi üzerinde gözlenebilir değişikliktir. Her yardım özelliği aynı ölçüde mapping katkısı sağlamaz.

## 4. Özelliklerin ağırlığı

| Özellik | Önerilen yeri |
|---|---|
| Coğrafi olarak tutarlı çoklu NASA katmanları | Ana ürün; başarım gösterimi için zorunlu çekirdek |
| Kaynak/çözünürlük/eksik veri ve bilim hedefleri | Ana ürün |
| Astronot için rota, alan ve dönüş karşılaştırması | Ana ürün |
| Rover/drone ile hedefli gözlem ve harita güncellemesi | Güçlü teknik ayrıştırıcı; simülasyon olduğu açık |
| Unreal habitat ve saha görünümü | Haritayı kullanma/prova arayüzü |
| Kaynaklı normal asistan | Harita kararını açıklayan destek |
| Numune/sondaj | Kaynaklı bilim durağının işlemi; gereken derinlikte |
| Manuel sürüş | Gözlem/görev müdahalesi için kontrol biçimi |
| Vana ve ayrıntılı bakım | İkincil senaryo; ana jüri hikâyesini taşımamalı |
| Kontrollü hatalı asistan ve sınav | Ek eğitim/araştırma profili |

Büyük mühendislik kapsamı korunabilir; sunumdaki ve geliştirmedeki birincil bağımlılık harita çekirdeği olmalıdır. Bir vana animasyonunu bitirmek veri entegrasyonundaki açığı kapatmaz.

## 5. Beş görevi yeniden ağırlıklandırma önerisi

1. **Sahayı anla:** Kaynaklı bilim hedefi ve harita katmanlarını incele; veri eksiğini saptayıp hedef seç.
2. **Seferi planla:** Astronot için alternatif rota ve dönüş seçeneklerini açık model altında karşılaştır.
3. **Belirsizliği azalt:** Rover/drone gözlemini seç; yeni kanıtı haritada göster ve planı güncelle.
4. **Bilim durağını yürüt:** Hedef bağlamını doğrula, uygun gözlem/numune al; sonucu haritadaki bilim kaydına bağla.
5. **Yüzeyde uyarlan:** Güncel bilgiyle hedef/rota/geri dönüş kararını değiştir; sonuçları kanıtlarıyla değerlendir.

Eski numune, drill ve vana mekanikleri uygun durağın alt işlemleri veya ek kampanya profilleri olabilir. Bu öneri beş ayrı robotik mini oyundan tek insan seferi karar döngüsüne ağırlık verir.

## 6. Sunulabilir çekirdek hikâye

“Astronot iki belgeli bilim durağını ziyaret etmek istiyor. Katmanlı NASA haritası hedefleri ve erişim bağlamını gösteriyor; bir koridorun yerel verisi eksik. Sistem, hangi robot gözleminin kararı etkileyebileceğini öneriyor. Yeni simüle gözlem kendi kaynağı ve belirsizliğiyle haritaya ekleniyor. Astronot rotayı veya bilim hedefini değiştiriyor; dönüş seçeneklerini kontrol ediyor.”

Gösterimde önce gerçek konum ve iki NASA görevinin somut katkısı açılır. Sonra yerel veri eksiği ve gözlem gelir. En sonda yeni karar görülür. Habitat sinematiği, vana veya asistan hatasıyla başlamak bu merkezi zayıflatabilir.

## 7. Tasarımı sorgulama soruları

- Seçilen sahadaki her bilim durağı ürün/konum/ölçüm bağlantısıyla açılabiliyor mu?
- İkinci NASA görevi anlamlı bir bağlam veya karar katkısı sağlıyor mu? Katman yalnız görünümde mi?
- Veri çözünürlüğü ve bilinmeyen alan kullanıcıya dürüstçe gösteriliyor mu?
- Yeni robot gözlemi haritayı, insanın kararını veya kararın dayanağını değiştirebiliyor mu?
- Robotların hangi bilgiyi veya işi sağlayarak yürüyüşe katkı verdiği gösterilebiliyor mu?
- NASA ürünleri çıkarıldığında kaybolan somut işlev gösterilebiliyor mu?
- Varsayım değişince öneri değişiyorsa kullanıcı bunu görebiliyor mu?

Bu sorular bilim/ürün katkısını incelemek içindir; her biri ayrı challenge şartı veya otomatik ret ölçütü değildir. Açık kalan temel iş, gerçek saha ve veri birleşiminin insan yürüyüşü/bilim görevine katkısının gösterilmesidir.

## 8. 14 Kasım — Eleştirinin sınırı ve güncel karar

Konuşmalı asistan ve bilerek yanlış tavsiye sınavı kullanıcı kararıyla kapsamdan çıkarıldı. Unreal, katmanlı harita, path planning, manuel/otonom rover, drone ve bilim/numune görevleri korunuyor.

Önceki şu iddialar gereksinim değildir: robot çıkarıldığında ürünün aynı derecede faydalı kalması; her NASA görevinin ayrı bir aç/kapat katmanında olması; her katman kapandığında rotanın değişmesi; her bilim ölçümünün rota kararını etkilemesi. Çok görevli girdilerle üretilmiş bir ürünün kökeni geçerli katkı olabilir; kaynak ve işleme belgelenmelidir. Bağımsız ölçümler ve açık görünümler katkıyı anlatmayı kolaylaştırır, ancak zorunlu biçim sayılmaz.

Otonomi üç gerçek işlevle challenge'ı destekleyebilir: (1) robotun topladığı yerel gözlemle haritayı tamamlamak ve rotayı değerlendirmek, (2) bilim durağını incelemek/örneklemek ve konumlu sonucu astronota sunmak, (3) yürüyüş sırasında önden inceleme/refakat/ekipman desteğiyle insan iş yükünü ve görevin yürütülmesini desteklemek. Sonucun her seferinde plan değişikliği olması gerekmez; daha iyi bağlam, doğrulama veya tamamlanan bilim işi de katkıdır.

pH uygun numune/hazırlık/cihaz modeliyle bilim görevi olabilir. Yalnız “haritada sonucu var” demek bilimsel gerekçe değildir; araştırma sorusu, örnekleme konumu ve yorum gerekir. Phoenix arşiv kaydı yerel Gale ölçümü gibi sunulamaz. Bu veri doğruluğu eleştirisi korunur.

Vana görevinin katkısı daha dolaylıdır: sefer/laboratuvar altyapısının çalışmasını destekler. Kapsamda kalabilir; ana NASA veri birleşimi gösteriminin yerini alması zayıf bir sunum olur. Karmaşıklığın kendisi uygunluk veya uygunsuzluk ölçütü değildir.

Kalan gerçek açıklar: nihai saha/tekil ürün örtüşmesi, veri çözünürlüğü ve kökeninin korunması, simüle sensör ile gerçek ölçüm ayrımı, insan ve rover hareket profilleri, aynı kayıttan çalışan Unreal/ROS harita-görev döngüsü ve faydanın ölçülmesi. Güncel karar robotları geri plana atmak değil, bu bağlantıları uygulayıp değerlendirmektir.
