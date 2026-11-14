"""Render the current research reading index; timestamps are filesystem evidence."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
TR = timezone(timedelta(hours=3))


def main() -> None:
    paths = [ROOT / "docs/proje.md"]
    for folder in ("research/proje-fikirleri", "research/handoff", "research/notes", "research/notebook"):
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file())
    records = []
    for p in sorted(set(paths)):
        stat = p.stat()
        data = p.read_bytes()
        records.append({
            "path": p.relative_to(ROOT).as_posix(), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "last_write_at": datetime.fromtimestamp(stat.st_mtime, TR).isoformat(timespec="seconds"),
        })
    stamp = datetime.now(TR).isoformat(timespec="seconds")
    catalog = {
        "recorded_at": stamp, "timezone": "Europe/Istanbul",
        "note": "Current filesystem last-write times, not original research dates. Earlier publication snapshot remains in history/. Git dates show actual commits.",
        "final_specification": "docs/proje.md", "idea_phase": "finished; implementation starts from T0",
        "excluded_folder": "önceki deneme", "records": records,
    }
    (ROOT / "research/FILE_TIMESTAMPS.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    text = """# Proje fikir aşamaları ve araştırmalar / Research

**Fikir aşaması tamamlandı. Son uygulama belgesi [docs/proje.md](../docs/proje.md).** Aşağıdaki notlar fikrin araştırılmasını ve gelişimini anlatır; tamamlanmış uygulama sayılmaz.

![Fikir aşamalarının gelişimi](idea-stages.svg)

Şema belgelerin kavramsal gelişim sırasıdır. Kesin yazılma saati bilinmeyen araştırmalara saat atanmaz. Dosya son yazma zamanları aşağıda, gerçek yayın tarih/saatleri [Git geçmişinde](https://github.com/ahmetefesensoy/redline/commits/main/) görülür.

## Nasıl ilerledik?

| Aşama | Belgeler | Sonraki karara katkı |
|---|---|---|
| 01 — Araştırma | [İlk araştırma](proje-fikirleri/SPACE_APPS_ARASTIRMA.md), [kapsamlı araştırma](proje-fikirleri/SPACE_APPS_KAPSAMLI_ARASTIRMA.md), [kaynak/varlık kataloğu](proje-fikirleri/KAYNAK_VE_VARLIK_KATALOGU.md) | Veri, kaynak ve araç seçenekleri |
| 02 — Fikrin gelişimi | [Ürün tanımı](proje-fikirleri/PROJE_TANIMI.md), [astronot/rover/drone](proje-fikirleri/ASTRONOT_ROVER_DRONE.md), [görevler](proje-fikirleri/BES_ANA_GOREV_VE_MIMARI.md), [strateji](proje-fikirleri/GELISTIRME_STRATEJISI.md), [tasarım incelemesi](proje-fikirleri/TASARIM_GOZDEN_GECIRME.md), [v2 kılavuzu](proje-fikirleri/PROJE_KILAVUZU.md) | Görevler, roller ve alternatiflerin incelenmesi |
| 03 — V3 kararı | [V3 kılavuzu](proje-fikirleri/REDLINE_V3_KILAVUZU.md), [konsey kayıtları](notes/council-v3-source/README.md) | BXW ileri EVA, YKB kalibrasyon; tek EVA'nın beş evresi |
| 04 — Fikir aşaması bitti | [docs/proje.md](../docs/proje.md), [aktarılmış spek nüshası](proje-fikirleri/REDLINE_V3_UYGULAMA_SPEKI.md) | Kodlamanın esas belgesi ve T0–T14 kabul ölçütleri |

## Kayıtların anlamı

**Envanter:** STAMP · Europe/Istanbul (UTC+03:00). Aşağıdaki saatler mevcut dosya sisteminin son yazma zamanıdır; aktarma, paketleme veya bağlantı düzenlemesini yansıtabilir. İlk araştırmanın yapıldığı anı kanıtlamaz. İlk yayın envanteri [history/](history/) altında tarihsel haliyle korunur; orada eski yolların bulunması dosyaların hâlâ projede bulunduğu anlamına gelmez.

Kullanıcının son yönlendirmesiyle `önceki deneme` klasörü güncel çalışma ağacından çıkarıldı. Görsel tasarım ve 3D varlık üretimi kullanıcıyla birlikte yapılacak; bu görsel yalnız belge gelişimini anlatır.

## Dosyalar ve son yazma zamanları

| Belge / kayıt | Son yazma (UTC+03:00) |
|---|---|
""".replace("STAMP", stamp)
    for record in records:
        link = "../" + quote(record["path"], safe="/._-")
        text += f'| [{record["path"]}]({link}) | {record["last_write_at"]} |\n'
    text += "\n[Makinece okunabilir tarih/hash kaydı](FILE_TIMESTAMPS.json) · [Uygulama ilerlemesi](../journal/PROGRESS.md) · [Gerçek test kayıtları](../docs/VERIFICATION_LOG.md).\n"
    (ROOT / "research/README.md").write_text(text, encoding="utf-8")
    print(f"Research index: {len(records)} current records; {stamp}")


if __name__ == "__main__":
    main()
