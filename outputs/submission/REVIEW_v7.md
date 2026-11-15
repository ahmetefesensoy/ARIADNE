# REDLINE 30 saniye v7 incelemesi

15 Kasım 2026, 16:01–16:05 +03 · İncelenen dosya: `REDLINE_30s_v7.mp4`.

Karar: Sunum taslağı olarak kullanılabilir; aşağıdaki doğruluk ve okunabilirlik sorunları giderilmeden final teslim olarak önermiyorum. MP4 ve render betikleri değiştirilmedi.

SHA-256: `5F5155ABE3470417DD716FDC9EE2BBA624FC3C8C47B17DA165F30603C600820C`.

İnceleme: MP4'ten çıkarılan iki saniye aralıklı kareler, 12,9 ve 18,8 saniyede tam çözünürlüklü kareler; render betikleri, kaynak kayıtları ve yerel iddia defteri. Ses kanalı teknik olarak kontrol edildi; dinleyerek müzik/miks değerlendirmesi yapılmadı. Yarışma kurallarına uygunluk bu incelemenin kapsamında değil.

| Öncelik | Zaman | Bulgu | Düzeltme |
|---|---|---|---|
| Yüksek | 20,5–26,5 sn | Küçük Unreal penceresinde `same run (replay)` yazıyor. Büyük harita `C1_SOL4190_CHAPTER`, küçük pencere `C1_SHOT` kaydından. Aynı koşu değiller. | Aynı kaynak koşuyu kullan veya `Separate Unreal replay of the storm scenario` yaz. |
| Yüksek | 3–6 sn | `Earth is 32 min away` tek yön süresi gibi okunuyor. Yerel `light_time` kanıtı tek yön 15,84; gidiş-dönüş 31,67 dakika veriyor. | `About 32 min for a question and an answer` kullan. |
| Yüksek | 15–17 sn | Drone, stabilizasyon öncesi videonun 44–46. saniyesinden. Kaynağın faz kaydına göre hâlâ TAKEOFF; SURVEY yaklaşık 52,8 saniyede başlıyor. Bu kesit `costliest unknown first` seçimini göstermiyor. | Stabil uçuş/araştırma kesiti çek; hedef seçimini ayrıca kanıtlamıyorsan yazıyı `ROS-controlled scout flight` olarak daralt. |
| Orta | 12–15 sn | Gazebo var, fakat beyaz zemin ve geniş boşluk sahneyi eksik gösteriyor. RViz'de maliyet haritası ve plan çizgisi seçiliyor; üç saniyelik ayrı zamanlardan alınmış üçlü görüntü tamamlanmış engelden kaçınmayı göstermiyor. Unreal yakın planında kayalar görünmüyor. | Rover ve kayaçları aynı kadrajda tutan sürüş çekimi kullan; üç paneli büyüt, konu adlarını kaldır. Ayrı kaydedildikleri açıklaması kalsın. |
| Orta | 17–20,5 sn | Altı kutu aynı anda 3,5 saniye duruyor. pH/iletkenlik grafikleri mevcut ama ekran içindeki ekran olarak küçüldükleri için okunmuyor. Numune alma ve XRF kutuları benzer ayakta duran astronot görüntüsü veriyor. `12 linked tasks` yazısı bütün görevlerin oynanarak tamamlandığı kanıtı değil. | İki veya üç belirgin eylem ve okunabilir tek bir bilim çıktısı göster; diğer görevleri uzun demoya bırak. |
| Orta | Video geneli | Render yalnız müzik dosyasını bağlıyor; oyun sesi, alarm, motor/kapı efektleri ve seslendirme bu miksin içinde yok. | İstenen oyun hissi için seçili efektleri müziğin altına ekle. |
| Düşük | 0–12 sn ve kapanış | İlk altı saniyede aracın/görüntünün bağlamına göre fazla metin var. Yüzeyin yakın planı yumuşak görünüyor. Son kartta küçük kaynak satırları 30 saniyelik akışta okunması zor. | Açılışı tek somut soruya indir; dünyayı anlatan iki planı birleştirerek bilim/otonomi bölümüne süre ayır. Ayrıntılı kaynaklar teslim metninde kalsın. |

## Kaynak tutarlılığı kontrolü

- `render/run_compact.json` alarmı: 714,4713065900014 saniye. `runs/20261115T101234Z-C1_SOL4190_CHAPTER-42/ue_feed.jsonl` ile alarm, alarm öncesi ve sonrası poligonlar birebir eşleşti.
- `test-results/storm-video/source.json` küçük Unreal replay kaynağını `runs/20261115T105748Z-C1_SHOT-42/ue_feed.jsonl` olarak kaydediyor. Bu kaynakta ilk alarm 124,10298218800017 saniye; compact kaydın alarm sonrası poligonu birebir bulunmadı. Kontrol betiği: `test-results/v7-review/check_sources.py`.
- Drone fazları ve kalite notu: `outputs/raw-takes/02_drone_aciklama.json`.
- Süre iddiası: `docs/verification/SPACE_APPS_CLAIMS.json`, `light_time`.
- Kayaçlar Tripo üretimi değil: `assets/incoming/rock_07/SOURCE.md` bunları Poly Haven / Jenelle van Heerden / CC0 olarak kaydediyor.

## Teknik kontrol ve teslim dosyaları

MP4: 30,000 saniye, 1920×1080, 30 fps, H.264; ses AAC, stereo, 48 kHz. Ses örnek tepe seviyesi −5,1 dBFS; örnek tepesinde kırpılma görünmüyor. Bu ölçüm dinleyerek miks değerlendirmesi yerine geçmez.

`STORYBOARD_30s.md` v5'e; `CREDITS_AND_AI.md` ilk sürüme ait. İkisi de v7 kesimlerine göre güncellenmeli. `SUBMISSION_TEXT.md` hâlâ `[VIDEO_LINK]`, `[GITHUB_LINK]` ve kontrol notları içeriyor; doğrudan teslim edilecek son metin değil.

Güçlü taraf: gerçek veri haritası, alarm ve dönüş alanının daralması projeyi anlaşılır kılıyor. Bu yapıyı koruyup kaynak ifadelerini ve robot/bilim kesitlerini düzeltmek yeterli; bütün videoyu yeniden tasarlamak gerekmiyor.
