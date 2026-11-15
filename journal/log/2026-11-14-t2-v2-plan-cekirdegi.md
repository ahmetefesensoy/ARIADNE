# T2 v2 kararları ve plan çekirdeği — 14 Kasım 2026

Claude Code oturumu. Kullanıcının yönlendirmesi: "sorunları en kolay değil, en harika sonucu getirecek şekilde seç, kestirme yapmadan; benim karar kısımlarında da öyle".

## Ne yapıldı

**Kararlar (D010), her biri kanıtla:**
- σ: Gale DEM v3 ile HiRISE DTM'nin aynı stereo çiftten geldiği FGDC soyağacında görüldü. İki işlemenin topluluğu kuruldu ve Kirk ve ark. (2008) hassasiyet tabanı eklendi. BXW yasak oranı %38,9 → %28,9 oldu; eşik değiştirilmedi.
- Giysi maliyeti: EWT (NASA/TP-2009-214796) Tablo 5 verisine göre hızla orantılı modellendi. Dijkstra artık mesafe taşıyor. EV1 ayakta 708 → 236 W, nominal yürüyüş 756 → 486 W.
- Giysi kapasitesi: Apollo J-PLSS tasarım noktası (8 sa × 1200 Btu/sa), 30 dk OPS rezervi. Mars nominal yürüyüşünde dayanıklılık 5,8 sa.
- Habitat: MSL iniş eğim limitleri + 60 dk erişim alanını en büyüten yer seçimi → (290, −454) m. Erişilebilir alan %26,9 → %61,9.
- Kaya λ geometrik olarak 1,45 s. Gösterim çizgisi için köşe bütçesi ve 1/16 m yuvarlama: RedLine çerçevesi 317 → 111 KB.

**Plan çekirdeği (D011):** `science_value` (tam ortak bilgi kazancı), `orienteering` (pencereli, PET geçerlilikli; Held–Karp tam referansı ve boşluk raporu), `targets` (TPI ile sırt/çukur), `voi` (yerel yeniden yönlendirme), `eva_plan`; ROS'ta `planner_server` (`/redline/plan_eva`).

## Gözlenen sonuçlar

- Python: 538 test geçti (`test-results/t2v2-python.xml`). ROS: 22 test sonucu, 0 hata (`test-results/t5-build-pAiG4PGh`).
- BXW v2 harita: `data/derived/BXW/margin-v2-20261114T174827Z/`. T2 ile karşılaştırılabilir 40 dk anlık görüntüde güvenli alan 0,47 → 1,32 km².
- BXW T5 koşusu v2 (120× PET): `test-results/t5-bxw-20261114T175411Z-T5_THREAD_BXW-0`. Pay 285 → −109 dk; çizgi tamamen kapandı (dayanıklılık aşıldı); RedLine en çok 111 KB, tick 68 ms. Bir önceki deneme nedeni kaydedilmemiş bir yürüyücü hatasıyla düştü; betik artık yürüyücü çıktısını `walker.log`'a yazıyor.
- BXW PlanEva: SCIENCE 4 istasyon, 0,692 bit, 229 dk; SAFE ve FAST 3 istasyon, 165 dk, pay 154 dk. Üç hedefte boşluk 0. VOI aday başına medyan 23 ms.

## Açık işler

- Mars giysi verisi tek bir analog çalışma; hız modeli muhtemelen temkinli. σ yer gerçeği kalibrasyonu T12'de (PLACES eğimi, sol < 4533).
- Bilim gözlem modeli olasılıkları ve istasyon süreleri SCENARIO; T8 verisiyle gözden geçirilecek.
- PlanEva bacak maliyetleri istekler arasında önbelleklenmiyor (≈ 7 s).
- Unreal tarafı (T5 kabulü) değişmedi: T4 ve kullanıcıyla görsel çalışma bekleniyor.
