import bpy
import os

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty
from bpy.types import Operator, Panel
from mathutils import Vector


class ImportMixamo():
    def __init__(self, hips_name:str):
        """ init variables """
        self.obj = bpy.context.active_object
        self.intensity = self.obj.scale
        self.action = self.obj.animation_data.action

        for curve in self.obj.animation_data.action.fcurves:
            if curve.data_path == f'pose.bones["{bpy.utils.escape_identifier(hips_name)}"].location':
                if curve.array_index == 0:
                    self.curve_x = curve
                elif curve.array_index == 1:
                    self.curve_y = curve
                elif curve.array_index == 2:
                    self.curve_z = curve
    
    def rename_action(self, file_path:str):
        """ rename action, new name use file name """
        self.action.name = os.path.basename(file_path).split('.')[0]
        return {'FINISHED'}
    
    def remove_prefix_name(self, prefix_name:str):
        """ remove prefix name from the bone name"""
        bones = self.obj.pose.bones
        for bone in bones:
            if bone.name.startswith(prefix_name):
                bone.name = bone.name.replace(prefix_name, "")
        return {'FINISHED'}

    def delete_armature(self, armature_name:str):
        """ delete <Armature.00*>, delete cihld objects """
        if self.obj.name.startswith(armature_name + '.00'):
            bpy.ops.object.select_hierarchy(direction='CHILD', extend=True)
            bpy.ops.object.delete()
        return {'FINISHED'}

    def apply_all_transform(self):
        """ apply all transform to the object """
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        return {'FINISHED'}

    def scale_bone_action_intensity(self):
        """ Scale the action intensity of the bones, fix animation """
        ## x keyframes
        for kf in self.curve_x.keyframe_points:
            kf.co.y *= self.intensity.x
        ## y keyframes
        for kf in self.curve_y.keyframe_points:
            kf.co.y *= self.intensity.y
        ## z keyframs
        for kf in self.curve_z.keyframe_points:
            kf.co.y *= self.intensity.z
        return {'FINISHED'}
    
    def set_parent(self, child_bone_name:str, parent_bone_name:str):
        """ set parent of the root bone """
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.context.scene.frame_set(1)
        self.obj.data.edit_bones[child_bone_name].parent = self.obj.data.edit_bones[parent_bone_name]
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        return {'FINISHED'}

