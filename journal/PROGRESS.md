# REDLINE v3 ilerleme kaydı

14 Kasım 2026 · Bu kayıt yeni `ahmetefesensoy/redline` deposuna aittir.

## Güncel durum

Fikir aşaması tamamlandı. Son uygulama belgesi `docs/proje.md`; fikir/gelişim belgeleri `research/proje-fikirleri/` altında. `önceki deneme` güncel depodan çıkarıldı. **T0 yerel kabulü geçti; GitHub CI sonucu doğrulanacak.** Görsel tasarım ve 3D varlıklar kullanıcıyla birlikte yapılacak.

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

T0 GitHub CI sonucunu doğrula, ardından T1 veri hattına geç. Henüz T1 veya daha ileri bir taş tamamlanmış değildir. Yerel T0 sonucu: 53 saf Python testi, ROS build, 98 interface pytest testi geçti. [T0 çalışma kaydı](log/2026-11-14-t0-altyapi.md) ve [doğrulama günlüğü](../docs/VERIFICATION_LOG.md).

İlk ortam hazırlığında yeni bağımlılık yükleme veya editör başlatma yapılmadı.

## Research yayını

Kullanıcının isteğiyle bu depoda “Proje fikri / Research” dizini hazırlandı. `proje.md`, v3 belgeleri, araştırma/metadata kayıtları ve geliştirme rehberleri araştırma başlangıcı olarak commit ve push edilecek. Dosya tarihleri ile gerçek Git commit zamanı ayrı gösterilir; `research/FILE_TIMESTAMPS.json` boyutları ve SHA256 değerlerini de saklar. `proje.md` son paylaşılan metinle byte düzeyinde eşleşir; spekle satır sonu dışında içerik farkı yoktur. Bu yayın T0'ın tamamlandığı anlamına gelmez.
