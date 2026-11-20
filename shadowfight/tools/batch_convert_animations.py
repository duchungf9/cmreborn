import ast
import bpy
import csv
import os
import struct
import zipfile
import numpy as np

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
ZIP=os.environ.get('SF2_ARCHIVE',os.path.join(ROOT,'sources','Shadow Fight 2 Assets.zip'))
REPO=os.path.join(ROOT,'work','Gymnast-Tool-Suite')
TEMPLATE=os.path.join(REPO,'Blender Scenes','Shadow Fight 2','SF2Rig_Armature.blend')
OUT=os.path.join(ROOT,'outputs')
BLEND_OUT=os.path.join(OUT,'sf2_all_humanoid_animations.blend')
MANIFEST=os.path.join(OUT,'sf2_animation_manifest.csv')
SKIPPED=os.path.join(OUT,'sf2_non_humanoid_animations.csv')
LIMIT=int(os.environ.get('SF2_LIMIT','0'))
os.makedirs(OUT,exist_ok=True)

# Reuse the mapping validated by the single-clip converter.
source=open(os.path.join(OUT,'sf2_middle_hit_conversion.py'),encoding='utf-8').read()
tree=ast.parse(source)
ns={}
need={'ALIASES','NODE_TO_BONE','BODY_CHAIN','PIVOT_FOLLOW','LOCKED_TRACK_NODES','SF2_EXTRA','weapon_extra'}
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in need for t in node.targets):
  exec(compile(ast.Module(body=[node],type_ignores=[]),'<mappings>','exec'),ns)
ALIASES=ns['ALIASES']; NODE_TO_BONE=ns['NODE_TO_BONE']; BODY_CHAIN=ns['BODY_CHAIN']
PIVOT_FOLLOW=ns['PIVOT_FOLLOW']; LOCKED_TRACK_NODES=ns['LOCKED_TRACK_NODES']
SF2_EXTRA=ns['SF2_EXTRA']; WEAPON_EXTRA=ns['weapon_extra']

source_importer=open(os.path.join(REPO,'Addon','cascadeur','gymnast_tool_suite','shadow_fight_2','import_bin_sf2.py'),encoding='utf-8').read()
section=source_importer[source_importer.index('NODE_ORDER = ['):]
section=section[:section.index('\n]')+2]
NODE_ORDER=ast.literal_eval(section[len('NODE_ORDER = '):])
NODE_COUNT=len(NODE_ORDER)


def decode_points(data):
 if len(data)<4: raise ValueError('missing frame count')
 frame_count=struct.unpack_from('<i',data,0)[0]
 if frame_count<=0: raise ValueError(f'invalid frame count {frame_count}')
 frames=np.zeros((frame_count,NODE_COUNT,3),dtype=np.float32)
 offset=4; first_count=None
 for fi in range(frame_count):
  if offset+5>len(data): raise ValueError(f'truncated header at frame {fi}')
  count=struct.unpack_from('<i',data,offset+1)[0]
  if count<NODE_COUNT: raise ValueError(f'only {count} nodes at frame {fi}')
  if first_count is None: first_count=count
  payload=offset+5
  end=payload+12*count
  if end>len(data): raise ValueError(f'truncated payload at frame {fi}')
  frames[fi]=np.frombuffer(data,dtype='<f4',count=NODE_COUNT*3,offset=payload).reshape(NODE_COUNT,3)
  offset=end
 if offset!=len(data): raise ValueError(f'{len(data)-offset} trailing bytes')
 if not np.isfinite(frames).all(): raise ValueError('non-finite coordinates')
 return frames,first_count


def clear_scale_curves(action):
 if not action or not action.slots: return
 for layer in action.layers:
  for strip in layer.strips:
   for slot in action.slots:
    bag=strip.channelbag(slot)
    if not bag: continue
    for fc in list(bag.fcurves):
     if '.scale' in fc.data_path:
      bag.fcurves.remove(fc)


def add_constraint(pb,kind,target):
 c=pb.constraints.new(kind); c.target=target
 if kind=='LOCKED_TRACK': c.track_axis='TRACK_Z'; c.lock_axis='LOCK_Y'
 return c

bpy.ops.wm.open_mainfile(filepath=TEMPLATE,load_ui=False,use_scripts=False)
scene=bpy.context.scene
arm=bpy.data.objects.get('Armature')
if not arm or arm.type!='ARMATURE': raise RuntimeError('Template armature missing')
pose=arm.pose.bones
# Remove unassigned animation datablocks from the template to keep the library compact.
if arm.animation_data: arm.animation_data_clear()
arm.animation_data_create()
for act in list(bpy.data.actions):
 if act.users==0: bpy.data.actions.remove(act)

# The template has same-named static node markers, so these direct target objects acquire a suffix.
track={}
for src_name in NODE_ORDER:
 alias=ALIASES.get(src_name)
 if alias is None: continue
 obj=bpy.data.objects.new(alias,None); scene.collection.objects.link(obj)
 obj.empty_display_type='SPHERE'; obj.empty_display_size=1.0; obj.hide_render=True
 track[alias]=obj