class BakeMethod():
    """ calculate the height of the root motion """
    def __init__(self, hips_name:str, method:str, bake_x:bool, bake_y:bool, bake_z:bool):
        self.obj = bpy.context.active_object
        self.hips_name = hips_name
        self.bake_x = bake_x
        self.bake_y = bake_y
        self.bake_z = bake_z
        self.method = method

        for curve in self.obj.animation_data.action.fcurves:
            if curve.data_path == f'pose.bones["{bpy.utils.escape_identifier(hips_name)}"].location':
                if curve.array_index == 0:
                    self.curve_x = curve
        
        self.frames = []
        for kf in self.curve_x.keyframe_points:
            detail_frame = [int(kf.co.x), float("0." + str(kf.co.x).split('.')[1])]
            self.frames.append(detail_frame)
    
    def get_location_in_world(self, bone_name:str) -> Vector:
        return self.obj.matrix_world @ self.obj.pose.bones[bone_name].head

    def copy_for_hips(self):
        """ copy for hips bone location in world """
        vectors, root_vectors = [], []
        for f in self.frames:
            bpy.context.scene.frame_set(f[0], subframe=f[1])
            vectors.append(self.get_location_in_world(bone_name=self.hips_name))
        root_vectors = [Vector((v.x * self.bake_x,
                                v.y * self.bake_y,
                                v.z * self.bake_z
                                )) for v in vectors]
        hips_vectors = [vectors[i] - root_vectors[i] for i in range(len(vectors))]
        first_point = vectors[0]
        root_vectors = [Vector((v.x - first_point.x * self.bake_x,
                                v.y - first_point.y * self.bake_y,
                                v.z - first_point.z * self.bake_z,
                                )) for v in root_vectors]
        hips_vectors = [Vector((v.x + first_point.x * self.bake_x,
                                v.y + first_point.y * self.bake_y,
                                v.z + first_point.z * self.bake_z,
                                )) for v in hips_vectors]
        return root_vectors, hips_vectors

    def main_bone(self):
        """ get main bone y_loc min_value (World Coordinate System)"""
        vectors, height_ls = [], []
        for f in self.frames:
            bpy.context.scene.frame_set(f[0], subframe=f[1])
            vectors.append(self.get_location_in_world(bone_name=self.hips_name))
            ## get main bone lowest height
            headtop = self.obj.pose.bones["mixamorig:HeadTop_End"]
            lefthand = self.obj.pose.bones["mixamorig:LeftHand"]
            righthand = self.obj.pose.bones["mixamorig:RightHand"]
            spline = self.obj.pose.bones["mixamorig:Spine"]
            lefttoe = self.obj.pose.bones["mixamorig:LeftToe_End"]
            righttoe = self.obj.pose.bones["mixamorig:RightToe_End"]
            height = min(headtop.head[2], lefthand.head[2], righthand.head[2], 
                        spline.head[2], lefttoe.head[2],  righttoe.head[2])
            height_ls.append(height)
        root_vectors = [Vector((vectors[i].x * self.bake_x,
                                vectors[i].y * self.bake_y,
                                height_ls[i] * self.bake_z
                                )) for i in range(len(vectors))]
        hips_vectors = [vectors[i] - root_vectors[i] for i in range(len(vectors))]
        ## root_on_floor x/z
        first_point = vectors[0]
        root_vectors = [Vector((v.x - first_point.x * self.bake_x,
                                v.y - first_point.y * self.bake_y,
                                v.z )) for v in root_vectors]
        hips_vectors = [Vector((v.x + first_point.x * self.bake_x,
                                v.y + first_point.y * self.bake_y,
                                v.z )) for v in hips_vectors]
        return root_vectors, hips_vectors

    def bound_box(self):
        """ get bound box center """
        vectors, root_vectors, hips_vectors, lowest_points = [], [], [], []
        for f in self.frames:
            bpy.context.scene.frame_set(f[0], subframe=f[1])
            bound_box_loc = [b[:] for b in self.obj.bound_box]
            low_point = Vector((min(x) for x in (list(zip(*bound_box_loc)))))
            vectors.append(self.get_location_in_world(bone_name=self.hips_name))
            lowest_points.append(low_point)
        root_vectors = [Vector((vectors[i].x * self.bake_x,
                                vectors[i].y * self.bake_y,
                                lowest_points[i].z * self.bake_z
                                )) for i in range(len(vectors))]
        hips_vectors = [vectors[i] - root_vectors[i] for i in range(len(vectors))]
        ## root_on_floor x / z
        first_point = root_vectors[0]
        root_vectors = [Vector((v.x - first_point.x * self.bake_x,
                                v.y - first_point.y * self.bake_y,
                                v.z )) for v in root_vectors]
        hips_vectors = [Vector((v.x + first_point.x * self.bake_x,
                                v.y + first_point.y * self.bake_y,
                                v.z )) for v in hips_vectors]
        return root_vectors, hips_vectors

    def run(self):
        match self.method:
            case "COPY_HIPS":
                return self.copy_for_hips()
            case "MAIN_BONE":
                return self.main_bone()
            case "BOUND_BOX":
                return self.bound_box()


