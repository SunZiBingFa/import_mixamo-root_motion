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
    cur_obj = bpy.context.active_object
    hips_bone_name="mixamorig:Hips"
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    
    # create bone && set bone tail
    root_bone = cur_obj.data.edit_bones.new(root_bone_name)
    root_bone.head = (0, 0, 0)
    root_bone.tail = (0, 0, 0.3)
    
    ## set bone parent
    cur_obj.data.edit_bones[hips_bone_name].parent = cur_obj.data.edit_bones[root_bone_name]
    
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


## Method "COPY"
def get_y_offset():
    """ get endbone y_loc min_value"""
    active_obj = bpy.context.active_object
    
    headtop = active_obj.pose.bones["mixamorig:HeadTop_End"].head
    lefthand = active_obj.pose.bones["mixamorig:LeftHand"].head
    righthand = active_obj.pose.bones["mixamorig:RightHand"].head
    spline = active_obj.pose.bones["mixamorig:Spine"].head
    lefttoe = active_obj.pose.bones["mixamorig:LeftToe_End"].head
    righttoe = active_obj.pose.bones["mixamorig:RightToe_End"].head
    
    y_offset = min(headtop[2], lefthand[2], righthand[2], spline[2],lefttoe[2], righttoe[2])
    return y_offset

def copy_keyframe_hips2root(
        root_bone_name="Root", bake_x=True, bake_y=False, bake_z=True):
    """Copy the keyframes of the hips bone to the root bone"""
    
    ## variable
    hips_bone_name="mixamorig:Hips"
    action_name = bpy.context.active_object.animation_data.action.name
    
    ## root bone insert keyframe
    root_bone = bpy.context.active_object.pose.bones[root_bone_name]
    root_bone.keyframe_insert('location')
    
    ## variable -> y offset list
    y_offset_ls = []
    
    ## copy hips x/z location keyframe
    fcurves = bpy.data.actions[action_name].fcurves
    for curve in fcurves:
        if curve.data_path == 'pose.bones["%s"].location' % (hips_bone_name):
            if curve.array_index == 0 and bake_x:
                x_loc_curve = curve
            elif curve.array_index == 1 and bake_y:
                y_loc_curve = curve
                for kf in curve.keyframe_points:
                    bpy.context.scene.frame_set(int(kf.co.x))
                    y_offset = get_y_offset()
                    y_offset_ls.append(y_offset)
            elif curve.array_index == 2 and bake_z:
                z_loc_curve = curve

    ## set root bone loc keyframe
    for curve in fcurves:
        if curve.data_path == 'pose.bones["%s"].location' % (root_bone_name):
            if curve.array_index == 0 and bake_x:
                for kf in x_loc_curve.keyframe_points:
                    bpy.context.scene.frame_set(int(kf.co.x))
                    root_bone.keyframe_insert('location')
                    curve.keyframe_points[int(kf.co.x)-1].co = kf.co

            elif curve.array_index == 1 and bake_y:
                for kf in y_loc_curve.keyframe_points:
                    bpy.context.scene.frame_set(int(kf.co.x))
                    root_bone.keyframe_insert('location')
                    curve.keyframe_points[int(kf.co.x)-1].co.y = y_offset_ls[int(kf.co.x)-1]

            elif curve.array_index == 2 and bake_z:
                for kf in z_loc_curve.keyframe_points:
                    bpy.context.scene.frame_set(int(kf.co.x))
                    root_bone.keyframe_insert('location')
                    curve.keyframe_points[int(kf.co.x)-1].co = kf.co
    
    # del hips x/z location keyframes
    bpy.context.scene.frame_set(1)
    for curve in fcurves:
        if curve.data_path == 'pose.bones["%s"].location' % (hips_bone_name):
            if curve.array_index == 0 and bake_x:
                fcurves.remove(curve)
            elif curve.array_index == 2 and bake_z:
                fcurves.remove(curve)

    ## hips bone y locatioin sub y offset
    for curve in fcurves:
        if curve.data_path == 'pose.bones["%s"].location' % (hips_bone_name):
            if curve.array_index == 1 and bake_y:
                for kf in y_loc_curve.keyframe_points:
                    kf.co.y -= y_offset_ls[int(kf.co.x)-1]

    bpy.context.scene.frame_set(1)
    return


## Method: "CENTER"
def get_bound_box_center():
    """ get bound box center.x,y and bound_box lowest.z ; world orig"""
    act_obj = bpy.context.active_object
    armature_bound_box = [b[:] for b in act_obj.bound_box]
    armature_center = [value / len(armature_bound_box) 
        for value in list(map(sum, zip(*armature_bound_box)))]

    x_value = armature_center[0]
    y_value = armature_center[1]
    
    if not act_obj.children:
        z_value = min(list(zip(*armature_bound_box))[2])
    else:
        child_bound_boxs = []
        for child in act_obj.children:
            if child.type == 'MESH':
                child_bound_boxs += [c[:] for c in child.bound_box]
        z_value = min(list(zip(*child_bound_boxs))[2])
  
    return x_value, y_value, z_value        ## Global x, y, z


