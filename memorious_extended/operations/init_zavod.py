import json

from ..zavod import get_zavod


def init(context, data):
    zavod = get_zavod(context)
    zavod.export_metadata("index.json")
    archive_manifest = context.params.get("archive_manifest")
    if archive_manifest is not None:
        fp = zavod.get_resource_path("archive.json")
        with open(fp, "w") as fh:
            json.dump(archive_manifest, fh)
    context.emit(data=data)