class RootMotion():
    def __init__(self, hips_name:str):
        self.obj = bpy.context.active_object
        for curve in self.obj.animation_data.action.fcurves:
            if curve.data_path == f'pose.bones["{bpy.utils.escape_identifier(hips_name)}"].location':
                if curve.array_index == 0:
                    self.curve_x = curve
                elif curve.array_index == 1:
                    self.curve_y = curve
                elif curve.array_index == 2:
                    self.curve_z = curve

        ## get frames
        self.frames = []  ## -> [ whole_frame=float_value ]
        for kf in self.curve_x.keyframe_points:
            self.frames.append(kf.co.x)
    
    def add_root(self, root_name:str):
        """ add root bone"""
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        # create bone && set bone tail
        root = self.obj.data.edit_bones.new(root_name)
        root.head = (0.0, 0.0, 0.0)
        root.tail = (0.0, 0.0, 0.3)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        return {'FINISHED'}

    def vectors_world2local(self, bone_name, vectors) -> list:
        """ mapping coordinate system; world to local """
        local_bone = self.obj.pose.bones[bone_name]
        local_vectors = [self.obj.matrix_world.inverted() @ local_bone.bone.matrix_local.inverted() @ v 
                         for v in vectors]
        return local_vectors

    def bake_keyframes(self, bone_name, vectors):
        """ bake root motion keyframes """
        bone=self.obj.pose.bones[bone_name]
        local_vectors = self.vectors_world2local(bone_name, vectors)
        for i, f in enumerate(self.frames):
            bone.location = local_vectors[i]
            bone.keyframe_insert(data_path='location', frame=f, group=bone_name)
        return {'FINISHED'}

    def edit_keyframes(self, bone_name, vectors):
        """ edit hips bone keyframe points"""
        vectors = self.vectors_world2local(bone_name=bone_name, vectors=vectors)
        for i, kf in enumerate(self.curve_x.keyframe_points):
            kf.co.y = vectors[i].x
        for i, kf in enumerate(self.curve_y.keyframe_points):
            kf.co.y = vectors[i].y
        for i, kf in enumerate(self.curve_z.keyframe_points):
            kf.co.y = vectors[i].z
        return {'FINISHED'}


def import_mixamo_root_motion(context, file_path: str, is_apply_transform: bool, 
                              is_rename_action: bool, is_remove_prefix: bool, 
                              is_delete_armature: bool, is_add_root: bool,
                              method: str, bake_x: bool, bake_y: bool, bake_z: bool):
    """ main - batch """
    ## Parameters
    root_name = "Root"
    hips_name = "mixamorig:Hips"
    prefix_name = "mixamorig:"
    armature_name = "Armature"
    try:
        bpy.ops.import_scene.fbx(filepath=file_path)  ## import fbx file

        ## class instance
        importer = ImportMixamo(hips_name=hips_name)
        bake_method = BakeMethod(hips_name=hips_name, method=method,
                                bake_x=bake_x, bake_y=bake_y, bake_z=bake_z)
        root_motion = RootMotion(hips_name=hips_name)

        ## apply transform and fix animation
        if is_apply_transform:
            importer.scale_bone_action_intensity()
            importer.apply_all_transform()
        ## get vectors for bone
        if is_add_root and (bake_x, bake_y, bake_z):
            root_vectors, hips_vectors = bake_method.run()
        ## add root bone
        if is_add_root:
            root_motion.add_root(root_name=root_name)
        # ## bake root motion keyframes
        if is_add_root and (bake_x, bake_y, bake_z):
            root_motion.bake_keyframes(bone_name=root_name, vectors=root_vectors)
            root_motion.edit_keyframes(bone_name=hips_name, vectors=hips_vectors)
        # ## set parent
        if is_add_root:
            importer.set_parent(child_bone_name=hips_name, parent_bone_name=root_name)
        # ## rename action
        if is_rename_action:
            importer.rename_action(file_path=file_path)
        # ## remove prefix
        if is_remove_prefix:
            importer.remove_prefix_name(prefix_name=prefix_name)
        # ## delete armature
        if is_delete_armature:
            importer.delete_armature(armature_name=armature_name)
        context.scene.frame_set(1)  ## set frame to 1
    except Exception as e:
        print(e)
    return {'FINISHED'}


