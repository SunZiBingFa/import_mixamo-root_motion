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

import bpy
import os

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator, Panel
from mathutils import Vector


def rename_action_animation(file :str, old_action_prefix="Armature"):
    """rename action animation; return new name"""
    bpy.context.active_object.animation_data.action.name = os.path.splitext(file)[0]
    return

def scale_bone_anim_strength(strength=0.01):
    """Scale the animation intensity of the bones by 0.01x"""
    # get X/Y/Z Location Keyframe
    action_name = bpy.context.active_object.animation_data.action.name
    bone_name="mixamorig:Hips"
    
    for curve in bpy.data.actions[action_name].fcurves:
        if curve.data_path == 'pose.bones["%s"].location' % (bone_name):
            if curve.array_index == 0:
                for keyframe in curve.keyframe_points:
                    x_loc = keyframe.co
                    x_loc.y *= strength
                    keyframe.co = x_loc
                x_loc_kf = curve.keyframe_points

            elif curve.array_index == 1:
                for keyframe in curve.keyframe_points:
                    y_loc = keyframe.co
                    y_loc.y *= strength
                    keyframe.co = y_loc
                y_loc_kf = curve.keyframe_points

            elif curve.array_index == 2:
                for keyframe in curve.keyframe_points:
                    z_loc = keyframe.co
                    z_loc.y *= strength
                    keyframe.co = z_loc
                z_loc_kf = curve.keyframe_points
    return


def add_root_bone(root_bone_name="Root"):
    """Add root bone, set the bone tail length, set the parent of hips to root"""
    obj = bpy.context.active_object
    hips_bone_name="mixamorig:Hips"
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    
    # create bone && set bone tail
    root_bone = obj.data.edit_bones.new(root_bone_name)
    root_bone.head = (0, 0, 0)
    root_bone.tail = (0, 0, 0.3)
    
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    return

def set_bone_parent(child_bone_name="mixamorig:Hips", parent_bone_name="Root"):
    """ set bone parent"""
    obj = bpy.context.active_object
    bpy.context.scene.frame_set(1)
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    obj.data.edit_bones[child_bone_name].parent = obj.data.edit_bones[parent_bone_name]
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    return

def remove_prefix(prefix="mixamorig:"):
    """ remove bones name prefix """
    bones = bpy.context.active_object.pose.bones
    for bone in bones:
        if bone.name.startswith(prefix):
            bone.name = bone.name.replace(prefix, "")
    return

def delete_armature(armature_name="Armature"):
    """ get scene objects, remove Armature.00*"""
    if bpy.context.active_object.name.startswith(armature_name + '.00'):
        ## delete obj and children obj
        bpy.ops.object.select_hierarchy(direction='CHILD', extend=True)
        bpy.ops.object.delete()
    return

## Bake Keyframe - Root Motion
    """ ... """
def bone_loc_curve(bone_name="mixamorig:Hips"):
    action_name = bpy.context.active_object.animation_data.action.name
    ## get Keyframes
    for curve in bpy.data.actions[action_name].fcurves:
        if curve.data_path == 'pose.bones["%s"].location' % (bone_name):
            return curve


def bone_releative_vec(abone_name="mixamorig:Hips", bbone_name="Root"):
    """ abone releative moving vector ; root bone coordinate system"""
    obj = bpy.context.active_object
    abone = obj.pose.bones[abone_name]
    bbone = obj.pose.bones[bbone_name]
    
    curve = bone_loc_curve(bone_name=abone_name)

    ## keyframes.co.x , current frames
    for kf in curve.keyframe_points:
        subframe = float("0." + str(kf.co.x).split('.')[1])
        bpy.context.scene.frame_set(int(kf.co.x), subframe=subframe)                           ## set current frame
        if kf.co.x == 1.0:
            orig_point = abone.matrix.translation @ bbone.matrix           ## original points
            rel_vectors = [Vector((0, 0, 0))] 
            abs_vectors = [orig_point]
        else:
            abs_vec = abone.matrix.translation @ bbone.matrix
            releative_vec = abone.matrix.translation @ bbone.matrix - orig_point
            rel_vectors.append(releative_vec)
            abs_vectors.append(abs_vec)
    
    return rel_vectors, abs_vectors

