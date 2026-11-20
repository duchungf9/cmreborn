import bpy,zipfile,struct,os,re,csv
import numpy as np
import bmesh

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
ZIP=os.environ.get('SF2_ARCHIVE',os.path.join(ROOT,'sources','Shadow Fight 2 Assets.zip'))
OUT=os.path.join(ROOT,'outputs')
BLEND_OUT=os.path.join(OUT,'sf2_non_humanoid_point_animations.blend')
GLB_OUT=os.path.join(OUT,'sf2_non_humanoid_point_animations.glb')
MANIFEST=os.path.join(OUT,'sf2_non_humanoid_animations.csv')
MAX_NODES=14

def parse(data):
 fc=struct.unpack_from('<i',data,0)[0]; frames=[]; counts=[]; offset=4
 for fi in range(fc):
  nc=struct.unpack_from('<i',data,offset+1)[0]
  p=offset+5; end=p+nc*12
  if end>len(data): raise ValueError(f'truncated frame {fi}')
  row=np.frombuffer(data,dtype='<f4',count=nc*3,offset=p).reshape(nc,3).copy()
  frames.append(row); counts.append(nc); offset=end
 if offset!=len(data) or len(set(counts))!=1: raise ValueError('invalid binary layout')
 return frames,counts[0]
def safe(n): return 'SF2_'+re.sub(r'[^A-Za-z0-9_]+','_',os.path.splitext(os.path.basename(n))[0])

bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.fps=20; scene.render.fps_base=1.0
arm_data=bpy.data.armatures.new('SF2_EffectPointRig')
arm=bpy.data.objects.new('SF2_EffectPointRig',arm_data); scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
offsets=[]
for i in range(MAX_NODES):
 x=float(i*5)
 eb=arm_data.edit_bones.new(f'Track_{i+1:02d}')
 eb.head=(x,0.0,0.0); eb.tail=(x,0.0,2.0)
 offsets.append((x,0.0,0.0))
bpy.ops.object.mode_set(mode='OBJECT')
arm.animation_data_create()

# Low-poly skinned markers make the otherwise abstract projectile/effect tracks visible.
verts=[]; faces=[]; groups=[[] for _ in range(MAX_NODES)]
for i,(ox,oy,oz) in enumerate(offsets):
 bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=12,v_segments=8,radius=1.8)
 start=len(verts)
 verts.extend([(v.co.x+ox,v.co.y+oy,v.co.z+oz) for v in bm.verts])
 for f in bm.faces: faces.append(tuple(start+v.index for v in f.verts))
 groups[i].extend(range(start,len(verts)))
 bm.free()
mesh=bpy.data.meshes.new('EffectTrackMarkerMesh'); mesh.from_pydata(verts,[],faces); mesh.update()
obj=bpy.data.objects.new('Animated_Point_Markers',mesh); scene.collection.objects.link(obj)
mat=bpy.data.materials.new('Track marker'); mat.diffuse_color=(0.95,0.47,0.14,1.0); mesh.materials.append(mat)
for i,indices in enumerate(groups):
 vg=obj.vertex_groups.new(name=f'Track_{i+1:02d}'); vg.add(indices,1.0,'REPLACE')
mod=obj.modifiers.new('Point rig skin','ARMATURE'); mod.object=arm
obj.parent=arm; obj.matrix_parent_inverse=arm.matrix_world.inverted()

entries=[]
with zipfile.ZipFile(ZIP) as z:
 paths=sorted(n for n in z.namelist() if n.startswith('Shadow Fight 2 Assets/Animations/') and n.lower().endswith('.bin'))
 for path in paths:
  data=z.read(path); frame_count=struct.unpack_from('<i',data,0)[0]; node_count=struct.unpack_from('<i',data,5)[0]
  if node_count>=67: continue
  frames,count=parse(data)
  scene.frame_start=1; scene.frame_end=frame_count
  action=bpy.data.actions.new(safe(path)); action.use_fake_user=True
  arm.animation_data.action=action
  for fi,row in enumerate(frames):
   for i,p in enumerate(row):
    pos=(float(p[0]),float(-p[2]),float(p[1]))
    pb=arm.pose.bones[f'Track_{i+1:02d}']
    base=offsets[i]
    pb.location=(pos[0]-base[0],pos[1]-base[1],pos[2]-base[2])
    pb.keyframe_insert(data_path='location',frame=fi+1,group=pb.name)
   # Place inactive tracks below the preview area, so shorter clips show only their real points.
   for i in range(count,MAX_NODES):
    pb=arm.pose.bones[f'Track_{i+1:02d}']; base=offsets[i]
    pb.location=(0.0-base[0],0.0-base[1],-2000.0-base[2])
    pb.keyframe_insert(data_path='location',frame=fi+1,group=pb.name)
  action['source_file']=os.path.basename(path); action['frame_count']=frame_count; action['source_node_count']=node_count
  entries.append((action.name,os.path.basename(path),frame_count,node_count))
  if len(entries)%10==0: print('PROGRESS',len(entries),flush=True)

preferred=next((a for a in bpy.data.actions if a.name=='SF2_fireball_middle'),None)
if preferred is None and bpy.data.actions: preferred=bpy.data.actions[0]
arm.animation_data.action=preferred
scene.frame_start=1; scene.frame_end=int(preferred.get('frame_count',1)) if preferred else 1; scene.frame_set(1)
with open(MANIFEST,'w',newline='',encoding='utf-8') as f:
 w=csv.writer(f); w.writerow(['action','source_file','frames','source_nodes','fps']); w.writerows([(*r,20) for r in entries])
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active=arm
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT,compress=True)
p=os.path.join(OUT,GLB_OUT.split('/')[-1])
bpy.ops.export_scene.gltf(filepath=p,export_format='GLB',use_selection=True,export_animations=True,
 export_animation_mode='ACTIONS',export_action_filter=False,export_skins=True,export_frame_range=True)
print('COMPLETE',len(entries),'actions',len(bpy.data.actions),'frames',sum(r[2] for r in entries),'blend',os.path.getsize(BLEND_OUT),'glb',os.path.getsize(GLB_OUT),flush=True)