def record_center():
    """ calculate center x,y,z; record """
    action_name = bpy.context.active_object.animation_data.action.name
    hips_bone = bpy.context.active_object.pose.bones["mixamorig:Hips"]
    fcurves = bpy.data.actions[action_name].fcurves
    x_ls, y_ls, z_ls = [], [], []
    
    for curve in fcurves:
        if curve.data_path == 'pose.bones["mixamorig:Hips"].location' and curve.array_index == 0:
            for kf in curve.keyframe_points:
                bpy.context.scene.frame_set(int(kf.co.x))
                gl_x, gl_y, gl_z = get_bound_box_center()
                x, y, z = gl_x, gl_z, -gl_y            ## map Global Orientations to bone Local Orientations
                x_ls.append(x)
                y_ls.append(y)
                z_ls.append(z)
    
    return x_ls, y_ls, z_ls


def bake_root_keyframe(root_bone_name='Root', bake_x=True, bake_y=True, bake_z=True,
                            x_ls=[], y_ls=[], z_ls=[]):
    """ aaaa """
    action_name = bpy.context.active_object.animation_data.action.name
    ## insert a keyframe -> active root bone fcurves
    root_bone = bpy.context.active_object.pose.bones[root_bone_name]
    bpy.context.scene.frame_set(1)
    root_bone.keyframe_insert('location')
    
    ## apply x, y, z
    fcurves = bpy.data.actions[action_name].fcurves
    for curve in fcurves:
        if curve.data_path == 'pose.bones["%s"].location' % (root_bone_name):
            if curve.array_index == 0 and bake_x:
                for i, v in enumerate(x_ls):
                    bpy.context.scene.frame_set(i+1)
                    root_bone.keyframe_insert('location')
                    curve.keyframe_points[i].co.y = v
                    
            elif curve.array_index == 1 and bake_y:
                for i, v in enumerate(y_ls):
                    bpy.context.scene.frame_set(i+1)
                    root_bone.keyframe_insert('location')
                    curve.keyframe_points[i].co.y = v
            
            if curve.array_index == 2 and bake_z:
                for i, v in enumerate(z_ls):
                    bpy.context.scene.frame_set(i+1)
                    root_bone.keyframe_insert('location')
                    curve.keyframe_points[i].co.y = v


#    ## hip loc keyframe sub offset value
    for curve in fcurves:
        if curve.data_path == 'pose.bones["mixamorig:Hips"].location':
            if curve.array_index == 0 and bake_x:
                for kf in curve.keyframe_points:
                    kf.co.y -= x_ls[int(kf.co.x)-1]
            if curve.array_index == 1 and bake_y:
                for kf in curve.keyframe_points:
                    kf.co.y -= y_ls[int(kf.co.x)-1]
            if curve.array_index == 2 and bake_z:
                for kf in curve.keyframe_points:
                    kf.co.y -= z_ls[int(kf.co.x)-1]

    bpy.context.scene.frame_set(1)
    return


def batch_import_mixamo(context, directory, is_add_root, is_apply_transforms, bake_method, 
                        bake_x, bake_y, bake_z, is_rename_animation, is_remove_prefix, is_remove_armature):
    """Batch imort fbx (mixamo)"""
    try:
        ## variable
        root_bone_name="Root"
        prefix="mixamorig:"
        armature_name="Armature"
        
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

            ## Record
            x_ls, y_ls, z_ls = record_center()
            
            ## Add Root Bone
            if is_add_root:
                add_root_bone(root_bone_name=root_bone_name)
            
            ## Copy Hips Bone location x/y/z keframe to Root Bone
            if is_add_root and (bake_x or bake_y or bake_z):
                match bake_method:
                    case "COPY":
                        copy_keyframe_hips2root(root_bone_name=root_bone_name, bake_x=bake_x, bake_y=bake_y, bake_z=bake_z)
                    case "CENTER":
                        bake_root_keyframe(root_bone_name=root_bone_name,bake_x=bake_x, bake_y=bake_y, bake_z=bake_z,
                            x_ls=x_ls, y_ls=y_ls, z_ls=z_ls)

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
        description="Apply all transforms and fix animation intensity",
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
        description="Baked root bone keyframing method",
        items=(
            ('COPY', "Copy", "Copy the keyframes from the Hip bone to the Root bone."),
            ('CENTER', "Center", "Calculate the center of gravity of the bounding box, and the lowest point"),
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
        default=False,
    )
    
    bake_z: BoolProperty(
        name="Z",
        description="Baking <Z Location> to the Root Bone",
        default=True,
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
        row.prop(operator, 'bake_x', icon='DECORATE')
        row.prop(operator, 'bake_y', icon='DECORATE')
        row.prop(operator, 'bake_z', icon='DECORATE')


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
