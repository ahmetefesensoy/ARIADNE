# REDLINE v3 ilerleme kaydı

14 Kasım 2026 · Bu kayıt yeni `ahmetefesensoy/redline` deposuna aittir.

## Güncel durum

Başlangıç paketi aktarıldı, bütünlüğü doğrulandı ve gerçek makinenin ilk envanteri çıkarıldı. **T0 henüz tamamlanmadı.** Kullanıcı detaylı uygulama/kod dosyasını ayrıca göndereceğini belirtti; bu aşamada uygulama kodu, ROS mesaj paketi, venv, Unreal projesi veya CI oluşturulmadı.

## Tamamlanan hazırlık

- Kaynak paket aynı bilgisayarda bulundu: `C:\Users\USER\Desktop\space apps\output\handoff\REDLINE_V3_BASLANGIC_PAKETI.zip`.
- Yeni çalışma klasöründe yalnız `.git` vardı. Arşiv yolları, tekrar eden girdiler, mevcut dosyayla çakışma ve symlink girdileri kontrol edilerek paket çıkarıldı.
- Manifestteki 561 dosyanın boyutu ve SHA256 değeri eşleşti.
- `.agents/skills` altındaki 18 skill ve 428 kayıtlı dosya, sağlanan bütünlük aracıyla doğrulandı; sorun sayısı 0.
- `YENI_DEPO_AKTARIMI.md`, uygulama speki §0–4 ve §18, v3 kılavuzu, yeni depo `AGENTS.md`, README ve `redline-space-apps/SKILL.md` okundu.
- Windows/WSL çalışma zamanı, UE sürüm kaydı, C++ araç envanteri, ROS/Gazebo paketleri ve localhost erişimi kontrol edildi. Kanıtlar: [VERIFICATION_LOG.md](VERIFICATION_LOG.md).

## Uygulamanın esası

- BXW ileri EVA; YKB kalibrasyon/tutarlılık; tek EVA'nın beş evresi.
- İlk dikey hat spek §18.1'dir: BXW → çekirdek çizgi → ROS FieldTile/RedLine → Unreal → RAD4190 → alarm/çizgi daralması.
- Robot fiziği/kontrolü ROS/Gazebo'ya, insan sunumu ve etkileşimi Unreal'a aittir.
- Eski uygulama kodu taşınmadı; araştırma ve üçüncü taraf skill/helper dosyaları önceden var olan malzemedir.
- Fizik `/clock` ile görev/PET saati ayrılır. NASA ölçümleri ile DERIVED/SIMULATED/SCENARIO veriler karıştırılmaz.
- Eski belgelerdeki [D]/[K] işaretleri bu yeni depoda yeniden yapılmış test olarak sunulmaz.

## Sonraki çalışma

Kullanıcının detaylı dosyasını okuyup mevcut v3 sözleşmeleriyle karşılaştır. Ardından T0'ı sıfırdan uygula: repo iskeleti, venv, `redline_msgs`, colcon derlemesi, pytest ve CI. T0 ancak gerçek `colcon build` ve `pytest` başarı kanıtlarıyla tamamlanmış sayılacak. Henüz T1 veya daha ileri bir taş tamamlanmış değildir.

İlk ortam hazırlığında yeni bağımlılık yükleme veya editör başlatma yapılmadı.

## Research yayını

Kullanıcının isteğiyle bu depoda “Proje fikri / Research” dizini hazırlandı. `proje.md`, v3 belgeleri, araştırma/metadata kayıtları ve geliştirme rehberleri araştırma başlangıcı olarak commit ve push edilecek. Dosya tarihleri ile gerçek Git commit zamanı ayrı gösterilir; `research/FILE_TIMESTAMPS.json` boyutları ve SHA256 değerlerini de saklar. `proje.md` son paylaşılan metinle byte düzeyinde eşleşir; spekle satır sonu dışında içerik farkı yoktur. Bu yayın T0'ın tamamlandığı anlamına gelmez.
