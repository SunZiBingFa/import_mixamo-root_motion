bl_info = {
    "name": "Mixamo Fbx · Root Motion",
    "author": "SunZiBingFa@github.com",
    "version": (1, 0, 3),
    "blender": (4, 2, 0),
    "location": "File > Import > Mixamo fbx(folder/*.fbx)",
    "description": "Batch import fbx (Mixamo) and create root motion",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

from . import import_mixamo_root_motion
import bpy
from .translations import translations_dict


def register():
    bpy.app.translations.register(__name__, translations_dict)
    import_mixamo_root_motion.register()

def unregister():
    bpy.app.translations.unregister(__name__)
    import_mixamo_root_motion.unregister()