def method_bone_ylist() -> []:
    """ get bone y_loc min_value (World Coordinate System)"""
    obj = bpy.context.active_object
    y_ls = []
    curve = bone_loc_curve()
    
    headtop = obj.pose.bones["mixamorig:HeadTop_End"]
    lefthand = obj.pose.bones["mixamorig:LeftHand"]
    righthand = obj.pose.bones["mixamorig:RightHand"]
    spline = obj.pose.bones["mixamorig:Spine"]
    lefttoe = obj.pose.bones["mixamorig:LeftToe_End"]
    righttoe = obj.pose.bones["mixamorig:RightToe_End"]
    
    for kf in curve.keyframe_points:
        subframe = float("0." + str(kf.co.x).split('.')[1])
        bpy.context.scene.frame_set(int(kf.co.x), subframe=subframe)
        y_loc = min(headtop.head[2], 
                    lefthand.head[2], 
                    righthand.head[2], 
                    spline.head[2],
                    lefttoe.head[2], 
                    righttoe.head[2])
        y_ls.append(y_loc)

    return y_ls

def get_bound_box_y() -> []:
    """ get bound box lowest point y """
    obj = bpy.context.active_object
    armature_bound_box = [b[:] for b in obj.bound_box]
    
    if obj.children:
        child_bound_boxs = []
        for child in obj.children:
            if child.type == 'MESH':
                child_bound_boxs += [c[:] for c in child.bound_box]
        value = min(list(zip(*child_bound_boxs))[2])
    else:
        value = min(list(zip(*armature_bound_box))[2])
        
    return value

def method_bound_box_ylist() -> []:
    curve = bone_loc_curve()
    y_ls = []
    for kf in curve.keyframe_points:
        subframe = float("0." + str(kf.co.x).split('.')[1])
        bpy.context.scene.frame_set(int(kf.co.x), subframe=subframe)
        y_ls.append(get_bound_box_y())
    return y_ls

def bone_keyframes_insert(bone_name="Root", curve=None, vectors=[]):
    """ insert keyframes - root bone """
    obj = bpy.context.active_object
    bone = obj.pose.bones[bone_name]

    for i, kf in enumerate(curve.keyframe_points):        ## set root x y z keyframe points
        bone.location = vectors[i]
        bone.keyframe_insert(data_path='location', frame=kf.co.x)
    return

def bone_keyframe_fix(hips_name="mixamorig:Hips", root_name="Root", vectors=[]):
    """ bone keyframe offset to fix; hips bone local coordinate system """
    obj = bpy.context.active_object
    hips = obj.pose.bones[hips_name]
    root = obj.pose.bones[root_name]
    
    vectors = [root.bone.matrix @ v for v in vectors] ## hips bone map to armature coordinate system
    local_kf = [obj.matrix_world.inverted() @ hips.bone.matrix_local.inverted() @ v for v in vectors] ## hips bone map to local coordinate system
    
    ## set keyframes
    action_name = bpy.context.active_object.animation_data.action.name
    for curve in bpy.data.actions[action_name].fcurves:
        if curve.data_path == 'pose.bones["%s"].location' % (hips_name):
            if curve.array_index == 0:
                for i, kf in enumerate(curve.keyframe_points):
                    kf.co.y = local_kf[i][0]
                    
            elif curve.array_index == 1:
                for i, kf in enumerate(curve.keyframe_points):
                    kf.co.y = local_kf[i][1]
                    
            elif curve.array_index == 2:
                for i, kf in enumerate(curve.keyframe_points):
                    kf.co.y = local_kf[i][2]

def get_bone_vectors(bake_x=True, bake_y=True, bake_z=True, y_ls=[]):
    ## parm
    rel_vectors, abs_vectors = bone_releative_vec()
    
    ## set root keyframes
    if y_ls: ## Others Method
        root_vectors = [Vector((v.x * bake_x, y_ls[i] * bake_y, v.z * bake_z)) for i, v in enumerate(rel_vectors)] # root moving Vector * switch x y z
    else:  ## COPY Method
        root_vectors = [Vector((v.x * bake_x, v.y * bake_y, v.z * bake_z)) for i, v in enumerate(rel_vectors)] # root moving Vector * switch x y z
    
    hips_vectors = [abs_vectors[i] - root_vectors[i] for i in range(len(root_vectors))]
    
    return root_vectors, hips_vectors


def bake_root_motion(root_vectors, hips_vectors):
    """ bake_root_motion main func """
    ## Record Parm
    hips_curve = bone_loc_curve()

    ## set keyframe
    bone_keyframes_insert(bone_name="Root", curve=hips_curve, vectors=root_vectors)     ## set root bone keyframe
    bone_keyframe_fix(hips_name="mixamorig:Hips", root_name="Root", vectors=hips_vectors)       ## fix hips bone keyframe


