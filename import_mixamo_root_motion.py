import bpy
import os

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty
from bpy.types import Operator, Panel, Object, Action
from bpy.utils import escape_identifier
from mathutils import Vector


def get_fcurve(action: Action, main_bone: str):
    """ bone: fcurve; According to the method obtained by switching versions """
    if bpy.app.version >= (4, 4, 0):
        ## When importing an FBX file, the slot and strip automatically created by Blender are set to the first one by default.
        slot = action.slots[0]
        strip = action.layers[0].strips[0]
        channelbag = strip.channelbag(slot)
        curve_x = channelbag.fcurves.find(f'pose.bones["{main_bone}"].location', index=0)
        curve_y = channelbag.fcurves.find(f'pose.bones["{main_bone}"].location', index=1)
        curve_z = channelbag.fcurves.find(f'pose.bones["{main_bone}"].location', index=2)
    else:
        curve_x = action.fcurves.find(f'pose.bones["{main_bone}"].location', index=0)
        curve_y = action.fcurves.find(f'pose.bones["{main_bone}"].location', index=1)
        curve_z = action.fcurves.find(f'pose.bones["{main_bone}"].location', index=2)

    return curve_x, curve_y, curve_z

class ImportMixamo():
    def __init__(self, obj: Object, main_bone_name: str):
        """ init variables """
        self.obj = obj
        self.intensity = self.obj.scale.copy()
        self.action = self.obj.animation_data.action
        self.curve_x, self.curve_y, self.curve_z = get_fcurve(action=self.action, main_bone=main_bone_name)
    
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
    
    def suffix_format(self):
        """ Use lowercase bone names, remove 'left'/'right' from the names, and replace them with a '.L'/.R' suffix """
        bones = self.obj.pose.bones
        for bone in bones:
            bone.name = bone.name.lower()
            if "left" in bone.name:
                bone.name = bone.name.replace("left", "") + ".L"
            elif "right" in bone.name:
                bone.name = bone.name.replace("right", "") + ".R"
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
    
    def set_parent(self, child_bone:str, parent_bone:str):
        """ set parent of the root bone """
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.context.scene.frame_set(1)
        self.obj.data.edit_bones[child_bone].parent = self.obj.data.edit_bones[parent_bone]
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        return {'FINISHED'}


