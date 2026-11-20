import ast
import bpy
import math
import os
import struct
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
REPO = os.path.join(ROOT, 'work', 'Gymnast-Tool-Suite')
SCENE = os.path.join(REPO, 'Blender Scenes', 'Shadow Fight 2', 'SF2Rig_Armature.blend')
BIN = os.path.join(ROOT, 'work', 'poc', 'middle_hit.bin')
OUT = os.path.join(ROOT, 'outputs')
os.makedirs(OUT, exist_ok=True)

# Parse the public SF2 decoder's authoritative point order.
source = open(os.path.join(REPO, 'Addon', 'cascadeur', 'gymnast_tool_suite', 'shadow_fight_2', 'import_bin_sf2.py'), encoding='utf-8').read()
section = source[source.index('NODE_ORDER = ['):]
section = section[:section.index('\n]')+2]
NODE_ORDER = ast.literal_eval(section[len('NODE_ORDER = '):])

raw = open(BIN, 'rb').read()
frame_count = struct.unpack_from('<i', raw, 0)[0]
frames = np.empty((frame_count, len(NODE_ORDER), 3), dtype=np.float32)
offset = 4
for fi in range(frame_count):
    node_count = struct.unpack_from('<i', raw, offset + 1)[0]
    if node_count != len(NODE_ORDER):
        raise ValueError(f'Frame {fi}: expected {len(NODE_ORDER)} points, got {node_count}')
    offset += 5
    frames[fi] = np.frombuffer(raw, dtype='<f4', count=node_count*3, offset=offset).reshape(node_count, 3)
    offset += node_count * 12
if offset != len(raw):
    raise ValueError(f'Unexpected trailing bytes: {len(raw)-offset}')
if not np.isfinite(frames).all():
    raise ValueError('Animation contains non-finite values')

# BIN tracks use a different coordinate convention and a ground origin. The template
# armature is authored around z ~= 76 cm above that origin.
ALIASES = {
    'HeadF': 'NTop', 'Neck': 'NNeck',
    'Arm_2': 'NShoulder_2', 'Arm_1': 'NShoulder_1',
    'Forearm_2': 'NElbow_2', 'Forearm_1': 'NElbow_1',
    'Hand_2': 'NWrist_2', 'Hand_1': 'NWrist_1',
    'Fingertips_2_1': 'NFingertips_2', 'Fingertips_1_1': 'NFingertips_1',
    'Thigh_2': 'NHip_2', 'Thigh_1': 'NHip_1',
    'Calf_2': 'NKnee_2', 'Calf_1': 'NKnee_1',
    'Foot_2': 'NAnkle_2', 'Foot_1': 'NAnkle_1',
    'Toes_2': 'NToeTip_2', 'Toes_1': 'NToeTip_1', 'Pelvis': 'NPivot',
    'Stomach': 'NStomach', 'Chest': 'NChest', 'Head': 'NHead',
    'Toes_2_end': 'NToe_2', 'Toes_1_end': 'NToe_1',
    'Heel_2_end': 'NHeel_2', 'Heel_1_end': 'NHeel_1',
    'ToeS_2_end': 'NToeS_2', 'ToeS_1_end': 'NToeS_1',
    'Fingers_2': 'NKnuckles_2', 'Fingers_1': 'NKnuckles_1',
    'Knuckles_2_1_end': 'NKnucklesS_2', 'Knuckles_1_1_end': 'NKnucklesS_1',
    'Fingertips_2': 'NFingertipsS_2', 'Fingertips_1': 'NFingertipsS_1',
    'Fingers_2_1_end': 'NFingertipsSS_2', 'Fingers_1_1_end': 'NFingertipsSS_1',
    'HeadS_2_end': 'NHeadS_2', 'HeadS_1_end': 'NHeadS_1',
    'HeadF_end': 'NHeadF', 'ChestS_2_end': 'NChestS_2', 'ChestS_1_end': 'NChestS_1',
    'StomachS_2_end': 'NStomachS_2', 'StomachS_1_end': 'NStomachS_1',
    'ChestF_end': 'NChestF', 'StomachF_end': 'NStomachF', 'PelvisF_end': 'NPelvisF',
    'Hand_2_1_end': 'MacroNode1_2', 'Hand_2_2_end': 'MacroNode2_2',
    'Hand_1_1_end': 'MacroNode1_1', 'Hand_1_2_end': 'MacroNode2_1',
    'Knuckles_2_2_end': 'MacroNode3_2', 'Knuckles_1_2_end': 'MacroNode3_1',
    'Fingers_2_2_end': 'MacroNode4_2', 'Fingers_1_2_end': 'MacroNode4_1',
    'Fingertips_2_1_end': 'MacroNode5_2', 'Fingertips_1_1_end': 'MacroNode5_1',
    'Fingertips_2_2_end': 'MacroNode6_2', 'Fingertips_1_2_end': 'MacroNode6_1',
    'WeaponF_l': 'Weapon-Node1_1', 'ArmatureWeaponLeft': 'Weapon-Node2_1',
    'WeaponS_l': 'Weapon-Node3_1', 'WeaponDirection_l': 'Weapon-Node4_1',
    'WeaponF_r': 'Weapon-Node1_2', 'ArmatureWeaponRight': 'Weapon-Node2_2',
    'WeaponS_r': 'Weapon-Node3_2', 'WeaponDirection_r': 'Weapon-Node4_2',
}
# Additional end marker nodes are not used by the default 32-bone template.

