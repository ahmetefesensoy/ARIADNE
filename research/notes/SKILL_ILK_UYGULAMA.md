# REDLINE — Skill'lerin ilk uygulaması

14 Kasım 2026 · Kurulum, mevcut durum taraması ve metadata analizi

## Unreal bağlamı

`ue-project-context` iş akışıyla dosyalar tarandı. Yerel engine 5.8.4; depo içinde
`.uproject` yok. Haricî MyProject şablonunda C++ Source dosyası/modül bildirimi
bulunmadı. TopDown harita/GameMode, Enhanced Input sınıfları ve iki açık eklenti
kaydedildi; engine-default eklentilerin tamamı taranmadı.

Sonuç: [UE bağlamı](../.agents/ue-project-context.md). Yeni REDLINE projesi veya
köprü oluşturulmadı; eski şablon değiştirilmedi.

## NASA metadata notebook'u

`jupyter-notebook` helper'ı deney defterini oluşturdu. Mevcut iki yerel JSON
kaydını kullanan dört Python hücresi sırayla aynı Python 3.12 namespace'inde
çalıştırıldı. IPython/Jupyter kernel kurulmadı veya test edilmedi.

- [Notebook](../notebook/nasa-metadata-coverage.ipynb)
- [Sonuç ve girdi hash'leri](../notebook/nasa-metadata-coverage.validation.json)

Saklanan HiRISE label SHA-256 değeri ve sayısal alanları kayıtla eşleşti.
Wernecke_Brushed ve CumberlandNew_RP sayısal kutuda kaldı; iki Gobabeb satırı
kalmadı. Önceki metadata kontrolüyle uyumlu sonuç alındı.

Ham APXS CSV yeniden indirilmedi. Aynı kaydın farklı gösterimlerinin tutarlılığı
bağımsız saha doğrulaması değildir. CRS semantiği, gerçek footprint/no-data,
DEM hizalaması ve kesin delik/numune konumu hâlâ açık. Yeni arazi veya bilim
ölçümü üretilmedi.

## Quorum Mini değerlendirmesi

Soru: Seçilen skill seti projenin değişmesine ve uygulamaya geçmesine nasıl yardım etmeli?

Bu uygulama Mini modudur: aynı oturumda üç değerlendirme açısı; yeni bağımsız
aday/değerlendirici ajan veya farklı model çağrısı yok. Kurulum öncesindeki ayrı
kaynak araştırmaları bu Mini oturumun bağımsız Council deneyi olarak sayılmaz.

| Açı | Desteklenen bulgu | Karara etkisi |
|---|---|---|
| Analist | ROS, UE, GIS farklı işleri kapsıyor; Blender seti zaten var | İşe göre seçim, gereksiz tekrar kurulumundan kaçınma |
| Eleştirmen | Skill dosyası editör bağlantısı, ROS paketi veya doğru Mars CRS işlemi kanıtı değil | Gerçek araç ve girdileri uygulamada doğrulama |
| Uygulamacı | Mevcut dosyalardan UE bağlamı ve küçük NASA kontrolü üretilebiliyor | Kurulumu somut çıktıda kullanma; entegrasyonda poz/zaman/komut sınırına odaklanma |

Karar: Sabitlenmiş proje skill seti ve kısa REDLINE bağlamı kullanılacak; gereksiz
referanslar yüklenmeyecek. Önemli mimari alternatifler kapasite uygunsa Full
incelemeye; rutin işler doğrudan uygulamaya gidebilir. ROS–Unreal runtime'ı bu
değerlendirmede doğrulanmadı.

Quorum receipt: `auto -> mini`; aday `0` + değerlendirici `0` = toplam `0` yeni
worker; `maxWorkers=4`; provenance `internal-simulation`;
`explorationApplied=false`. Bu sayılar yalnız bu Mini uygulamasına aittir.
Otomatik hafıza status sonucu kapalıydı; açılmadı veya hafıza kaydı oluşturulmadı.

## Kurulum doğrulaması

17 dış kaynak giriş dosyası sabitlenmiş upstream içerikle satır sonları
normalleştirilerek karşılaştırıldı; yerel REDLINE skill'i ayrıca oluşturuldu.
Dosya bütünlüğü ve negatif kontrol sonuçları
[doğrulama kaydında](../.agents/skills-validation.json).

Bu, bütün dış skill bilgi/örneklerinin test edildiği anlamına gelmez. ROS/Unreal
başlatılmadı; ek sağlayıcı, otomatik hook veya ücretli API etkinleştirilmedi.
Kaynak/seçim ayrıntıları [skill planında](../research/proje-fikirleri/SKILL_PLANI.md).
