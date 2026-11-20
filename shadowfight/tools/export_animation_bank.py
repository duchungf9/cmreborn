import bpy,os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
OUT=os.path.join(ROOT,'outputs')
BLEND=os.path.join(OUT,'sf2_all_humanoid_animations.blend')
bpy.ops.wm.open_mainfile(filepath=BLEND,load_ui=False,use_scripts=False)
arm=bpy.data.objects['Armature']
print('actions',len(bpy.data.actions),'active',arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None,flush=True)
for pb in arm.pose.bones: pb.custom_shape=None
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active=arm
p=os.path.join(OUT,'sf2_all_humanoid_animations.glb')
bpy.ops.export_scene.gltf(filepath=p,export_format='GLB',use_selection=True,
 export_animations=True,export_animation_mode='ACTIONS',export_action_filter=False,
 export_skins=True,export_frame_range=True,export_optimize_animation_size=True)
print('GLB',os.path.getsize(p),flush=True)
p=os.path.join(OUT,'sf2_all_humanoid_animations.fbx')
bpy.ops.export_scene.fbx(filepath=p,use_selection=True,add_leaf_bones=False,
 bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,
 bake_anim_use_all_actions=True,axis_forward='-Z',axis_up='Y')
print('FBX',os.path.getsize(p),flush=True)