bpy.ops.wm.open_mainfile(filepath=SCENE, load_ui=False, use_scripts=False)
scene = bpy.context.scene
armature = bpy.data.objects.get('Armature')
if not armature or armature.type != 'ARMATURE':
    raise RuntimeError('SF2 template armature was not found')

# The source scene contains a model-viewer node modifier setup; keep it in the .blend,
# but don't export those app-specific procedural objects to glTF.
for obj in list(bpy.data.objects):
    if obj.type == 'EMPTY' and obj.name.startswith('N'):
        bpy.data.objects.remove(obj, do_unlink=True)

scene.frame_start = 1
scene.frame_end = frame_count
scene.render.fps = 20
scene.render.fps_base = 1.0

track_objects = {}
for index, source_name in enumerate(NODE_ORDER):
    alias = ALIASES.get(source_name)
    if alias is None:
        continue
    if alias in track_objects:
        raise ValueError(f'Duplicate alias: {alias}')
    obj = bpy.data.objects.new(alias, None)
    scene.collection.objects.link(obj)
    obj.empty_display_type = 'SPHERE'
    obj.empty_display_size = 1.0
    obj.hide_render = True
    track_objects[alias] = obj
    for fi in range(frame_count):
        x, y, z = frames[fi, index]
        # BIN (x,y,z) -> Blender (x,-z,y); translate the whole sample onto the rig's ground level.
        obj.location = (float(x), float(-z), float(y + 76.0))
        obj.keyframe_insert(data_path='location', frame=fi+1, group=alias)

# Set up the same point-follow constraints used by the SF2 Blender template add-on.
NODE_TO_BONE = {
    'NTop':'Head', 'NHead':'Head', 'NHeadF':'HeadF',
    'NNeck':'Neck', 'NShoulder_2':'Clavicle_2', 'NShoulder_1':'Clavicle_1',
    'NElbow_2':'Arm_2', 'NElbow_1':'Arm_1', 'NWrist_2':'Forearm_2', 'NWrist_1':'Forearm_1',
    'NKnuckles_2':'Hand_2', 'NKnuckles_1':'Hand_1',
    'NFingertips_2':'Fingers_2', 'NFingertips_1':'Fingers_1',
    'NChest':'Chest', 'NChestF':'Chest', 'NChestS_2':'Chest', 'NChestS_1':'Chest',
    'NStomach':'Stomach', 'NStomachF':'Stomach', 'NStomachS_2':'Stomach', 'NStomachS_1':'Stomach',
    'NPivot':'Pelvis', 'NPelvisF':'Pelvis', 'NHip_2':'Hip_2', 'NHip_1':'Hip_1',
    'NKnee_2':'Thigh_2', 'NKnee_1':'Thigh_1', 'NAnkle_2':'Calf_2', 'NAnkle_1':'Calf_1',
    'NHeel_2':'Heel_2', 'NHeel_1':'Heel_1', 'NToe_2':'Foot_2', 'NToe_1':'Foot_1',
    'NToeS_2':'Foot_2', 'NToeS_1':'Foot_1', 'NToeTip_2':'Toes_2', 'NToeTip_1':'Toes_1',
    'NFingertipsS_2':'Fingers_2', 'NFingertipsS_1':'Fingers_1',
    'NFingertipsSS_2':'FingersS_2', 'NFingertipsSS_1':'FingersS_1',
    'MacroNode1_1':'Hand_1', 'MacroNode1_2':'Hand_2', 'MacroNode2_1':'Hand_1', 'MacroNode2_2':'Hand_2',
    'MacroNode3_1':'Hand_1', 'MacroNode3_2':'Hand_2', 'MacroNode4_1':'Fingers_1', 'MacroNode4_2':'Fingers_2',
    'MacroNode5_1':'FingersS_1', 'MacroNode5_2':'FingersS_2', 'MacroNode6_1':'FingersS_1', 'MacroNode6_2':'FingersS_2',
}
BODY_CHAIN = {'Pelvis':'NStomach', 'Stomach':'NChest', 'Chest':'NNeck', 'Neck':'NHead', 'Head':'NTop'}
PIVOT_FOLLOW = {'Pelvis','Hip_1','Hip_2'}
LOCKED_TRACK_NODES = {'NToeS_1':'Foot_1','NToeS_2':'Foot_2','NHeadS_2':'Head','NKnucklesS_1':'Hand_1','NKnucklesS_2':'Hand_2'}
SF2_EXTRA = {
    'NFingertipsSS_2':('FingersS_2','DAMPED_TRACK'), 'NFingertipsSS_1':('FingersS_1','DAMPED_TRACK'),
    'NFingertipsS_2':('Fingers_2','LOCKED_TRACK'), 'NFingertipsS_1':('Fingers_1','LOCKED_TRACK'),
    'MacroNode5_2':('FingersS_2','LOCKED_TRACK'), 'MacroNode5_1':('FingersS_1','LOCKED_TRACK'),
}
weapon_extra = {
    'Weapon-Node2_1':('Weapon_1','COPY_LOCATION'), 'Weapon-Node3_1':('Weapon_1','DAMPED_TRACK'), 'Weapon-Node4_1':('Weapon_1','LOCKED_TRACK'),
    'Weapon-Node2_2':('Weapon_2','COPY_LOCATION'), 'Weapon-Node3_2':('Weapon_2','DAMPED_TRACK'), 'Weapon-Node4_2':('Weapon_2','LOCKED_TRACK'),
}
pose = armature.pose.bones
for alias, target in track_objects.items():
    if alias in LOCKED_TRACK_NODES:
        c = pose[LOCKED_TRACK_NODES[alias]].constraints.new('LOCKED_TRACK'); c.target = target; c.track_axis='TRACK_Z'; c.lock_axis='LOCK_Y'
    extra = SF2_EXTRA.get(alias) or weapon_extra.get(alias)
    if extra:
        pb = pose.get(extra[0])
        if pb:
            c = pb.constraints.new(extra[1]); c.target = target
            if extra[1]=='LOCKED_TRACK': c.track_axis='TRACK_Z'; c.lock_axis='LOCK_Y'
    if alias.endswith(('S_1','S_2')) or alias in {'NTop'} or alias.startswith('MacroNode') or alias.startswith('Weapon-Node'):
        continue
    if alias=='NHeadF':
        c = pose['HeadF'].constraints.new('DAMPED_TRACK'); c.target=target
        continue
    bone_id = NODE_TO_BONE.get(alias)
    if not bone_id or not pose.get(bone_id):
        continue
    if alias.endswith('F'):
        c=pose[bone_id].constraints.new('LOCKED_TRACK'); c.target=target; c.track_axis='TRACK_Z'; c.lock_axis='LOCK_Y'
        continue
    if bone_id in PIVOT_FOLLOW:
        pivot = track_objects.get('NPivot')
        if pivot:
            c=pose[bone_id].constraints.new('COPY_LOCATION'); c.target=pivot
    look_name = BODY_CHAIN.get(bone_id, alias)
    look = track_objects.get(look_name)
    if look:
        c=pose[bone_id].constraints.new('DAMPED_TRACK'); c.target=look

