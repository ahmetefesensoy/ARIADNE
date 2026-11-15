"""Draw the app's original vector-like A mark; do not modify cover artwork."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parents[1];dest=root/'desktop/ariadne/assets'
image=Image.new('RGBA',(256,256),(24,18,15,255));draw=ImageDraw.Draw(image)
draw.rounded_rectangle((10,10,246,246),radius=46,fill=(31,23,19),outline=(122,74,47),width=2)
font=ImageFont.truetype('C:/Windows/Fonts/times.ttf',174)
box=draw.textbbox((0,0),'A',font=font);draw.text(((256-(box[2]-box[0]))/2-box[0],(238-(box[3]-box[1]))/2-box[1]),'A',font=font,fill=(241,229,210))
draw.line([(66,211),(102,201),(139,210),(190,194)],fill=(174,69,46),width=5)
image.save(dest/'ariadne-icon.png');image.save(dest/'ariadne.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
cover=dest/'ariadne-cover.png'
record={'tool':'Built-in Image Generation','image_source':'C:/Users/USER/.codex/generated_images/01a1d8d9-b680-7611-8d66-c13892a0d7d0/exec-c3bbe36f-d36e-4b8e-9b16-e08a3456a845.png','sha256':hashlib.sha256(cover.read_bytes()).hexdigest(),'status':'AI_GENERATED FICTIONAL COVER; not NASA archive image','prompt':'Landscape cinematic ARIADNE Windows launch cover: realistic solitary EVA astronaut, six-wheel research rover, rust-orange Martian boxwork ridges, dusty amber sunset, fine red safe return route to a tiny habitat, ivory upper-left ARIADNE title. Restrained photographic game key art. No other lettering, NASA logos, flags, neon UI, giant planets or device mockup.','icon':'Original code-drawn A monogram, not a crop/edit of the generated artwork.'}
(dest/'cover-source.json').write_text(json.dumps(record,indent=2)+'\n')
