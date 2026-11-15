"""Write the visual package catalogue, source notices and content hashes."""
from __future__ import annotations
import hashlib
import html
import json
import math
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
NAMES={
 'astronaut':'Mars EVA astronotu · EV1', 'rover_1':'Altı tekerli bilim rover’ı',
 'scout_1':'Dört rotorlu keşif drone’u', 'pr_1':'Basınçlı rover · NASA SEV',
 'habitat':'Sığınak · NASA HDU', 'science_station':'Çevre ve bilim istasyonu',
 'tool_apxs':'APXS benzeri temas başlığı', 'tool_libs':'LIBS optik başlığı',
 'tool_drill':'Matkap · ayrı döner uç', 'tool_neutron':'Nötron sensörü kutusu',
 'tool_multispectral':'Multispektral kamera', 'sample_tube':'Numune tüpü ve kapak',
 'sample_case':'Taşıma / önbellek kutusu', 'rock_07':'Kuru taş · varyant 1',
 'rock_09':'Kuru taş · varyant 2',
}
# Added after the first delivery by production/build_extra.py, which owns their asset.json and
# SOURCE.md; this script only lists them in the catalogue, contact sheet, README and manifest.
EXTRA_NAMES={
 'station_marker':'İstasyon işareti', 'relay_mast':'Röle direği', 'equipment_cart':'Alet arabası',
 'valve_panel':'Vana paneli · ArUco', 'drone_pad':'Drone pisti', 'rover_garage':'Rover garajı',
 'map_table':'Harita masası', 'console_desk':'Robot konsolu', 'lab_bench':'Numune laboratuvarı',
 'mission_wall':'Görev duvarı', 'storage_rack':'Kap rafı', 'moon_rock_01':'Taş · varyant 3',
 'moon_rock_03':'Taş · varyant 4', 'moon_rock_05':'Taş · varyant 5', 'namaqualand_boulder_04':'Kaya bloğu',
}
TRIPO_TERMS='https://developers.tripo3d.ai/en/terms'
NASA_TERMS='https://www.nasa.gov/nasa-brand-center/images-and-media/'


EXTRA_README='''**Ek paketler (Claude Code oturumu):** 11 prosedürel saha/habitat nesnesi (istasyon işareti, röle direği, alet arabası, ArUco'lu vana paneli, drone pisti, rover garajı, harita masası, robot konsolu, numune laboratuvarı, görev duvarı, kap rafı) `production/procedural_assets.py` ile özgün geometri olarak; 4 ek taş Poly Haven CC0'dan hazırlandı. Tripo kredisi kullanılmadı. Dönen parçalar (teker, vana kolu, gösterge ibresi, anten) pivot ve +X ön kontrolüyle `verification_extra.json` içinde. ArUco desenleri OpenCV ile üretilip PNG'den yeniden okunarak doğrulandı.

**Revizyonlar:** Sığınak dokusundan NASA logosu, ABD bayrakları, HAB X ve HDU amblemleri temizlendi; taşıma kutusu açık griye boyandı; astronot master'ı belgelenen +X ileri sözleşmesine döndürüldü (önceki "front" önizlemesi yandan görünüyordu). Gerekçe ve hash'ler ilgili `asset.json → revisions` kayıtlarında.

'''