## ImportHelper
class BatchImport(Operator, ImportHelper):
    """ Batch import """
    bl_idname = "import_mixamo.root_motion"
    bl_label = "Import Mixamo *.Fbx"
    bl_options = {'PRESET'}

    # ImportHelper mix-in class uses this.
    filename_ext = ".fbx"
    
    files: CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'},
    ) # type: ignore

    directory: StringProperty(
        subtype='DIR_PATH'
    ) # type: ignore
    
    filter_glob: StringProperty(
        default="*.fbx",
        options={'HIDDEN'},
        maxlen=255,
    ) # type: ignore

    # List of operator properties
    is_apply_transforms: BoolProperty(
        name="Apply Transform",
        description="Recommended to keep it checked and fix animation, apply all transforms, if unchecked, root motion will have unpredictable results",
        default=True,
    ) # type: ignore
    
    is_add_root: BoolProperty(
        name="Add Root Bone",
        description="Add the root bone and set as parent, Root Motion use this bone to bake keyframes, if unchecked, Root Motion will not work.",
        default=True,
    ) # type: ignore
    
    is_rename_action: BoolProperty(
        name="Rename Action",
        description="Rename the name of the action animation using the filename",
        default=True,
    ) # type: ignore
    
    is_remove_prefix: BoolProperty(
        name="Remove prefix",
        description="Remove prefix names from all bones <mixamorig:>",
        default=True,
    ) # type: ignore
    
    is_delete_armature: BoolProperty(
        name="Remove Armature",
        description="Remove object <Armature.00*>",
        default=True,
    ) # type: ignore
    
    method: EnumProperty(
        name="Method",
        description="Root-Motion -> Bake keyframes: Height bake method",
        items=(
            ('COPY_HIPS', "Copy", "Copy from hips bone transform in wrold space"),
            ('MAIN_BONE', "Bone", "Copy hips bone X/Y, get lowest bone height as Z"),
            ('BOUND_BOX', "Bound box", "Copy hips bone X/Y, get Bound Box lowest as Z"),
        ),
        default='COPY_HIPS',
    ) # type: ignore
    
    bake_x: BoolProperty(
        name="X",
        description="Baking <X Location> to the Root Bone",
        default=True,
    ) # type: ignore
    
    bake_y: BoolProperty(
        name="Y",
        description="Baking <Y Location> to the Root Bone",
        default=True,
    ) # type: ignore
    
    bake_z: BoolProperty(
        name="Z",
        description="Baking <Z Location> to the Root Bone - Height",
        default=False,
    ) # type: ignore
    
    def execute(self, context):
        for file in self.files:
            file_path = os.path.join(self.directory, file.name)
            import_mixamo_root_motion(context, file_path=file_path, 
                                        is_apply_transform=self.is_apply_transforms, 
                                        is_rename_action=self.is_rename_action, 
                                        is_remove_prefix=self.is_remove_prefix, 
                                        is_delete_armature=self.is_delete_armature, 
                                        is_add_root=self.is_add_root,
                                        method=self.method, bake_x=self.bake_x, 
                                        bake_y=self.bake_y, bake_z=self.bake_z)
        return {'FINISHED'}
    
    def draw(self, context):
        pass

## Panel: import setings
class IMPORT_PT_base_settings(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Import Settings"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "IMPORT_MIXAMO_OT_root_motion"

    def draw(self, context):
        layout = self.layout
        sfile = context.space_data
        operator = sfile.active_operator
        column = layout.column(align=True)
        column.prop(operator, 'is_apply_transforms', icon='CON_TRANSFORM')
        column.prop(operator, 'is_add_root', icon='GROUP_BONE')
        column.prop(operator, 'is_remove_prefix', icon='BONE_DATA')
        column.prop(operator, 'is_rename_action', icon='ACTION')
        column.prop(operator, 'is_delete_armature', icon='TRASH')

## Panel: root motion settings
class IMPORT_PT_bake_settings(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Root Motion"
    bl_parent_id = "IMPORT_PT_base_settings"
    bl_options = {'HEADER_LAYOUT_EXPAND'}
    
    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "IMPORT_MIXAMO_OT_root_motion"

    def draw(self, context):
        layout = self.layout
        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, 'method')

        row = layout.row(align=True)
        row.prop(operator, 'bake_x', icon='KEYFRAME_HLT')
        row.prop(operator, 'bake_y', icon='KEYFRAME_HLT')
        row.prop(operator, 'bake_z', icon='KEYFRAME_HLT')


def menu_func_import(self, context):
    self.layout.operator(BatchImport.bl_idname, text="Mixamo fbx(folder/*.fbx)")
    
# Register and add to the "file selector" menu (required to use F3 search "Text Import Operator" for quick access).
def register():
    bpy.utils.register_class(BatchImport)
    bpy.utils.register_class(IMPORT_PT_base_settings)
    bpy.utils.register_class(IMPORT_PT_bake_settings)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(BatchImport)
    bpy.utils.unregister_class(IMPORT_PT_bake_settings)
    bpy.utils.unregister_class(IMPORT_PT_base_settings)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
    # test call
    bpy.ops.import_mixamo.root_motion('INVOKE_DEFAULT')
#    unregister()