## main <---
def batch_import_mixamo(context, directory, is_add_root, is_apply_transforms, bake_method, 
                        bake_x, bake_y, bake_z, is_rename_animation, is_remove_prefix, is_remove_armature):
    """Batch imort fbx (mixamo)"""
    try:
        ## variable
        root_bone_name="Root"
        prefix="mixamorig:"
        armature_name="Armature"
        bake_y, bake_z = bake_z, bake_y  ## for user Z as height
        
        if not os.path.isdir(directory):
            directory = os.path.dirname(directory)
        ## Record the fbx file name and filter out the fbx file
        files_name = [f for f in os.listdir(directory) if os.path.splitext(f)[-1][1:].lower() == 'fbx']
        
        for file in files_name:
            file_path = os.path.join(directory, file)
            
            ## Import fbx
            bpy.ops.import_scene.fbx(filepath=file_path)
            
            ## Rename Animation
            if is_rename_animation:
                rename_action_animation(file)
            
            if is_apply_transforms:
                ## Record active object X Scale
                active_obj_scale = bpy.context.active_object.scale[0]
                ## Apply Object All Transform
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                ## Scale Action Strength
                scale_bone_anim_strength(strength=active_obj_scale)

            if is_add_root and (bake_x or bake_y or bake_z):
                match bake_method:
                    case "COPY":
                        y_ls = []
                    case "BONE":
                        y_ls = method_bone_ylist()
                    case "BOUND_BOX":
                        y_ls = method_bound_box_ylist()

            
            ## Add Root Bone
            if is_add_root:
                add_root_bone(root_bone_name=root_bone_name)
            
            if is_add_root and (bake_x or bake_y or bake_z):
                root_vectors, hips_vectors = get_bone_vectors(bake_x=bake_x, bake_y=bake_y, bake_z=bake_z, y_ls=y_ls)
                bake_root_motion(root_vectors, hips_vectors)
            
            if is_add_root:
                set_bone_parent()

            ## remove prefix "mixamorig"
            if is_remove_prefix:
                remove_prefix(prefix=prefix)
        
            ## remove Armature.00* and child
            if is_remove_armature:
                delete_armature(armature_name=armature_name)
        
    except Exception as e:
        print("Error! %s" %e)

    return {'FINISHED'}



## ImportHelper
class BatchImport(Operator, ImportHelper):
    """ Batch import """
    bl_idname = "import_mixamo.root_motion"
    bl_label = "Import Mixamo *.Fbx"
    bl_options = {'PRESET'}

    # ImportHelper mix-in class uses this.
    filename_ext = ""
    
    directory: StringProperty(subtype='DIR_PATH')
    
    filter_glob: StringProperty(
        default="",
        options={'HIDDEN'},
        maxlen=255,
    )


    # List of operator properties
    is_apply_transforms: BoolProperty(
        name="Apply transforms",
        description="Recommended to keep it checked, apply all transforms and fix animation intensity",
        default=True,
    )
    
    is_add_root: BoolProperty(
        name="Add Root Bone",
        description="Add the root bone, Root Motion needs to use this bone to bake keyframes, if unchecked, Root Motion will not work.",
        default=True,
    )
    
    is_rename_animation: BoolProperty(
        name="Rename Action",
        description="Rename the name of the action animation using the filename",
        default=True,
    )
    
    is_remove_prefix: BoolProperty(
        name="Remove prefix",
        description="Remove prefix names from all bones <mixamorig:>",
        default=True,
    )
    
    is_remove_armature: BoolProperty(
        name="Remove Armature",
        description="Remove object <Armature.00*>",
        default=True,
    )
    
    bake_method: EnumProperty(
        name="Method",
        description="Root-Motion -> Bake keyframes: Height bake method",
        items=(
            ('COPY', "Copy", "Copy from hips bone delta_height animation"),
            ('BONE', "Bone", "Armature -> lowest Bone"),
            ('BOUND_BOX', "Bound box", "Armature -> Bound Box -> lowset height"),
        ),
        default='COPY',
    )
    
    bake_x: BoolProperty(
        name="X",
        description="Baking <X Location> to the Root Bone",
        default=True,
    )
    
    bake_y: BoolProperty(
        name="Y",
        description="Baking <Y Location> to the Root Bone",
        default=True,
    )
    
    bake_z: BoolProperty(
        name="Z",
        description="Baking <Z Location> to the Root Bone - Height",
        default=False,
    )
    
    def execute(self, context):
        return batch_import_mixamo(context, self.filepath, self.is_add_root, self.is_apply_transforms, self.bake_method, self.bake_x, self.bake_y, self.bake_z,
            self.is_rename_animation, self.is_remove_prefix, self.is_remove_armature)
    
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
        column.prop(operator, 'is_rename_animation', icon='ACTION')
        column.prop(operator, 'is_remove_armature', icon='TRASH')

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
        
        layout.prop(operator, 'bake_method')
        
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
