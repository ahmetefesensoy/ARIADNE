# Önceden var olan çalışma

14 Kasım 2026 tarihinde `REDLINE_V3_BASLANGIC_PAKETI.zip`, yerel araştırma deposundan bu yeni depoya aktarıldı. Kaynak, hash ve bütünlük sonuçları [VERIFICATION_LOG.md](VERIFICATION_LOG.md) içinde kayıtlıdır.

Aktarılan v3 tasarım/spek, eski tasarım belgeleri, araştırma notları, konsey çıktıları, metadata/provenance kayıtları ve araştırma not defteri önceden var olan çalışmalardır. Yeni uygulamanın çalıştığını kanıtlamazlar. Eski ROS/web/rover uygulama kodu aktarılmadı.

`.agents/skills` içindeki 18 skill ile `optional-user-skills` içindeki 26 referans skill, kaynak ve lisans kayıtları korunarak taşındı. `optional-user-skills` kopyaları kullanıcı profiline ayrıca kurulmadı. Üçüncü taraf scripts/helpers ve `tools/verify_skill_installation.py` önceki geliştirme araçlarıdır; yeni yazılmış REDLINE uygulama kodu olarak sunulmazlar. Kaynak sürümleri ve dosya hash'leri skill manifestlerinde bulunur.

Bu yeni hazırlıkta yazılanlar: `docs/PROGRESS.md`, `docs/VERIFICATION_LOG.md` ve bu belge. Ayrıca uygulama kodu yazmadan makine envanteri ve geçici HTTP localhost deneyi yapıldı. Sonraki Research yayınında README okuma dizini, `research/` tarih/hash kayıtları ve `docs/AI_DISCLOSURE.md` eklendi. Bunlar araştırmanın sunumu ve kayıtlarıdır.

Kullanıcının önceki oturumda ürettirdiği Tripo astronotunun yedeği kullanıcı profilinde kalır; başlangıç paketine veya bu yeni çalışma ağacına kopyalanmadı. Tripo anahtarları, kişisel Codex ayarları ve hesap oturumları bu depoya taşınmadı.

## Güncel düzenleme

Kullanıcının son yönlendirmesiyle ilk aktarımda bulunan `önceki deneme` altındaki 6 araştırma/provenance dosyası güncel ağaçtan kaldırıldı. Önceki yayın commit'inde geri alınabilir; Git geçmişi yeniden yazılmadı. Fikir ve tasarım notları `research/proje-fikirleri/` altına taşındı, aktarım belgeleri `research/handoff/` altında tutuldu. İlk yayın envanteri `research/history/` altında tarihsel haliyle korunur; mevcut dosya listesi değildir. `proje.md` içeriğinin yalnız belge bağlantıları yeni yollara uyarlandı.
