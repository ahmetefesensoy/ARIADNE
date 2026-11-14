# Brief: REDLINE fikrini Space Apps 2026 "Martian Map" challenge'ına göre geliştir (Türkçe yanıtla)

## Bağlam
Takım NASA Space Apps Challenge 2026'ya (Ankara, 14–15 Kasım 2026, 48 saat) katılıyor. Seçilen challenge:
"Interplanetary Survival Guide: Martian Map" — https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/
(Resmî sayfa daha önce SSL/502 hatası verdi; yerel organizatör kopyası: https://hackathlone.com/challenges/interplanetary-survival-guide-martian-map). Challenge metnini ve Resources listesini MUTLAKA kendin aç ve oku; açamazsan bunu açıkça yaz.

Karar verilmiş ve kapsam dışı:
- Ekip tamamen mühendislerden oluşuyor, 48 saat aralıksız çalışacak, yeni bir depoda sıfırdan başlayacak. **Kapsam/zaman kısıtı bu incelemenin konusu DEĞİL**; "kes, küçült" tavsiyesi verme. Fikrin kalitesine, challenge uyumuna, NASA veri kullanımına ve jüri etkisine odaklan.
- Yığın: ROS 2 Jazzy + Gazebo Harmonic (WSL) robot fiziği/kontrolü; Unreal Engine 5.8.4 (Windows) insan sunumu/etkileşimi; aralarında açık frame/birim/saat/komut sahipliği sözleşmeleri.

## Mevcut fikir (gözden geçirilecek konu)
REDLINE: Mars'ta bir insan bilim yürüyüşünü (EVA) NASA verileriyle planlayan, Unreal'da astronot gözünden prova ettiren ve yardımcı rover + hava aracının keşfiyle haritayı güncelleyen sistem. Şu an masadaki fikir parçaları:
1. **Canlı harita**: harita bir resim değil; drone tarar → rover doğrular → astronot yürür → numune → analiz → harita güncellenir. Beş görev tek zincir; her görev haritaya delta yazar, sonraki okur.
2. **Güven katmanı**: her hücrede kaynak, çözünürlük, yaş, güven; "harita neyi bilmediğini bilir"; arşiv / türetilmiş / simüle / senaryo ayrımı ekranda.
3. **REDLINE çizgisi**: O₂/süre bütçesi, giysi eğim kısıtı, sığınağa varış süresi ve güvenlik altında geri dönülebilir alanın sınırı; yeni kaya bulununca ya da SEP (güneş parçacık olayı) uyarısında canlı daralır.
4. **Saha**: Gale kraterinde Yellowknife Bay (Curiosity'nin ilk sondajı, John Klein / Cumberland). Gerçek veri adayları: MSL Gale DEM 1 m mozaiği, HiRISE ortomozaik, APXS/CheMin ölçümleri, Curiosity traverse (PLACES), MSL RAD, REMS. Simüle değerler açıkça etiketli.
5. **Önce/sonra deneyi**: yalnız yörünge verisi vs yörünge + robot desteği; simülasyonda çok koşulu Monte Carlo; metrikler: rotadaki bilinmeyen oranı, engel, süre, dönüş payı, sığınak süresi.
6. **Interplanetary**: gezegenden bağımsız manifest (CRS, ürün, kaynak, rol); ikinci saha (ör. Jezero) yalnız manifestle yüklenir.
7. **İnsan–otonomi**: otonom kararlar gerekçeli; astronot geçersiz kılabilir; açık komut yetkisi.
8. **Demo krizi**: rover beklenmedik kaya bulur, rota değişir, SEP uyarısı, dönüş sınırı daralır.
Beş görev (eski tasarımda): bilim/numune, sondaj, kaçak/vana müdahalesi (habitat), eğitim/sınav, keşif/haritalama.

## Okunabilecek yerel kaynaklar (salt-okunur)
Eski araştırma deposu (bu hackathon'da kod taşınmayacak, ama araştırma notları referans): `c:\Users\USER\Desktop\space apps\`
- `PROJE_KILAVUZU.md` (eski tasarım özeti, büyük — ilgili bölümleri oku)
- `KAYNAK_VE_VARLIK_KATALOGU.md` (NASA veri ürünleri D01–D16)
- `research-notes/SAHA_VE_BILIM_ISTASYONU.md`, `research-notes/APXS_HEDEF_ON_KONTROL.json`, `research-notes/SPACE_APPS_MAPPING_JURI_INCELEMESI.md`, `research-notes/Gale_PLACES_AOI_KONTROLU.md`
- `SPACE_APPS_KAPSAMLI_ARASTIRMA.md` (geçmiş kazanan projeler)
İnternette challenge sayfası, NASA PDS / Mars Trek / USGS Astrogeology / Space Apps jüri rehberi gibi birincil kaynaklara bakabilirsin.

## Soru
REDLINE fikrini challenge'ın **gerçek istekleri** (metinde açıkça yazanlar ve Resources listesi) ve **gerçek NASA verisi kullanımı** açısından nasıl daha güçlü yaparız? Somut eklemeler öner. Her öneride: hangi challenge maddesine / jüri kriterine hizmet ettiği, hangi NASA ürününü kullandığı (ürün adı/ID, erişim yeri, biçim) ve verinin ne işe yaradığı (simüle değil gerçek ölçüm mü?) belirtilsin.

## Çıktı formatı
1. Challenge'ın gerçek istekleri: madde madde, kaynağıyla (alıntı/URL). Mevcut fikir her birini ne kadar karşılıyor (iyi / zayıf / yok).
2. En değerli 6–10 eklenti/geliştirme, öncelik sırasıyla; her biri için: ne, neden (challenge maddesi + jüri kriteri), veri (ürün + erişim + gerçek/simüle), jüride nasıl görünür.
3. Mevcut fikirde değiştirilmesi/yeniden çerçevelenmesi gereken 3–5 şey.
4. Doğrulayamadığın iddialar.
