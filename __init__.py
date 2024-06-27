bl_info = {
    "name": "Mixamo Fbx",
    "author": "SunZiBingFa@github.com",
    "version": (1, 0),
    "blender": (4, 10, 0),
    "location": "File > Import > Mixamo fbx(folder/*.fbx)",
    "description": "Batch Import Fbx (Mixamo) And Rename From File Name",
    "warning": "",
    "doc_url": "",
    "category": "Batch Import",
}



from . import import_mixamo_root_motion


def register():
    import_mixamo_root_motion.register()


def unregister():
    import_mixamo_root_motion.unregister()