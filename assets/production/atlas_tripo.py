"""Atlas segmented Tripo PBR images, retaining original GLBs and UV layouts.

UV transforms are applied later by build_package.py. Square tiles never rotate,
so the source tangent-space normal direction remains unchanged.
"""
from __future__ import annotations
import io
import json
import struct
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def atlas(asset_id: str, size: int) -> None:
    out = ROOT / "incoming" / asset_id
    raw = (out / "source.glb").read_bytes()
    count = struct.unpack_from("<I", raw, 12)[0]
    doc = json.loads(raw[20:20+count])
    binary = raw[28+count:]
    meshes = []
    for idx, mesh in enumerate(doc["meshes"]):
        tri = sum(doc["accessors"][p["indices"]]["count"] // 3 for p in mesh["primitives"])
        if tri > 4:
            meshes.append((idx, tri))
    meshes.sort(key=lambda v: v[1], reverse=True)
    occupied = set()
    canvases = {"BaseColor": Image.new("RGB", (size, size), (180,180,180)), "NormalGL": Image.new("RGB", (size,size), (128,128,255)), "ORM": Image.new("RGB", (size,size), (255,180,0))}
    mapping = {}
    unit = size // 8
    for order, (idx, _) in enumerate(meshes):
        blocks = 4 if order == 0 else 2 if order < (7 if len(meshes) > 20 else 4) else 1
        found = None
        for row in range(9-blocks):
            for col in range(9-blocks):
                cells = {(row+y,col+x) for y in range(blocks) for x in range(blocks)}
                if not cells & occupied:
                    found=(row,col,cells)
                    break
            if found:
                break
        if not found:
            raise ValueError("Atlas overflow")
        row,col,cells = found
        occupied |= cells
        tile = blocks * unit
        pad = 4
        mapping[f"tripo_part_{idx}"] = {"u": (col*unit+pad)/size, "v": (size-(row*unit+tile)+pad)/size, "scale": (tile-2*pad)/size}
        material = doc["materials"][doc["meshes"][idx]["primitives"][0]["material"]]
        refs = {"BaseColor": material["pbrMetallicRoughness"]["baseColorTexture"]["index"], "NormalGL": material["normalTexture"]["index"], "ORM": material["pbrMetallicRoughness"]["metallicRoughnessTexture"]["index"]}
        for channel, ref in refs.items():
            img = doc["images"][doc["textures"][ref]["source"]]
            view = doc["bufferViews"][img["bufferView"]]
            start = view.get("byteOffset", 0)
            image = Image.open(io.BytesIO(binary[start:start+view["byteLength"]])).convert("RGB")
            image = image.resize((tile-2*pad,tile-2*pad), Image.Resampling.LANCZOS)
            # Extend edge pixels into gutters to prevent sampling the neighboring tile.
            padded=ImageOps.expand(image,border=pad)
            padded.paste(image.crop((0,0,image.width,1)).resize((image.width,pad)),(pad,0))
            padded.paste(image.crop((0,image.height-1,image.width,image.height)).resize((image.width,pad)),(pad,tile-pad))
            padded.paste(image.crop((0,0,1,image.height)).resize((pad,image.height)),(0,pad))
            padded.paste(image.crop((image.width-1,0,image.width,image.height)).resize((pad,image.height)),(tile-pad,pad))
            for xx,yy,px,py in [(0,0,0,0),(tile-pad,0,image.width-1,0),(0,tile-pad,0,image.height-1),(tile-pad,tile-pad,image.width-1,image.height-1)]:
                padded.paste(image.getpixel((px,py)),(xx,yy,xx+pad,yy+pad))
            canvases[channel].paste(padded, (col*unit,row*unit))
    textures=out/"textures";textures.mkdir(exist_ok=True)
    for channel, img in canvases.items():
        img.save(textures/f"{asset_id}_{channel}.png")
    r,g,b=canvases["NormalGL"].split()
    Image.merge("RGB",(r,ImageOps.invert(g),b)).save(textures/f"{asset_id}_NormalDX.png")
    for i,ch in enumerate(("AO","Roughness","Metallic")):
        canvases["ORM"].getchannel(i).save(textures/f"{asset_id}_{ch}.png")
    (out/"atlas.json").write_text(json.dumps({"size":size,"tiles":mapping,"material_count":1,"normal_convention":"OpenGL; separate NormalDX flips green"},indent=2)+"\n",encoding="utf-8")
    print(asset_id, len(mapping), "parts -> 1 material",size)


if __name__ == "__main__":
    atlas("rover_1",2048)
    atlas("science_station",1024)
    atlas("tool_drill",1024)
