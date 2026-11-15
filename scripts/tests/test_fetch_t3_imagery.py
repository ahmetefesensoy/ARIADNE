"""Analytic RGB/mask fixtures for the map-to-source imagery contract."""
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
import pytest
import rasterio
from rasterio.enums import ColorInterp
from rasterio.transform import from_origin


spec=importlib.util.spec_from_file_location("fetch_t3_imagery",Path(__file__).parents[1]/"fetch_t3_imagery.py")
imagery=importlib.util.module_from_spec(spec);spec.loader.exec_module(imagery)


@pytest.fixture
def fixture(tmp_path):
    e0,n0=8142565.198776576,-284814.9215994864
    lat=-4.805;factor=math.cos(math.radians(lat))
    frame={"origin":{"E0_m":e0,"N0_m":n0,"H0_m":0.0,"status":"SCENARIO"},
           "east_scale_factor":factor,"expected":{"sphere_radius_m":3396190,"lon_0_deg":0,"lat_ts_deg":0}}
    rows,cols=np.meshgrid(np.arange(1024),np.arange(1024),indexing="ij")
    rgb=np.stack((cols//4,rows//4,200-(cols+rows)//16)).astype("uint8")
    rgb[:,507:509,507:509]=0  # Valid dark source pixels must remain valid.
    mask=np.full((1024,1024),255,dtype="uint8");mask[515:518,515:518]=0
    source=tmp_path/"rgb.tif"
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True),rasterio.open(source,"w",driver="GTiff",width=1024,height=1024,
            count=3,dtype="uint8",crs="+proj=eqc +R=3396190 +lon_0=0 +lat_ts=0 +units=m",
            transform=from_origin(e0-2048,n0+2048,4,4),tiled=True,blockxsize=512,blockysize=512) as d:
        d.write(rgb);d.colorinterp=(ColorInterp.red,ColorInterp.green,ColorInterp.blue);d.write_mask(mask)
    provenance=tmp_path/"dem.provenance.json"
    provenance.write_text(json.dumps({"status":"DERIVED","frame":"map","units":"m","sha256":"a"*64,
        "origin":frame["origin"],"east_scale_factor":factor,
        "identity":{"center_lat":lat,"expected":frame["expected"]}}),encoding="utf-8")
    return source,provenance,frame


def test_source_metadata_uses_real_wkt_rgb_and_internal_mask(fixture):
    source,_,frame=fixture
    with rasterio.open(source) as d:
        m=imagery.source_metadata(d,frame)
        assert m["crs_report"]["sphere_radius_m"]==3396190
        assert m["colour_interpretation"]==["red","green","blue"]
        assert m["internal_dataset_mask_verified"] and m["nodata"] is None
        assert "absolute_alignment_not_validated" in m["validity_status"]
        with pytest.raises(ValueError,match="radius"):
            imagery.source_metadata(d,{**frame,"expected":{**frame["expected"],"sphere_radius_m":3400000}})


def test_three_corner_inverse_and_asymmetric_pixels_keep_north_up(fixture):
    source,_,frame=fixture
    with rasterio.open(source) as d:
        a,m=imagery.render_atlas(d,frame,(-500,-500,500,500),32,chunk=7)
        nw,ne,sw=m["three_point_coordinate_qa"]
        assert m["coordinate_qa_passed"]
        assert nw["source_corner_pixel_col_row"][0]<ne["source_corner_pixel_col_row"][0]
        assert nw["source_corner_pixel_col_row"][1]<sw["source_corner_pixel_col_row"][1]
        assert a[0,0,0]<a[0,-1,0]  # red grows east
        assert a[0,0,1]<a[-1,0,1]  # green grows south in source raster
        assert a[0,0,3]==255
        c,r=imagery.source_pixel(d,frame,100.0,-40.0)
        e,n=d.transform*(c,r)
        assert e==pytest.approx(frame["origin"]["E0_m"]+100/frame["east_scale_factor"])
        assert n==pytest.approx(frame["origin"]["N0_m"]-40)


def test_alpha_is_nearest_provider_mask_never_black_heuristic(fixture):
    source,_,frame=fixture
    with rasterio.open(source) as d:
        # Output centres deliberately coincide with source pixel centres.
        x0=(506*4+2-2048)*frame["east_scale_factor"]
        x1=(519*4+2-2048)*frame["east_scale_factor"]
        y_top=2048-(506*4+2);y_bottom=2048-(519*4+2)
        bounds=(x0-2*frame["east_scale_factor"],y_bottom-2,x1+2*frame["east_scale_factor"],y_top+2)
        a,_=imagery.render_atlas(d,frame,bounds,14,chunk=5)
        assert np.array_equal(a[1,1],[0,0,0,255])
        assert (a[9:12,9:12,3]==0).all()
        assert (a[9:12,9:12,:3]==0).all()


def test_outside_source_support_is_transparent_without_extrapolation(fixture):
    source,_,frame=fixture
    with rasterio.open(source) as d:
        a,m=imagery.render_atlas(d,frame,(-3000,-3000,3000,3000),32,chunk=8)
        assert (a[0,:,3]==0).all() and (a[-1,:,3]==0).all()
        assert 0<m["output_valid_fraction"]<1


def test_chunk_results_equal_single_chunk_and_read_budgets_fail_before_arrays(fixture):
    source,_,frame=fixture
    with rasterio.open(source) as d:
        a,_=imagery.render_atlas(d,frame,(-500,-500,500,500),32,chunk=32)
        b,m=imagery.render_atlas(d,frame,(-500,-500,500,500),32,chunk=7)
        assert np.array_equal(a,b) and m["source_window_reads"]>1
        with pytest.raises(ValueError,match="pixel budget"):
            imagery.render_atlas(d,frame,(-500,-500,500,500),4200)
        with pytest.raises(ValueError,match="budget"):
            imagery.render_atlas(d,frame,(-500,-500,500,500),32,max_read_bytes=100)
        with pytest.raises(ValueError,match="budget"):
            imagery.render_atlas(d,frame,(-500,-500,500,500),32,max_window_side=10)


def test_atomic_atlases_manifest_and_hash_cache_do_not_overwrite(fixture,tmp_path):
    source,provenance,_=fixture;out=tmp_path/"imagery"
    m=imagery.fetch_imagery(out,provenance,source=str(source),size=32,chunk=8)
    assert set(m["atlases"])=={"ops","context"}
    with Image.open(out/"atlas_ops.png") as image:
        assert image.mode=="RGBA" and image.size==(32,32)
    assert m["frame"]["origin"]["H0_m"]==0
    assert m["origin"]==m["frame"]["origin"]
    times={p.name:p.stat().st_mtime_ns for p in out.iterdir()}
    cached=imagery.fetch_imagery(out,provenance,source=str(source),size=32,chunk=8)
    assert cached["cache_hit"] and times=={p.name:p.stat().st_mtime_ns for p in out.iterdir()}
    with pytest.raises(FileExistsError,match="differs"):
        imagery.fetch_imagery(out,provenance,source=str(source),size=16,chunk=8)
    (out/"atlas_ops.png").write_bytes(b"corrupted")
    with pytest.raises(ValueError,match="hash mismatch"):
        imagery.fetch_imagery(out,provenance,source=str(source),size=32,chunk=8)


def test_t1_frame_factor_mismatch_is_not_silently_relabelled(fixture):
    _,provenance,_=fixture;m=json.loads(provenance.read_text());m["east_scale_factor"]=1.0
    provenance.write_text(json.dumps(m))
    with pytest.raises(ValueError,match="scale factor"):
        imagery.frame_from_provenance(provenance)