# Set up the same SF2 point-follow rig used by the single-clip conversion.
for alias,target in track.items():
 if alias in LOCKED_TRACK_NODES:
  add_constraint(pose[LOCKED_TRACK_NODES[alias]],'LOCKED_TRACK',target)
 extra=SF2_EXTRA.get(alias) or WEAPON_EXTRA.get(alias)
 if extra and pose.get(extra[0]): add_constraint(pose[extra[0]],extra[1],target)
 if alias.endswith(('S_1','S_2')) or alias=='NTop' or alias.startswith('MacroNode') or alias.startswith('Weapon-Node'):
  continue
 if alias=='NHeadF':
  add_constraint(pose['HeadF'],'DAMPED_TRACK',target); continue
 bone_id=NODE_TO_BONE.get(alias)
 if not bone_id or not pose.get(bone_id): continue
 if alias.endswith('F'):
  add_constraint(pose[bone_id],'LOCKED_TRACK',target); continue
 if bone_id in PIVOT_FOLLOW and track.get('NPivot'):
  c=pose[bone_id].constraints.new('COPY_LOCATION'); c.target=track['NPivot']
 look=track.get(BODY_CHAIN.get(bone_id,alias))
 if look: add_constraint(pose[bone_id],'DAMPED_TRACK',look)

bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode='POSE')
entries=[]; skipped=[]; processed=0; total_frames=0
with zipfile.ZipFile(ZIP) as archive:
 paths=sorted(n for n in archive.namelist() if n.startswith('Shadow Fight 2 Assets/Animations/') and n.lower().endswith('.bin'))
 for path in paths:
  data=archive.read(path)
  try:
   frame_count=struct.unpack_from('<i',data,0)[0]
   # Fast-check the first frame before decoding all frames.
   first_nodes=struct.unpack_from('<i',data,5)[0]
   if first_nodes<NODE_COUNT:
    skipped.append((os.path.basename(path),frame_count,first_nodes,'non-humanoid/effect rig'))
    continue
   frames,node_count=decode_points(data)
  except Exception as exc:
   skipped.append((os.path.basename(path),-1,-1,str(exc)))
   continue
  clip=os.path.splitext(os.path.basename(path))[0]
  action_name='SF2_'+''.join(c if c.isalnum() or c=='_' else '_' for c in clip)
  scene.frame_start=1; scene.frame_end=frame_count; scene.render.fps=20; scene.render.fps_base=1.0
  # Re-key the 66 source point tracks for this clip.
  for index,src_name in enumerate(NODE_ORDER):
   alias=ALIASES.get(src_name)
   obj=track.get(alias)
   if not obj: continue
   for fi in range(frame_count):
    x,y,z=frames[fi,index]
    obj.location=(float(x),float(-z),float(y+76.0))
    obj.keyframe_insert(data_path='location',frame=fi+1,group=alias)
  arm.animation_data.action=None
  bpy.context.view_layer.update()
  result=bpy.ops.nla.bake(frame_start=1,frame_end=frame_count,only_selected=False,
       visual_keying=True,clear_constraints=False,use_current_action=False,bake_types={'POSE'},step=1)
  action=arm.animation_data.action if arm.animation_data else None
  if result!={'FINISHED'} or action is None:
   raise RuntimeError(f'Bake failed for {clip}: {result}')
  action.name=action_name
  action.use_fake_user=True
  clear_scale_curves(action)
  action['source_file']=os.path.basename(path)
  action['frame_count']=frame_count
  action['source_node_count']=node_count
  # Clear temporary point animation so the next clip starts without residual channels.
  for obj in track.values(): obj.animation_data_clear()
  # Remove temporary object actions left behind by keyframe_insert, preserving all rig actions.
  for temp_action in list(bpy.data.actions):
   if temp_action is not action and not temp_action.users and not temp_action.use_fake_user:
    bpy.data.actions.remove(temp_action)
  processed+=1; total_frames+=frame_count
  entries.append((action_name,os.path.basename(path),frame_count,node_count,action_name))
  if processed%10==0:
   print(f'PROGRESS {processed} clips / {total_frames} frames; last={clip}',flush=True)
  if LIMIT and processed>=LIMIT: break

# Make a representative attack action active, then remove point constraints and temporary targets.
chosen=next((a for a in bpy.data.actions if a.name=='SF2_middle_hit'),None)
if chosen is None and processed: chosen=arm.animation_data.action
for pb in arm.pose.bones:
 for c in list(pb.constraints): pb.constraints.remove(c)
arm.animation_data.action=chosen
for obj in list(track.values()): bpy.data.objects.remove(obj,do_unlink=True)
scene.frame_start=1
scene.frame_end=int(chosen.get('frame_count',1)) if chosen else 1
scene.frame_set(1)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active=arm

with open(MANIFEST,'w',newline='',encoding='utf-8') as f:
 w=csv.writer(f); w.writerow(['action','source_file','frames','source_nodes','fps']); w.writerows([(*row[:4],20) for row in entries])
with open(SKIPPED,'w',newline='',encoding='utf-8') as f:
 w=csv.writer(f); w.writerow(['source_file','frames','node_count','reason']); w.writerows(skipped)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT,compress=True)
print('COMPLETE',processed,'skipped',len(skipped),'total_frames',total_frames,'actions',len(bpy.data.actions),'file_bytes',os.path.getsize(BLEND_OUT),flush=True)