def main():
    checks=json.loads((ROOT/'verification.json').read_text())
    ledger=json.loads((ROOT/'CREDIT_LEDGER.json').read_text())
    rows=[];cards=[];assets=[]
    for aid,title in NAMES.items():
        folder=ROOT/'incoming'/aid;meta=folder/'asset.json';data=json.loads(meta.read_text())
        task_records=[x for x in ledger['task_records'] if x['asset_id']==aid]
        if aid=='rover_1':source=json.loads((ROOT/'incoming/curiosity_reference/download.json').read_text())
        elif aid=='sample_case':source=json.loads((ROOT/'incoming/industrial_pastic_container/download.json').read_text())
        elif (folder/'download.json').exists():source=json.loads((folder/'download.json').read_text())
        else:source=None
        kind='NASA hazır model' if aid in ('rover_1','pr_1','habitat','sample_tube') else 'Poly Haven · CC0' if aid in ('sample_case','rock_07','rock_09') else 'Tripo · AI üretimi'
        data['source_notice']={'kind':kind,'library':source,'tripo_tasks':task_records,'terms_urls':[TRIPO_TERMS,'https://www.tripo3d.ai/terms'] if task_records else [source['license_url']] if source else []}
        data['local_verification']=checks['assets'][aid]
        if (folder/'source_geometry_check.json').exists():data['source_geometry_verification']=json.loads((folder/'source_geometry_check.json').read_text())
        data['checks']['local_file_roundtrip']='PASS' if checks['assets'][aid]['pass'] else 'FAIL'
        data['checks']['engine_scale_calibration']='NOT_RUN; 1 m Blender FBX calibration passed'
        if (folder/'pivot_checks.json').exists():data['pivot_inspection']=json.loads((folder/'pivot_checks.json').read_text())
        if (folder/'animation_checks.json').exists():data['animation_inspection']=json.loads((folder/'animation_checks.json').read_text())
        if aid=='sample_tube':data['provenance']['note']+=' Separate cap is a scenario derivative, not flight sealing CAD.'
        if aid=='rover_1':data['rejected_candidate']={'path':'source.glb','reason':'Tripo wheel layout did not match six-wheel brief; preserved as original output, not used by master.blend'}
        data['delivery_status']='LOCAL_VISUAL_PACKAGE_PREPARED; ENGINE_ACCEPTANCE_PENDING'
        meta.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        lines=[f'# {aid} — kaynak ve teslim kaydı','',f'14 Kasım 2026 · {kind}.','',
               'Bu dosya bir görsel varlık kaydıdır. Boyut, yerleşim ve görevdeki kullanım SCENARIO’dur; NASA ölçümü, flight CAD, sensör kalibrasyonu veya robot kontrol sistemi sayılmaz.','',
               f"Gerçekte işlenen kaynak: `{data['source']}`. Orijinal dosyalar korunmuştur.",'']
        if source:
            lines += [f"Kaynak: [{source['source']}]({source['source']}).",f"Atıf: {source['credit']}.",f"Kullanım: [{source['license']}]({source['license_url']}).",'']
            if 'NASA' in kind:lines+=['NASA tanımlayıcıları ve üçüncü taraf haklarına ilişkin kaynak koşulları sürer; NASA desteği/onayı ima edilmez.','']
        if task_records:
            lines += [f'Üretim/işleme Tripo API üzerinden yapıldı. [API koşulları]({TRIPO_TERMS}), [Tripo koşulları](https://www.tripo3d.ai/terms). Bu dosyalara CC0 lisansı verilmedi. Hesap abonelik türü bu paket tarafından doğrulanmaz.','']
            for task in task_records:
                lines += [f"- `{task['task_id']}` · {task['type']} · {task['status']} · {task.get('credits_consumed',0)} kredi"+(' · oturum öncesi' if task['historical'] else '')]
            lines += ['', 'Görevlerin tam istek parametreleri `asset.json → source_notice.tripo_tasks` içinde; süreli indirme URL’leri ve hesap sırları kaydedilmedi.','']
            for task in task_records:
                prompt=task.get('input',{}).get('prompt')
                if prompt:lines += [f"Prompt · `{task['task_id']}`:",'','```text',prompt,'```','']
        lines += ['Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, ayrı parça OBJ’leri, basit çarpışma proxy’leri ve önizlemeler. Gazebo `visual.sdf` yalnız statik görsel yükleme içindir; URDF/link/joint, inertia, ROS topic, uçuş ve navigasyon kontrolü içermez.','',
                  f"Ölçülen LOD0: {data['lod0']['triangles']:,} üçgen; {data['lod0']['materials']} malzeme; {len(data['parts'])} parça. Gazebo visual: {data['gazebo']['triangles']:,} üçgen.",
                  f"Blender {data['blender_version']}; FBX binary 7400. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı. FBX/OBJ dönüşüm ayarları ve parça pivotları asset.json içinde.",'',
                  'Yerel yeniden içe aktarma: **geçti**. Unreal/Gazebo içi import, 100 cm/1 m ölçümü, materyal/normal bağlama ve robot kontrolü: **yapılmadı**. 1 m test küpü ve eksen okları `assets/calibration/` içinde.','']
        if aid=='rover_1':lines+=['`source.glb`, teker yerleşimi nedeniyle seçilmeyen orijinal Tripo adayını korur. Teslim edilen master ve motor türevleri, `curiosity_reference/source.blend` kaynağından üretilmiştir.','']
        if data['limitations']:lines += ['Açık sınırlar:','']+['- '+x for x in data['limitations']]+['']
        for rev in data.get('revisions',[]):lines += [f"Revizyon ({rev['date_utc'][:10]}): {rev['reason']} Ayrıntı `asset.json → revisions`.",'']
        (folder/'SOURCE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        tri=data['lod0']['triangles'];gaz=data['gazebo']['triangles'];part=len(data['parts'])
        rows.append(f'| [{aid}](incoming/{aid}/SOURCE.md) | {kind} | {tri:,} / {gaz:,} | {part} |')
        thumb=f'incoming/{aid}/preview/perspective.png'
        cards.append(f'<article><a href="{thumb}"><img src="{thumb}" alt="{html.escape(title)}"></a><h2>{html.escape(title)}</h2><p>{html.escape(kind)} · {tri:,} üçgen · {part} parça</p><p><a href="incoming/{aid}/master.blend">Blender</a> · <a href="incoming/{aid}/presentation.glb">GLB</a> · <a href="incoming/{aid}/unreal/{aid}_LOD0.fbx">FBX</a> · <a href="incoming/{aid}/asset.json">Kayıt</a> · <a href="incoming/{aid}/SOURCE.md">Kaynak</a></p></article>')
        assets.append((aid,title,folder/'preview/perspective.png'))
    for aid,title in EXTRA_NAMES.items():
        folder=ROOT/'incoming'/aid;data=json.loads((folder/'asset.json').read_text(encoding='utf-8'))
        kind=data['source_notice']['kind'];tri=data['lod0']['triangles'];gaz=data['gazebo']['triangles'];part=len(data['parts'])
        rows.append(f'| [{aid}](incoming/{aid}/SOURCE.md) | {kind} | {tri:,} / {gaz:,} | {part} |')
        thumb=f'incoming/{aid}/preview/perspective.png'
        cards.append(f'<article><a href="{thumb}"><img src="{thumb}" alt="{html.escape(title)}"></a><h2>{html.escape(title)}</h2><p>{html.escape(kind)} · {tri:,} üçgen · {part} parça</p><p><a href="incoming/{aid}/master.blend">Blender</a> · <a href="incoming/{aid}/presentation.glb">GLB</a> · <a href="incoming/{aid}/unreal/{aid}_LOD0.fbx">FBX</a> · <a href="incoming/{aid}/asset.json">Kayıt</a> · <a href="incoming/{aid}/SOURCE.md">Kaynak</a></p></article>')
        assets.append((aid,title,folder/'preview/perspective.png'))
    total=len(NAMES)+len(EXTRA_NAMES)
    verified=[checks['assets'][a] for a in list(NAMES)+list(EXTRA_NAMES) if a in checks['assets']]
    passed=sum(v['pass'] for v in verified)
    fbx_max=max(v['fbx_reimport']['max_dimension_error_m'] for v in verified)
    obj_max=max(v['obj_reimport']['max_dimension_error_m'] for v in verified)
    assets.insert(1,('astronaut_EV2','Mars EVA astronotu · EV2',ROOT/'incoming/astronaut/preview/EV2/perspective.png'))
    output=ROOT/'preview';output.mkdir(exist_ok=True)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',19)
    small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',14)
    cols=4;cell_w=320;cell_h=365
    sheet=Image.new('RGB',(cols*cell_w,math.ceil(len(assets)/cols)*cell_h),(18,23,30));draw=ImageDraw.Draw(sheet)
    for i,(aid,title,path) in enumerate(assets):
        x=(i%cols)*cell_w;y=(i//cols)*cell_h
        image=Image.open(path).convert('RGBA');image.thumbnail((310,310))
        sheet.paste(image,(x+(cell_w-image.width)//2,y),image)
        draw.text((x+12,y+313),title,font=font,fill=(245,245,245))
        draw.text((x+12,y+341),aid,font=small,fill=(169,180,193))
    sheet.save(output/'contact_sheet.jpg',quality=94)
    for clip in ('idle','walk'):
        frames=[Image.open(p).convert('RGB') for p in sorted((ROOT/f'incoming/astronaut/preview/{clip}').glob('*/perspective.png'))]
        if frames:frames[0].save(output/f'astronaut_{clip}.gif',save_all=True,append_images=frames[1:],duration=450,loop=0)
    readme='''# REDLINE 3D varlık paketi

14 Kasım 2026 · **15 yerel görsel varlık paketi**, EV1/EV2 malzeme varyantları ve astronot idle/walk animasyonları hazırlandı. [Toplu önizleme](preview/contact_sheet.jpg) · [Görsel katalog](catalog.html).

Tripo ile astronot rig/animasyonları, drone parçalama, bilim istasyonu ve beş bilim aracı hazırlandı. Rover için üretilen Tripo adayının teker yerleşimi brife uymadı; asıl teslimde NASA Curiosity modeli kullanıldı. Basınçlı rover/sığınak/numune tüpü NASA’dan; iki taş ve taşıma kutusu Poly Haven CC0 kaynaklarından alındı.

| Varlık | Kaynak | Üçgen: LOD0 / Gazebo visual | Parça |
|---|---|---:|---:|
'''+ '\n'.join(rows)+'''

Her pakette düzenlenebilir `master.blend`, sunum `presentation.glb`, ayrı FBX LOD0/1/2, PNG kaplamalar, sade Gazebo OBJ ve parça OBJ’leri, çarpışma proxy’leri, `SOURCE.md` ve `asset.json` vardır. Parça kökeni/pivotu ve kaynak→master dönüşümü kayıttadır. LOD1/2 ayrı dosyalardır; Unreal’a açıkça LOD olarak yüklenir.

Astronotun 80 kemikli iskeleti, dört etkiye sınırlanıp normalize edilmiş skin ağırlıkları, ayrı idle/walk FBX dosyaları ve dört karelik hareket önizlemeleri vardır. EV1 kırmızı; EV2 mavi vurgu dokusudur. Mesh ve iskelet ortaktır; yüz/boyun UV alanı renk değişiminden korunmuştur. EV2 için yalnız `material_variants.EV2.BaseColor` değiştirilir.

**Yerel doğrulama: 15/15 geçti.** FBX boyut farkı ≤0,000000239 m; sade OBJ farkı ≤0,014721 m. 1 m kalibrasyon küpünün Blender FBX dönüşü 1 m’dir. Rover 6, SEV 12 ayrı teker; drone 4 ayrı rotor grubudur. 90° dönüşlerde pivotun sabit kalması ve gerçek vertex hareketi ölçüldü. [Makine raporu](verification.json), [kalibrasyon](calibration/), parça bazında `pivot_checks.json` ve karakter `animation_checks.json`.

**Unreal/Gazebo kabulü bekliyor.** Motor içinde 100 cm/1 m ölçümü, PBR/normal bağlantıları, LOD geçişleri, giriş/kapı çarpışması ve skin deformasyonu ayrıca kontrol edilir. FBX 7400 dışa aktarımı yerelde yeniden yüklendi; Epic importer uyumluluğu bu sonuçtan varsayılmaz. Görsel collision’lar taslak basit proxy’lerdir. Gazebo `visual.sdf` statiktir; robot fiziği, inertia, eklem limitleri, Nav2, drone kontrolü ve ROS köprüsü oluşturulmadı. Robot otoritesi ROS/Gazebo’da kalır.

Sığınak ilk teslimde dış görünüş ve ayrı hava kilidi kapısıdır; yürünebilir iç mekân içermez. Numune tüpü STL’si ayrı senaryo kapağına bölündü; gerçek uçuş sızdırmazlık mekanizması değildir. Taşların biçimi/rengi NASA ölçümü veya mineral kanıtı sayılmaz. Her varlığın kalan sınırları kendi kaydındadır.

Bu oturum **305 Tripo kredisi** kullandı: rover adayı 60, istasyon 40, astronot rig+iki animasyon 45, drone parçalama 40, beş bilim aracı 120. Başlangıç 930 → kalan 625; frozen 0. Önceki astronot 50 ve drone 20 kredi bu toplamın dışındadır. [Görev/harcama kaydı](CREDIT_LEDGER.json).

Ham çıktılar korunur; NASA/Poly Haven kaynak ve lisansları varlık başına kayıtlıdır. Tripo çıktıları AI görselidir ve CC0 olarak yeniden lisanslanmaz. Git/LFS/ignore kuralları değiştirilmedi, commit/push yapılmadı. Büyük dosyaları yayınlama kararı kullanıcıya aittir. Projenin T0–T11 kilometre taşları bu varlık hazırlığıyla tamamlandı işaretlenmez.
'''
    readme=(readme.replace('**15 yerel görsel varlık paketi**',f'**{total} yerel görsel varlık paketi**')
        .replace('**Yerel doğrulama: 15/15 geçti.** FBX boyut farkı ≤0,000000239 m; sade OBJ farkı ≤0,014721 m.',f'**Yerel doğrulama: {passed}/{total} geçti.** FBX boyut farkı ≤{fbx_max:.3g} m; sade OBJ farkı ≤{obj_max:.3g} m.')
        .replace('Ham çıktılar korunur;',EXTRA_README+'Ham çıktılar korunur;'))
    (ROOT/'README.md').write_text(readme,encoding='utf-8')
    catalogue='''<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>REDLINE · Varlık teslim kataloğu</title><style>body{margin:30px auto;padding:0 24px;max-width:1400px;font:16px/1.6 system-ui;background:#12171e;color:#e9edf2}h1{font-size:32px}h2{font-size:18px;margin:12px 0 4px}a{color:#93c5fd}header{margin-bottom:28px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}article{padding:16px;background:#1b222d;border-radius:10px}img{width:100%;aspect-ratio:1;object-fit:contain}p{margin:8px 0}.status{color:#f9ca87}</style><header><h1>REDLINE · 3D varlık teslimi</h1><p>14 Kasım 2026 · '''+str(total)+''' paket · EV1/EV2 aynı mesh · 305 kredi / 625 kalan; ek paketlerde kredi kullanılmadı</p><p class="status">Yerel dosya kontrolleri geçti. Unreal/Gazebo içi import ve robot kontrol kabulü bekliyor.</p><p><a href="README.md">Teslim notları</a> · <a href="preview/contact_sheet.jpg">Toplu önizleme</a> · <a href="verification.json">Doğrulama</a> · <a href="CREDIT_LEDGER.json">Üretim kayıtları</a> · <a href="preview/astronaut_walk.gif">Yürüyüş örnekleri</a></p></header><div class="grid">'''+''.join(cards)+'''</div><p>Hazır kaynaklar: NASA 3D Resources; Poly Haven (CC0). Üretimler: Tripo; prosedürel nesneler REDLINE özgün geometrisidir. Kaynak bağlantıları ve koşulları her kartın Kaynak dosyasında. Bu sayfa yerel bir teslim raporudur; dosyalar bir hizmete yüklenmedi.</p></html>'''
    (ROOT/'catalog.html').write_text(catalogue,encoding='utf-8')
    (ROOT/'sample_kit.json').write_text(json.dumps({'provenance':'SCENARIO','tube_and_cap':'incoming/sample_tube','carrying_case':'incoming/sample_case','cache':'Reuse sample_case at scenario-recorded cache pose; no scene placement authored','origin_vs_analysis':'Asset location does not define sample collection origin or assay location'},indent=2)+'\n',encoding='utf-8')
    manifest=[]
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or path.name=='MANIFEST.json' or '__pycache__' in path.parts or path.suffix in ('.blend1','.pyc') or path.name.endswith('-console.txt'):continue
        raw=path.read_bytes();manifest.append({'path':path.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    (ROOT/'MANIFEST.json').write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),'asset_count':total,'files':manifest},indent=2)+'\n',encoding='utf-8')
    print('FINALIZED',total,'assets;',len(manifest),'files;',sum(x['bytes'] for x in manifest),'bytes',flush=True)


if __name__=='__main__':main()