# Give each bone its frame-by-frame pose, then remove constraints and keep ordinary keyframes.
bpy.ops.object.select_all(action='DESELECT')
armature.select_set(True)
bpy.context.view_layer.objects.active = armature
bpy.ops.object.mode_set(mode='POSE')
bpy.context.view_layer.update()
bpy.ops.nla.bake(frame_start=1, frame_end=frame_count, only_selected=False,
                 visual_keying=True, clear_constraints=True, use_current_action=True,
                 bake_types={'POSE'}, step=1)
bpy.ops.object.mode_set(mode='OBJECT')
scene.frame_set(1)

# Keep the rig clean and export only the conventional armature animation to glTF.
for obj in list(bpy.data.objects):
    if obj.type == 'EMPTY' and obj.name in track_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
# Select only the armature so app-specific procedural model objects are omitted from glTF.
bpy.ops.object.select_all(action='DESELECT')
armature.select_set(True)
bpy.context.view_layer.objects.active = armature
blend_path = os.path.join(OUT, 'sf2_middle_hit_rigged.blend')
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
# Custom bone-shape widgets are Blender viewport helpers; omit them from interchange exports.
for pb in armature.pose.bones:
    pb.custom_shape = None
glb_path = os.path.join(OUT, 'sf2_middle_hit_rigged.glb')
bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB', use_selection=True,
                          export_animations=True, export_skins=True, export_frame_range=True)
fbx_path = os.path.join(OUT, 'sf2_middle_hit_rigged.fbx')
bpy.ops.export_scene.fbx(filepath=fbx_path, use_selection=True, add_leaf_bones=False,
                         bake_anim=True, bake_anim_use_all_bones=True,
                         bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
                         axis_forward='-Z', axis_up='Y')

# Report bake state for validation.
action = armature.animation_data.action if armature.animation_data else None
curve_count = 0
if action:
    for layer in action.layers:
        for strip in layer.strips:
            bag = strip.channelbag(action.slots[0]) if action.slots else None
            if bag:
                curve_count += len(bag.fcurves)
print('OUTPUT_BLEND', blend_path)
print('OUTPUT_GLB', glb_path)
print('OUTPUT_FBX', fbx_path)
print('FRAME_COUNT', frame_count)
print('ALIAS_COUNT', len(track_objects))
print('ACTION', action.name if action else None, 'CURVES', curve_count)
print('POSE_BONES', len(armature.data.bones))
print('FILE_BYTES', os.path.getsize(blend_path), os.path.getsize(glb_path), os.path.getsize(fbx_path))