class BakeMethod():
    """ calculate the height of the root motion """
    def __init__(self, obj, main_bone_name: str, method: str, is_start_feet: bool,
                bake_x: bool, bake_y: bool, bake_z: bool, head_top_bone_name: str,
                spine_bone_name: str, left_hand_bone_name: str, right_hand_bone_name: str,
                left_foot_bone_name: str, right_foot_bone_name: str, left_toe_bone_name: str,
                right_toe_bone_name: str):
        self.obj = obj
        self.action = obj.animation_data.action
        self.main_bone_name = main_bone_name
        self.bake_x = bake_x
        self.bake_y = bake_y
        self.bake_z = bake_z
        self.method = method
        self.is_start_feet = is_start_feet

        self.head_top_bone_name = head_top_bone_name
        self.spine_bone_name = spine_bone_name
        self.left_hand_bone_name = left_hand_bone_name
        self.right_hand_bone_name = right_hand_bone_name
        self.left_foot_bone_name = left_foot_bone_name
        self.right_foot_bone_name = right_foot_bone_name
        self.left_toe_bone_name = left_toe_bone_name
        self.right_toe_bone_name = right_toe_bone_name

        self.start_point = self.get_start_point()

        self.curve_x, _, _ = get_fcurve(action=self.action, main_bone=main_bone_name)

        self.frames = []
        for kf in self.curve_x.keyframe_points:
            detail_frame = [int(kf.co.x), float("0." + str(kf.co.x).split('.')[1])]
            self.frames.append(detail_frame)
    
    def get_location_in_world(self, bone_name:str) -> Vector:
        return self.obj.matrix_world @ self.obj.pose.bones[bone_name].head
    
    def get_start_point(self):
        """ get first point 待完成... """
        bpy.context.scene.frame_set(1)
        left_foot = self.get_location_in_world(bone_name=self.left_foot_bone_name)
        right_foot = self.get_location_in_world(bone_name=self.right_foot_bone_name)
        start_point = (left_foot + right_foot) / 2 * Vector((1, 1, 0))
        return start_point

    def copy_for_main_bone(self):
        """ copy for main bone [mixamorig:Hips] location in world """
        vectors, root_vectors = [], []
        for f in self.frames:
            bpy.context.scene.frame_set(f[0], subframe=f[1])
            vectors.append(self.get_location_in_world(bone_name=self.main_bone_name))
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
        first_point = vectors[0] - self.start_point * self.is_start_feet
        hips_vectors = [Vector((v.x + first_point.x * self.bake_x,
                                v.y + first_point.y * self.bake_y,
                                v.z + first_point.z * self.bake_z,
                                )) for v in hips_vectors]
        return root_vectors, hips_vectors

    def get_lowest_bone_height(self):
        """ get main bone y_loc min_value (World Coordinate System)"""
        vectors, min_height_ls = [], []
        for f in self.frames:
            bpy.context.scene.frame_set(f[0], subframe=f[1])
            vectors.append(self.get_location_in_world(bone_name=self.main_bone_name))
            ## get main bone lowest height
            headtop = self.obj.pose.bones[self.head_top_bone_name]
            lefthand = self.obj.pose.bones[self.left_hand_bone_name]
            righthand = self.obj.pose.bones[self.right_hand_bone_name]
            spine = self.obj.pose.bones[self.spine_bone_name]
            lefttoe = self.obj.pose.bones[self.left_toe_bone_name]
            righttoe = self.obj.pose.bones[self.right_toe_bone_name]
            min_height = min(headtop.head[2], lefthand.head[2], righthand.head[2], 
                        spine.head[2], lefttoe.head[2],  righttoe.head[2])
            min_height_ls.append(min_height)

        root_vectors = [Vector((vectors[i].x * self.bake_x,
                                vectors[i].y * self.bake_y,
                                min_height_ls[i] * self.bake_z
                                )) for i in range(len(vectors))]
        hips_vectors = [vectors[i] - root_vectors[i] for i in range(len(vectors))]
        ## root_on_floor x/z
        first_point = vectors[0] - self.start_point
        root_vectors = [Vector((v.x - first_point.x * self.bake_x,
                                v.y - first_point.y * self.bake_y,
                                v.z )) for v in root_vectors]
        first_point = vectors[0] - self.start_point * self.is_start_feet
        hips_vectors = [Vector((v.x + first_point.x * self.bake_x,
                                v.y + first_point.y * self.bake_y,
                                v.z )) for v in hips_vectors]
        return root_vectors, hips_vectors

    def get_bound_box_bottom(self):
        """ get bound box center """
        vectors, root_vectors, hips_vectors, lowest_points = [], [], [], []
        for f in self.frames:
            bpy.context.scene.frame_set(f[0], subframe=f[1])
            vectors.append(self.get_location_in_world(bone_name=self.main_bone_name))

            bound_box = [self.obj.matrix_world @ Vector(v) for v in self.obj.bound_box]
            lowest_point = min(bound_box, key=lambda v:v.z)
            lowest_points.append(lowest_point)

        root_vectors = [Vector((vectors[i].x * self.bake_x,
                                vectors[i].y * self.bake_y,
                                lowest_points[i].z * self.bake_z
                                )) for i in range(len(vectors))]
        hips_vectors = [vectors[i] - root_vectors[i] for i in range(len(vectors))]
        ## root_on_floor x / z
        first_point = root_vectors[0] - self.start_point
        root_vectors = [Vector((v.x - first_point.x * self.bake_x,
                                v.y - first_point.y * self.bake_y,
                                v.z )) for v in root_vectors]
        first_point = vectors[0] - self.start_point * self.is_start_feet
        hips_vectors = [Vector((v.x + first_point.x * self.bake_x,
                                v.y + first_point.y * self.bake_y,
                                v.z )) for v in hips_vectors]
        return root_vectors, hips_vectors

    def run(self):
        match self.method:
            case "COPY_DATA":
                return self.copy_for_main_bone()
            case "LOWEST_BONE":
                return self.get_lowest_bone_height()
            case "BOUND_BOX":
                return self.get_bound_box_bottom()


