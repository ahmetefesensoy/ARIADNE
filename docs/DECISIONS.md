# Karar kaydı

## D001 — Fikir aşamasından uygulamaya geçiş

14 Kasım 2026 · Kullanıcının açık yönlendirmesi.

- Fikir aşaması tamamlandı. Kodlamanın esası kökteki `proje.md`; destekleyici fikir/tasarım gelişimi `research/proje-fikirleri/` altında.
- `önceki deneme` güncel çalışma ağacından çıkarılır ve uygulamaya kaynak olarak geri alınmaz. Normal silme commit'i kullanılır; geçmiş yeniden yazılmaz.
- Üçüncü taraf skill/helper dosyaları ve lisansları korunur. Yalnız yerel `redline-space-apps` skill'inin belge bağlantıları değişti ve dosya hash'i manifestte güncellendi.
- T0'dan itibaren ROS Jazzy + Python 3.12 altyapısı, mesaj sözleşmeleri ve testler sıfırdan yazılır. Unreal 5.8.4 ilerleyen entegrasyon aşamasıdır.
- Ekran görünümü, sahne, malzeme ve 3D varlık tasarımları kullanıcıyla birlikte yapılacaktır. Bu aşamada model üretimi veya ücretli görsel API çağrısı yapılmaz.
- Fikir gelişimi SVG'si yalnız doküman şemasıdır; ürün arayüzü veya 3D tasarımı değildir.

## D002 — T0 sınırı

14 Kasım 2026 · Spek §18 ve mevcut makine envanteri.

T0 için `redline_core`/`redline_data` paket temelleri, eksen/birim ve saat sözleşme testleri, §5 ROS arayüzleri ve pytest/colcon CI kurulur. Veri işleme/rota algoritmaları T1/T2 kabul kapılarından önce tamamlanmış ilan edilmez. `CollectSample` gibi §5'te karşılığı olmayan adlar uydurma bir arayüzle doldurulmaz; belirsizlik günlüğe yazılır.

## D003 — ROS arayüzleri ve build kökeni

14 Kasım 2026 · İlk T0 derlemesi/testleri.

- Esas belge düzenleme sonrasında `docs/proje.md` yolundadır. Günlük `journal/PROGRESS.md` altındadır. Bu taşıma kararları uygulama sözleşmelerini değiştirmez.
- §5'teki 22 msg, 5 srv ve 11 action alan/tipleri uygulanır. Ortak aksiyon Result sabitleri §5.3 metnindeki SUCCEEDED/PARTIAL/CANCELED/FAILED/REJECTED = 0/1/2/3/4'tür. Şema değişikliği ayrı kararla izlenir.
- `FieldTile.nodata_byte` uint8, dokümanda PNG 8/16-bit olarak geçiyor. Şema aynen korunur; 16-bit nodata üretim/çözümleme kuralı sonraki veri/bridge aşamasından önce doğrulanacaktır.
- ROS derlemesi, Unicode Windows yolunun yerel rosidl configure hatası nedeniyle içerik hash'leri eşleşen, yeni ASCII Linux workspace'inde yapılır. Eski overlay veya derleme artığı test kanıtı sayılmaz.
- Yeni kod için açık lisans seçimi henüz yapılmadı; ROS manifestinde `LicenseRef-Project-Pending` ve geçersiz örnek maintainer adresi açık placeholder'dır. Üçüncü taraf lisansları bu karardan etkilenmez.

## D003 — Depo düzeni (hackathon yayını)

14 Kasım 2026 · Kullanıcının yönlendirmesi.

- Depo GitHub/hackathon için düzenlendi: kökte yalnız README, `docs/`, `journal/`, `research/` ve kod/altyapı klasörleri bulunur.
- Bütün fikir ve araştırma aşaması `research/` altına toplandı (`research-notes` → `research/notes`, `output/jupyter-notebook` → `research/notebook`, `docs/source-history` → `research/history/source-history`).
- Kullanıcının nihai uygulama belgesi `proje.md` → `docs/proje.md` (içeriği değişmedi). Kod içi `proje.md §…` atıfları bu belgeyi gösterir.
- Yapay zekâ asistanı dosyaları (`AGENTS.md`, `.agents/`, `optional-user-skills/`) yerelde kalır, `.gitignore` ile yayından çıkarıldı; CI'daki skill bütünlük adımı kaldırıldı. Üçüncü taraf skill kaynak/lisans kayıtları `research/proje-fikirleri/SKILL_PLANI.md` ve önceki commit geçmişinde durur.
- İlerleme günlüğü `journal/` altında tarih sıralı tutulur.
