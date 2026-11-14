# Research yayın kontrolleri

Kontrol kaydı: **2026-11-14T12:26:07+03:00** · Europe/Istanbul.

| Kontrol | Sonuç |
|---|---|
| Dosya envanteri | 567 dosyanın tamamında boyut ve SHA256 eşleşti; 0 hata. |
| Tarih biçimi | Her dosya kaydının oluşma/aktarım ve son yazma zamanı saat dilimi içeriyor. |
| Okuma dizini bağlantıları | Ana README ve Research README içindeki 79 yerel bağlantı çözümlendi; kırık bağlantı yok. |
| Proje skill bütünlüğü | 18 skill, 428 kayıtlı dosya; 0 sorun, exit 0. |
| Kullanıcının son metni | Ek ile `proje.md` SHA256 eşleşti. Spekle satır sonları normalleştirildiğinde aynı içerik. |
| Kimlik bilgisi taraması | Yaygın canlı GitHub/Tripo/OpenAI anahtar biçimleri ve private-key başlangıçları için dosya taramasında eşleşme yok. Bu, her olası sırrı kapsayan bir güvence değildir. |
| Hedef repo | `ahmetefesensoy/redline`, private; remote `origin`. |
| Yayın öncesi Git | Fetch sonrası HEAD ile origin/main eşit (0/0). |
| Stage kapsamı | 570 dosya: 567 envanter girdisi ve üretilen 3 Research sunum dosyası. |
| Yeni yayın belgelerinin biçimi | CRLF'yi satır sonu olarak ele alan `git diff --cached --check` yeni/değiştirilen sunum belgelerinde geçti. |

Tüm arşivdeki ilk whitespace kontrolü, korunmuş CRLF satır sonları ve tarihsel dosyaların mevcut satır sonu boşluklarını bildirdi. Araştırma/skill kaynaklarının hash'lerini korumak için özgün dosyalar normalize edilmedi. Biçim kontrolü bu yayında düzenlenen sunum belgelerine uygulanarak geçti.

Bu kontroller araştırma yayınının bütünlüğüne aittir. Uygulama pytest/colcon/Unreal testleri değildir; T0 tamamlanmadı.

Kesin commit kimliği ve yayın tarih/saatleri [bu reponun Git geçmişinde](https://github.com/ahmetefesensoy/redline/commits/main/) görülebilir. Bu dosya yayın öncesi kontrol anını kaydeder. Üretilen `research/` dizini, kendi kendine hash döngüsü oluşmaması için `FILE_TIMESTAMPS.json` envanterinin kapsamı dışındadır.