class RootMotion():
    def __init__(self, obj, main_bone_name:str):
        self.obj = obj
        self.action = self.obj.animation_data.action
        self.curve_x, self.curve_y, self.curve_z = get_fcurve(self.action, main_bone=main_bone_name)

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


def main(context, file_path: str, is_apply_transform: bool, is_rename_action: bool, is_remove_prefix: bool, 
        is_suffix_format: bool,is_delete_armature: bool, is_add_root: bool, method: str, is_start_feet: bool,
        bake_x: bool, bake_y: bool, bake_z: bool, armature_name: str, root_name: str, prefix_name: str,
        main_bone_name: str, head_top_bone_name: str, spine_bone_name: str, left_hand_bone_name: str,
        right_hand_bone_name: str, left_foot_bone_name: str, right_foot_bone_name: str, 
        left_toe_bone_name: str,right_toe_bone_name: str,
        ):
    """ main - batch """
    ## Parameters
    armature_name = escape_identifier(armature_name)
    root_name = escape_identifier(root_name)
    prefix_name = escape_identifier(prefix_name)
    main_bone_name = escape_identifier(main_bone_name)
    head_top_bone_name = escape_identifier(head_top_bone_name)
    spine_bone_name = escape_identifier(spine_bone_name)
    left_hand_bone_name = escape_identifier(left_hand_bone_name)
    right_hand_bone_name = escape_identifier(right_hand_bone_name)
    left_foot_bone_name = escape_identifier(left_foot_bone_name)
    right_foot_bone_name = escape_identifier(right_foot_bone_name)
    left_toe_bone_name = escape_identifier(left_toe_bone_name)
    right_toe_bone_name = escape_identifier(right_toe_bone_name)

    try:
        bpy.ops.import_scene.fbx(filepath=file_path)  ## import fbx file

        obj = context.object
        ## class instance
        importer = ImportMixamo(obj, main_bone_name=main_bone_name)
        bake_method = BakeMethod(obj, main_bone_name=main_bone_name, method=method, is_start_feet=is_start_feet,
                                bake_x=bake_x, bake_y=bake_y, bake_z=bake_z, head_top_bone_name=head_top_bone_name,
                                spine_bone_name=spine_bone_name, left_hand_bone_name=left_hand_bone_name, 
                                right_hand_bone_name=right_hand_bone_name, left_foot_bone_name=left_foot_bone_name, 
                                right_foot_bone_name=right_foot_bone_name, left_toe_bone_name=left_toe_bone_name,
                                right_toe_bone_name=right_toe_bone_name)
        root_motion = RootMotion(obj, main_bone_name=main_bone_name)

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
            root_motion.edit_keyframes(bone_name=main_bone_name, vectors=hips_vectors)
        # ## set parent
        if is_add_root:
            importer.set_parent(child_bone=main_bone_name, parent_bone=root_name)
        # ## rename action
        if is_rename_action:
            importer.rename_action(file_path=file_path)
        # ## remove prefix
        if is_remove_prefix:
            importer.remove_prefix_name(prefix_name=prefix_name)
        if is_suffix_format:
            importer.suffix_format()
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
        type = bpy.types.OperatorFileListElement,
        options = {'HIDDEN', 'SKIP_SAVE'},
    ) # type: ignore

    directory: StringProperty(
        subtype = 'DIR_PATH'
    ) # type: ignore
    
    filter_glob: StringProperty(
        default = "*.fbx",
        options = {'HIDDEN'},
        maxlen = 255,
    ) # type: ignore

    # List of operator properties
    is_apply_transforms: BoolProperty(
        name = "Apply transform",
        description = "Apply the object's transform properties and fix animation intensity",
        default = True,
    ) # type: ignore
    
    is_add_root: BoolProperty(
        name = "Add root bone",
        description = "Add root bone and set as parent; Root Motion will bake keyframes using this bone. See 'Root' in 'Name Settings' for details",
        default = True,
    ) # type: ignore
    
    is_rename_action: BoolProperty(
        name = "Rename action",
        description = "Rename actions using the file name",
        default = True,
    ) # type: ignore
    
    is_remove_prefix: BoolProperty(
        name = "Remove prefix",
        description = "Rename bones by removing the <mixamorig:> prefix from all bones. See 'Prefix' in 'Name Settings' for details",
        default = True,
    ) # type: ignore

    is_suffix_format: BoolProperty(
        name = "Suffix format",
        description = "Rename bones by replacing 'Left/Right' in bone names with '.L/.R' suffixes and converting other letters to lowercase",
        default = True,
    ) # type: ignore
    
    is_delete_armature: BoolProperty(
        name = "Remove armature",
        description = "Remove redundant armature objects (usually named <Armature.00*>). See 'Armature' in 'Name Settings' for details",
        default = True,
    ) # type: ignore
    
    method: EnumProperty(
        name = "Method",
        description = "Calculation method for the height axis when baking keyframes; planar motion uses copy method",
        items = (
            ('COPY_DATA', "Copy", "Copy position keyframes of the main bone in world coordinates. See 'Main bone' in 'Name Settings' for details"),
            ('LOWEST_BONE', "Bone", "Get the height of the lowest bone from six key bones as height axis data. See 'Name Settings' for details"),
            ('BOUND_BOX', "Bound box", "Get the height of the bottom of the bounding box"),
        ),
        default = 'COPY_DATA',
    ) # type: ignore
    
    is_start_feet: BoolProperty(
        name = "Root starts from feet",
        description = "Root bone initially positioned at the feet; used for cases where the armature is not at world center in initial state",
        default = False,
    ) # type: ignore

    bake_x: BoolProperty(
        name = "X",
        description = "Bake <Location X> property to root bone",
        default = True,
    ) # type: ignore
    
    bake_y: BoolProperty(
        name = "Y",
        description = "Bake <Location Y> property to root bone",
        default = True,
    ) # type: ignore
    
    bake_z: BoolProperty(
        name = "Z",
        description = "Bake <Location Z> property to root bone",
        default = False,
    ) # type: ignore
    
    ## name settings
    armature_name: StringProperty(
        name = "Armature",
        description = "Armature name",
        default = "Armature",
    ) # type: ignore

    root_name: StringProperty(
        name = "Root",
        description = "Root name",
        default = "root",
    ) # type: ignore

    prefix_name: StringProperty(
        name = "Prefix",
        description = "Prefix name",
        default = "mixamorig:",
    ) # type: ignore

    main_bone_name: StringProperty(
        name = "Main bone",
        description = "Original root bone name, which contains animation data",
        default = "mixamorig:Hips",
    ) # type: ignore

    head_top_bone_name: StringProperty(
        name = "Head top",
        description = "Head top bone name",
        default = "mixamorig:HeadTop_End",
    ) # type: ignore

    left_hand_bone_name: StringProperty(
        name = "Left hand",
        description = "Left hand bone name",
        default = "mixamorig:LeftHand",
    ) # type: ignore

    right_hand_bone_name: StringProperty(
        name = "Right hand",
        description = "Right hand bone name",
        default = "mixamorig:RightHand",
    ) # type: ignore

    left_foot_bone_name: StringProperty(
        name = "Left foot",
        description = "Left foot bone name",
        default = "mixamorig:LeftFoot",
    ) # type: ignore

    right_foot_bone_name: StringProperty(
        name = "Right foot",
        description = "Right foot bone name",
        default = "mixamorig:RightFoot",
    ) # type: ignore

    left_toe_bone_name: StringProperty(
        name = "Left toe",
        description = "Left toe bone name",
        default = "mixamorig:LeftToe_End",
    ) # type: ignore

    right_toe_bone_name: StringProperty(
        name = "Right toe",
        description = "Right toe bone name",
        default = "mixamorig:RightToe_End",
    ) # type: ignore

    spine_bone_name: StringProperty(
        name = "Spine",
        description = "Spine bone name",
        default = "mixamorig:Spine",
    ) # type: ignore

    def execute(self, context):
        for file in self.files:
            file_path = os.path.join(self.directory, file.name)
            main(context, file_path=file_path, 
                is_apply_transform=self.is_apply_transforms, is_rename_action=self.is_rename_action, 
                is_remove_prefix=self.is_remove_prefix, is_suffix_format=self.is_suffix_format, 
                is_delete_armature=self.is_delete_armature, 
                is_add_root=self.is_add_root, method=self.method, is_start_feet=self.is_start_feet,
                bake_x=self.bake_x, bake_y=self.bake_y, bake_z=self.bake_z,
                armature_name=self.armature_name, root_name=self.root_name, prefix_name=self.prefix_name,
                main_bone_name=self.main_bone_name, head_top_bone_name=self.head_top_bone_name,
                spine_bone_name=self.spine_bone_name, left_hand_bone_name=self.left_hand_bone_name,
                right_hand_bone_name=self.right_hand_bone_name, left_foot_bone_name=self.left_foot_bone_name, 
                right_foot_bone_name=self.right_foot_bone_name, left_toe_bone_name=self.left_toe_bone_name,
                right_toe_bone_name=self.right_toe_bone_name,
                )
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
        column.prop(operator, 'is_suffix_format', icon='BONE_DATA')
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
        layout.prop(operator, 'is_start_feet', icon='ACTION')

        row = layout.row(align=True)
        row.prop(operator, 'bake_x', icon='KEYFRAME_HLT')
        row.prop(operator, 'bake_y', icon='KEYFRAME_HLT')
        row.prop(operator, 'bake_z', icon='KEYFRAME_HLT')

