# pyright: strict



if __name__ == "__main__":
    import sys
    from pathlib import Path
    import os

    project_root_dir = Path(__file__).parent.parent
    sys.path.append(str(project_root_dir))

    # selecting a caching implementation is usually done in load-time, by setting PYTHONPATH
    # and pointing to something in project_root_dir / caching
    sys.path.append(str(project_root_dir / "caching/lru_cache"))

    # selecting an executor implementation is usually done in load-time, by setting PYTHONPATH
    # and pointing to something in project_root_dir / executor_getters
    sys.path.append(str(project_root_dir / "executor_getters/default"))

    # This security env var flag should usually be set before running webilastik
    os.environ["WEBILASTIK_ALLOW_LOCAL_FS"] = "true"


    from pathlib import PurePosixPath
    import math

    from webilastik.datasink.precomputed_chunks_sink import PrecomputedChunksSink
    from webilastik.datasource.precomputed_chunks_info import RawEncoder
    from webilastik.datasource.skimage_datasource import SkimageDataSource
    from webilastik.filesystem.os_fs import OsFs
    from webilastik.ui.applet.export_jobs import DownscaleDatasource

    fs = OsFs.create(); assert not isinstance(fs, Exception), str(fs)
    datasource = SkimageDataSource(
        filesystem=fs, path=PurePosixPath(project_root_dir) / "public/images/c_cells_1.png"
    )
    output_dir = Path.home() / "blas.precomputed"

    for level in range(999):
        scale = 2 ** level
        sink_shape = datasource.shape.updated(
            x=math.ceil(datasource.shape.x / scale),
            y=math.ceil(datasource.shape.y / scale),
        )
        sink  = PrecomputedChunksSink(
            filesystem=fs,
            dtype=datasource.dtype,
            encoding=RawEncoder(),
            interval=sink_shape.to_interval5d(),
            path=PurePosixPath(output_dir),
            resolution=( # this is the physical size of each voxel in nm, as per the spec
                datasource.spatial_resolution[0] * scale,
                datasource.spatial_resolution[1] * scale,
                datasource.spatial_resolution[2] * scale,
            ),
            scale_key=PurePosixPath(f"level_{level}"),
            tile_shape=datasource.tile_shape,
        )

        sink_writer = sink.open()
        assert not isinstance(sink_writer, Exception)

        for sink_tile in sink.interval.split(sink.tile_shape):
            print(f"Writing to sink tile {sink_tile} from scale at level {level}", file=sys.stderr)
            # note that this always scales down from the finest resolution.
            # Check PixelClassificationExportApplet._launch_downscaling_job for an example of downscaling
            #   from the previous level
            writing_result = DownscaleDatasource.downscale(sink_tile=sink_tile, source=datasource, sink_writer=sink_writer)
            assert not isinstance(writing_result, Exception), str(writing_result)

        # Uncomment these to show the downscaled imags in your web browser. Be careful with huge or 3D images, though
        #import PIL
        #import tempfile
        #temp_f = tempfile.NamedTemporaryFile(suffix=".png")
        #PIL.Image.fromarray(sink.to_datasource().retrieve().raw("yxc")).save(temp_f)
        #import webbrowser
        #_ = webbrowser.open_new_tab(f"file://{temp_f.name}")

        if sink_shape.x == 1 and sink_shape.y == 1:
            break
