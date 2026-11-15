#!/usr/bin/env python3
"""Bounded offline-cache export of real USGS Gale LRGB into map-frame RGBA atlases."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import urllib.request

import numpy as np
from PIL import Image
import rasterio
from rasterio.enums import ColorInterp, MaskFlags
from rasterio.windows import Window
from redline_data.crs import ExpectedCrs, check_wkt


ALGORITHM="redline-t3-imagery-v1"
SOURCE_URL="https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_HiRISE-LRGB_78quads_sharp_cog.tif"
TEXT_URL=SOURCE_URL[:-4]+".txt"
CATALOG_URL="https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_orthophoto_mosaic_25cm"


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for b in iter(lambda:stream.read(1024*1024),b""):h.update(b)
    return h.hexdigest()


def bounded_metadata(url, *, byte_range=None, limit=65536):
    headers={"User-Agent":"Mozilla/5.0 (compatible; REDLINE-T3-imagery/1.0)","Accept-Encoding":"identity"}
    if byte_range:headers["Range"]=byte_range
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30) as response:
        if byte_range and response.status!=206:raise RuntimeError("Source refused HTTP Range; no full-download fallback")
        if byte_range and not response.headers.get("Content-Range","").startswith("bytes 0-16383/"):
            raise RuntimeError("Unexpected metadata byte range")
        size=response.headers.get("Content-Length")
        if size is not None and int(size)>limit:raise RuntimeError("Metadata response exceeds body budget")
        body=response.read(limit+1)
        if len(body)>limit:raise RuntimeError("Metadata response exceeds body budget")
        return {"source_url":url,"final_url":response.url,"http_status":response.status,
                "observed_at_utc":datetime.now(timezone.utc).isoformat(),
                "headers":{k:v for k,v in response.headers.items() if k.lower() in
                           ("etag","last-modified","content-range","content-length","content-type","accept-ranges")},
                "body_bytes":len(body),"body_sha256":hashlib.sha256(body).hexdigest()},body


def frame_from_provenance(path):
    path=Path(path);metadata=json.loads(path.read_text(encoding="utf-8"))
    if metadata.get("frame")!="map" or metadata.get("units")!="m" or metadata.get("status")!="DERIVED":
        raise ValueError("T1 map-frame/metre DERIVED provenance required")
    expected=ExpectedCrs(**metadata["identity"]["expected"])
    origin=metadata["origin"]
    if not all(math.isfinite(origin[k]) for k in ("E0_m","N0_m","H0_m")):
        raise ValueError("Finite explicit T1 origin required")
    factor=float(metadata["east_scale_factor"])
    phi=math.radians(metadata["identity"]["center_lat"])
    calculated=math.cos(phi)/math.cos(math.radians(expected.lat_ts_deg))
    if not math.isfinite(factor) or factor<=0 or not math.isclose(factor,calculated,abs_tol=1e-12,rel_tol=0):
        raise ValueError("T1 east scale factor disagrees with its CRS/centre metadata")
    return {"origin":origin,"east_scale_factor":factor,"expected":asdict(expected),
            "source_provenance_path":path.as_posix(),"source_provenance_sha256":sha256(path),
            "dem_sha256":metadata["sha256"]}


def source_pixel(dataset,frame,x,y):
    """Map XY -> source corner-coordinate pixel indices; no Earth CRS fallback."""
    e=np.asarray(x,dtype="float64")/frame["east_scale_factor"]+frame["origin"]["E0_m"]
    n=np.asarray(y,dtype="float64")+frame["origin"]["N0_m"]
    return (~dataset.transform)*(e,n)


def source_metadata(dataset,frame):
    if dataset.count!=3 or dataset.dtypes!=("uint8",)*3:
        raise ValueError("Expected exactly three uint8 source colour bands")
    if dataset.colorinterp!=(ColorInterp.red,ColorInterp.green,ColorInterp.blue):
        raise ValueError("Provider colour interpretation must be RGB")
    if not dataset.is_tiled or dataset.block_shapes!=[(512,512)]*3:
        raise ValueError("Expected source 512x512 tiled imagery")
    if dataset.transform.b!=0 or dataset.transform.d!=0 or dataset.transform.a<=0 or dataset.transform.e>=0:
        raise ValueError("Expected north-up source grid")
    crs=check_wkt(dataset.crs.to_wkt() if dataset.crs else None,ExpectedCrs(**frame["expected"]))
    flags=[[flag.name for flag in band] for band in dataset.mask_flag_enums]
    internal=all(MaskFlags.per_dataset in band for band in dataset.mask_flag_enums)
    return {"source_wkt":dataset.crs.to_wkt(),"crs_report":crs,"shape":[dataset.height,dataset.width],
            "bands":3,"dtype":"uint8","colour_interpretation":[c.name for c in dataset.colorinterp],
            "transform":list(dataset.transform),"bounds_projected_m":list(dataset.bounds),
            "pixel_resolution_m":list(dataset.res),"block_shapes":dataset.block_shapes,
            "overviews":dataset.overviews(1),"nodata":dataset.nodata,"mask_flags":flags,
            "internal_dataset_mask_verified":internal,"source_tags":dataset.tags(),
            "image_structure":dataset.tags(ns="IMAGE_STRUCTURE"),
            "validity_status":"internal_mask_verified; absolute_alignment_not_validated" if internal else
                              "provider_mask_semantics_unknown; absolute_alignment_not_validated"}


def render_atlas(dataset,frame,bounds,size,*,chunk=512,max_pixels=17_000_000,max_read_bytes=128*1024*1024,max_window_side=16384):
    if size<1 or size*size>max_pixels or chunk<1 or chunk>512:raise ValueError("Output/chunk pixel budget exceeded")
    if max_read_bytes<1 or max_window_side<1:raise ValueError("Invalid read budgets")
    left,bottom,right,top=map(float,bounds)
    if not all(math.isfinite(v) for v in bounds) or not(left<right and bottom<top):raise ValueError("Invalid ENU bounds")
    rx,ry=(right-left)/size,(top-bottom)/size
    cache_bytes=16*1024*1024
    if size*size*4+cache_bytes>max_read_bytes:raise ValueError("Output/cache working-array budget exceeded")
    rgba=np.zeros((size,size,4),dtype="uint8")
    maximum=0;maximum_side=0;reads=0;source_pixels=0;all_mask_255=True
    for row in range(0,size,chunk):
        height=min(chunk,size-row)
        y=top-(row+np.arange(height)+.5)*ry
        for col in range(0,size,chunk):
            width=min(chunk,size-col)
            x=left+(col+np.arange(width)+.5)*rx
            xx,yy=np.meshgrid(x,y)
            corners_c,corners_r=source_pixel(dataset,frame,xx,yy)
            cc,rr=corners_c-.5,corners_r-.5
            inside=(cc>=0)&(cc<=dataset.width-1)&(rr>=0)&(rr<=dataset.height-1)
            if not inside.any():continue
            cc=np.clip(cc,0,dataset.width-1);rr=np.clip(rr,0,dataset.height-1)
            c0,r0=np.floor(cc).astype("int64"),np.floor(rr).astype("int64")
            c1,r1=np.minimum(c0+1,dataset.width-1),np.minimum(r0+1,dataset.height-1)
            wl,wt=int(c0[inside].min()),int(r0[inside].min())
            ww,wh=int(c1[inside].max())-wl+1,int(r1[inside].max())-wt+1
            # Conservative live arrays estimate: output RGBA + source RGB/mask
            # + target indices/weights, masks and interpolation scratch. This
            # is an allocation bound, not a measurement of HTTP/TLS wire bytes.
            estimate=size*size*4+cache_bytes+ww*wh*4+width*height*128
            if estimate>max_read_bytes or max(ww,wh)>max_window_side:
                raise ValueError("Bounded source-window/working-array budget exceeded")
            maximum=max(maximum,estimate);maximum_side=max(maximum_side,ww,wh)
            window=Window(wl,wt,ww,wh)
            rgb=dataset.read((1,2,3),window=window)
            mask=dataset.read_masks(1,window=window)
            reads+=1;source_pixels+=ww*wh;all_mask_255 &= bool((mask==255).all())
            # Clamp only unused out-of-support target slots to keep indexing
            # bounded; their alpha remains zero.
            c0=np.clip(c0-wl,0,ww-1);c1=np.clip(c1-wl,0,ww-1)
            r0=np.clip(r0-wt,0,wh-1);r1=np.clip(r1-wt,0,wh-1)
            fx,fy=cc-np.floor(cc),rr-np.floor(rr)
            colour=np.zeros((height,width,3),dtype="float64");weight_sum=np.zeros((height,width))
            for r,c,weight in ((r0,c0,(1-fx)*(1-fy)),(r0,c1,fx*(1-fy)),(r1,c0,(1-fx)*fy),(r1,c1,fx*fy)):
                effective=weight*(mask[r,c]!=0)
                colour+=np.moveaxis(rgb[:,r,c],0,-1)*effective[:,:,None]
                weight_sum+=effective
            # Alpha is nearest-neighbour provider mask, independently of RGB
            # brightness. Bilinear colour excludes masked contributors.
            nearest_c=np.clip(np.floor(cc+.5).astype("int64")-wl,0,ww-1)
            nearest_r=np.clip(np.floor(rr+.5).astype("int64")-wt,0,wh-1)
            alpha=mask[nearest_r,nearest_c]
            valid=inside&(alpha!=0)&(weight_sum>0)
            colour/=np.where(weight_sum>0,weight_sum,1)[:,:,None]
            block=rgba[row:row+height,col:col+width]
            block[:,:,:3]=np.where(valid[:,:,None],np.clip(np.rint(colour),0,255),0).astype("uint8")
            block[:,:,3]=np.where(valid,alpha,0)
    controls=[]
    for name,r,c in (("northwest",0,0),("northeast",0,size-1),("southwest",size-1,0)):
        x,y=left+(c+.5)*rx,top-(r+.5)*ry
        source_c,source_r=source_pixel(dataset,frame,x,y)
        e,n=dataset.transform*(source_c,source_r)
        inverse_x=(e-frame["origin"]["E0_m"])*frame["east_scale_factor"]
        inverse_y=n-frame["origin"]["N0_m"]
        controls.append({"id":name,"output_row_col":[r,c],"map_pixel_center_xy_m":[x,y],
                         "source_corner_pixel_col_row":[float(source_c),float(source_r)],
                         "inverse_error_m":math.hypot(inverse_x-x,inverse_y-y)})
    stats={"bounds_map_m":list(bounds),"shape":[size,size],"resolution_map_m":[rx,ry],
           "transform_map":[rx,0,left,0,-ry,top,0,0,1],"frame":"map","units":"m","status":"DERIVED",
           "rgb_resampling":"bilinear excluding provider-masked contributors",
           "alpha_resampling":"nearest provider dataset mask plus in-source interpolation support",
           "source_window_reads":reads,"source_pixels_decoded_including_overlap":source_pixels,
           "max_source_window_side_pixels":maximum_side,"max_estimated_working_array_bytes":maximum,
           "output_valid_fraction":float((rgba[:,:,3]!=0).mean()),"all_read_provider_mask_samples_255":all_mask_255,
           "three_point_coordinate_qa":controls,"coordinate_qa_passed":max(p["inverse_error_m"] for p in controls)<1e-6,
           "pixel_row_orientation":"row 0 north; col 0 west; PNG is not vertically flipped"}
    return rgba,stats


def fetch_imagery(out,dem_provenance,*,source=SOURCE_URL,size=4096,chunk=512,max_read_bytes=128*1024*1024,
                  max_pixels=17_000_000,max_window_side=16384):
    frame=frame_from_provenance(dem_provenance)
    remote=source.startswith(("https://","http://"))
    observations=[];text=None;catalog_evidence=None
    if remote:
        observation,_=bounded_metadata(source,byte_range="bytes=0-16383",limit=16384);observations.append(observation)
        if source==SOURCE_URL:
            observation,body=bounded_metadata(TEXT_URL,limit=4096);observations.append(observation);text=body.decode("utf-8")
            observation,body=bounded_metadata(CATALOG_URL,limit=100000);observations.append(observation)
            html=body.decode("utf-8")
            constraints={}
            for label in ("Use Constraints","Access Constraints"):
                match=re.search(r"<dt[^>]*>\s*"+label+r"\s*</dt>\s*<dd[^>]*>(.*?)</dd>",html,re.S)
                if not match:raise RuntimeError("Live provider use/credit metadata could not be parsed")
                constraints[label]=re.sub(r"<[^>]*>","",match.group(1)).strip()
            catalog_evidence={"url":CATALOG_URL,"response_sha256":observation["body_sha256"],
                "observed_at_utc":observation["observed_at_utc"],"observed_constraints":constraints}
        source_identity={"url":source,"range_probe":observations[0]}
        # Volatile access timestamps are evidence, not cache identity.
        stable_source={"url":source,"etag":observations[0]["headers"].get("ETag"),
                       "content_range":observations[0]["headers"].get("Content-Range"),
                       "prefix_sha256":observations[0]["body_sha256"]}
    else:
        stable_source={"path":str(source),"sha256":sha256(source)};source_identity=stable_source
    identity={"algorithm":ALGORITHM,"helper_sha256":sha256(__file__),"source":stable_source,
              "frame_provenance_sha256":frame["source_provenance_sha256"],"size":size,"chunk":chunk,
              "max_read_bytes":max_read_bytes,"max_pixels":max_pixels,"max_window_side":max_window_side}
    out=Path(out)
    if out.exists():
        manifest=out/"imagery.json"
        if not manifest.is_file():raise FileExistsError("Output exists without completed imagery manifest")
        cached=json.loads(manifest.read_text(encoding="utf-8"))
        if cached["identity"]!=identity:raise FileExistsError("Output source/configuration differs; use new output path")
        for item in cached["artifacts"]:
            path=(out/item["relative_path"]).resolve()
            if path.parent!=out.resolve() or sha256(path)!=item["sha256"]:raise ValueError("Cached atlas hash mismatch")
        return {**cached,"cache_hit":True}
    out.parent.mkdir(parents=True,exist_ok=True)
    options={"GDAL_DISABLE_READDIR_ON_OPEN":"EMPTY_DIR","CPL_VSIL_CURL_ALLOWED_EXTENSIONS":".tif",
             "GDAL_HTTP_TIMEOUT":"30","GDAL_HTTP_MAX_RETRY":"0","CPL_VSIL_CURL_CHUNK_SIZE":"16384",
             "VSI_CACHE":False,"GDAL_CACHEMAX":16*1024*1024}
    if remote and stable_source.get("etag"):
        options["GDAL_HTTP_HEADERS"]="If-Match: "+stable_source["etag"]
    with rasterio.Env(**options),rasterio.open(source) as dataset:
        metadata=source_metadata(dataset,frame)
        atlases={};artifacts=[]
        with tempfile.TemporaryDirectory(prefix=out.name+".partial-",dir=out.parent) as temp:
            directory=Path(temp)/"complete";directory.mkdir()
            for name,half in (("ops",500.0),("context",1500.0)):
                rgba,stats=render_atlas(dataset,frame,(-half,-half,half,half),size,chunk=chunk,
                    max_pixels=max_pixels,max_read_bytes=max_read_bytes,max_window_side=max_window_side)
                path=directory/f"atlas_{name}.png"
                Image.fromarray(rgba,"RGBA").save(path,format="PNG",compress_level=6)
                stats.update(relative_path=path.name,sha256=sha256(path),bytes=path.stat().st_size,
                             colour_mode="RGBA8",alpha_source="GDAL read_masks(1); never RGB brightness")
                atlases[name]=stats;artifacts.append({"relative_path":path.name,"sha256":stats["sha256"]})
                del rgba
            manifest={"schema_version":1,"identity":identity,"created_at_utc":datetime.now(timezone.utc).isoformat(),
                      "status":"DERIVED","source_product_id":"MSL_Gale_HiRISE-LRGB_78quads_sharp_cog",
                      "source":source_identity,"source_metadata":metadata,"frame":frame,"origin":frame["origin"],"atlases":atlases,
                      "metadata_http_observations":observations,"provider_text_url":TEXT_URL,"provider_text":text,
                      "credit":"Timothy J. Parker and Fred J. Calef III; NASA/JPL-Caltech, USGS Astrogeology Science Center, University of Arizona",
                      "credit_and_use_evidence":{"url":CATALOG_URL,"live_catalog_evidence":catalog_evidence,
                          "provider_use_constraints":catalog_evidence["observed_constraints"]["Use Constraints"] if catalog_evidence else "fixture; not asserted",
                          "provider_access_constraints":catalog_evidence["observed_constraints"]["Access Constraints"] if catalog_evidence else "fixture; not asserted",
                          "colour_release":"July 2025 (not acquisition time)",
                          "processing":"HiRISE RGB strips manually tied, blended and fused to MSL RED orthophoto mosaic; GIMP unsharp mask; JPEG quality 85"},
                      "limits":["Internal source mask is used; mask=255 does not independently prove the absence of every black mosaic hole.",
                          "No RGB black-pixel heuristic or invented fill was applied.",
                          "Coordinate QA verifies affine/inverse pixel placement, not independent DEM/ortho landmark registration.",
                          "Provider imagery includes baked lighting and publisher sharpening; texture pixels are not newly measured 3D geometry.",
                          "Window budgets bound decoded arrays; HTTP/TLS wire byte count was not measured."],
                      "versions":{"rasterio":rasterio.__version__,"gdal":rasterio.__gdal_version__,"numpy":np.__version__},
                      "artifacts":artifacts,"cache_hit":False}
            (directory/"imagery.json").write_text(json.dumps(manifest,indent=2,allow_nan=False)+"\n",encoding="utf-8")
            os.rename(directory,out)
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",default=SOURCE_URL);p.add_argument("--dem-provenance",type=Path,default=Path("data/derived/BXW/dem_enu.provenance.json"))
    p.add_argument("--out",required=True,type=Path);p.add_argument("--size",type=int,default=4096)
    p.add_argument("--chunk",type=int,default=512);p.add_argument("--max-read-bytes",type=int,default=128*1024*1024)
    args=p.parse_args();m=fetch_imagery(args.out,args.dem_provenance,source=args.source,size=args.size,chunk=args.chunk,max_read_bytes=args.max_read_bytes)
    print(json.dumps({"manifest":str(args.out/"imagery.json"),"cache_hit":m["cache_hit"],
                      "atlases":{k:{"shape":v["shape"],"valid_fraction":v["output_valid_fraction"],"coordinate_qa_passed":v["coordinate_qa_passed"]} for k,v in m["atlases"].items()}},indent=2))


if __name__=="__main__":main()