## Panel: name settings
class IMPORT_PT_name_settings(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Name Settings"
    bl_parent_id = "IMPORT_PT_base_settings"
    bl_options = {'DEFAULT_CLOSED'}
    
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
        column.prop(operator, 'armature_name')
        column.prop(operator, 'root_name')
        column.prop(operator, 'prefix_name')
        column.prop(operator, 'main_bone_name')
        column.prop(operator, 'head_top_bone_name')
        column.prop(operator, 'spine_bone_name')
        column.prop(operator, 'left_hand_bone_name')
        column.prop(operator, 'right_hand_bone_name')
        column.prop(operator, 'left_foot_bone_name')
        column.prop(operator, 'right_foot_bone_name')
        column.prop(operator, 'left_toe_bone_name')
        column.prop(operator, 'right_toe_bone_name')


def menu_func_import(self, context):
    self.layout.operator(BatchImport.bl_idname, text="Mixamo fbx(folder/*.fbx)")
    
# Register and add to the "file selector" menu (required to use F3 search "Text Import Operator" for quick access).
def register():
    bpy.utils.register_class(BatchImport)
    bpy.utils.register_class(IMPORT_PT_base_settings)
    bpy.utils.register_class(IMPORT_PT_bake_settings)
    bpy.utils.register_class(IMPORT_PT_name_settings)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.utils.unregister_class(IMPORT_PT_name_settings)
    bpy.utils.unregister_class(IMPORT_PT_bake_settings)
    bpy.utils.unregister_class(IMPORT_PT_base_settings)
    bpy.utils.unregister_class(BatchImport)

if __name__ == "__main__":
    register()
    # test call
    bpy.ops.import_mixamo.root_motion('INVOKE_DEFAULT')
#    unregister()
