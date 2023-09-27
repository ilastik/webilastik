# pyright: strict

if __name__ == "__main__":
    import sys
    from pathlib import Path
    import os

    project_root_dir = Path(__file__).parent.parent
    sys.path.append(str(project_root_dir))

    # This security env var flag should usually be set before running webilastik
    os.environ["WEBILASTIK_ALLOW_LOCAL_FS"] = "true"

    from typing import List
    from pathlib import PurePosixPath

    from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksSink
    from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
    from webilastik.datasource.precomputed_chunks_info import RawEncoder
    from webilastik.filesystem.os_fs import OsFs
    from webilastik.ui.datasource import try_get_datasources_from_url
    from webilastik.utility.url import Url

    url = Url.parse_or_raise("https://app.ilastik.org/public/images/c_cells_2.precomputed")
    output_dir = Path.home() / "blas.precomputed"

    fs = OsFs.create()
    if isinstance(fs, Exception):
        raise Exception(f"Could not write to local filesystem: {fs}")

    datasource_scales = try_get_datasources_from_url(url=url)
    if isinstance(datasource_scales, Exception):
        raise datasource_scales
    if not datasource_scales:
        raise Exception(f"No datasources found at {url}")

    precomp_datasources: List[PrecomputedChunksDataSource] = []
    for ds in datasource_scales:
        assert isinstance(ds, PrecomputedChunksDataSource), f"Expected precomp chunks datasource, found {ds}"
        precomp_datasources.append(ds)

        sink  = PrecomputedChunksSink(
            filesystem=fs,
            dtype=ds.dtype,
            encoding=RawEncoder(),
            interval=ds.interval,
            path=PurePosixPath(output_dir),
            resolution=ds.spatial_resolution,
            scale_key=ds.scale_key,
            tile_shape=ds.tile_shape,
        )
        writer = sink.open()
        assert not isinstance(writer, Exception), str(writer)

        for tile in ds.roi.get_datasource_tiles():
            print(f"Writing tile {tile} to {sink}", file=sys.stderr)
            writing_result = writer.write(tile.retrieve())
            assert not isinstance(writing_result, Exception), f"Failed writing tile {tile}: {writing_result}"