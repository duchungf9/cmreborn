import bpy
import numpy as np
import os

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
OUT=os.path.join(ROOT,'work','poc','proxy_mesh_frames')
os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT,'outputs','sf2_middle_hit_rigged.blend'),load_ui=False,use_scripts=False)
scene=bpy.context.scene
arm=bpy.data.objects['Armature']
scene.frame_start=1; scene.frame_end=20
objects=[o for o in bpy.data.objects if o.type=='MESH' and not o.hide_render and o.name.startswith(('Capsule','Weapon'))]
print('MESH_OBJECTS',len(objects))
for frame in range(1,21):
 scene.frame_set(frame); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get()
 vertices=[]; face_indices=[]; face_offsets=[0]; face_category=[]
 for obj in objects:
  ev=obj.evaluated_get(deps); mesh=ev.to_mesh(preserve_all_data_layers=False,depsgraph=deps)
  if not mesh or not mesh.vertices:
   ev.to_mesh_clear(); continue
  start=len(vertices)
  mat=ev.matrix_world
  vertices.extend([tuple(mat@v.co) for v in mesh.vertices])
  cname=obj.name.lower()
  cat=1 if 'muscle' in cname else (2 if 'edge' in cname else (3 if obj.name.startswith('Weapon') else 0))
  for poly in mesh.polygons:
   face_indices.extend(start+i for i in poly.vertices)
   face_offsets.append(len(face_indices))
   face_category.append(cat)
  ev.to_mesh_clear()
 arr=np.asarray(vertices,dtype=np.float32)
 inds=np.asarray(face_indices,dtype=np.int32)
 offs=np.asarray(face_offsets,dtype=np.int32)
 cats=np.asarray(face_category,dtype=np.uint8)
 segments=[]; bone_categories=[]
 for pb in arm.pose.bones:
  segments.append((arm.matrix_world@pb.head,arm.matrix_world@pb.tail))
  if pb.name.startswith('Weapon'):
   bone_categories.append(2)
  elif pb.name in {'Pelvis','Stomach','Chest','Neck','Head'}:
   bone_categories.append(1)
  else:
   bone_categories.append(0)
 segs=np.asarray(segments,dtype=np.float32)
 bcats=np.asarray(bone_categories,dtype=np.uint8)
 p=os.path.join(OUT,f'frame_{frame:02d}.npz')
 np.savez_compressed(p,vertices=arr,face_indices=inds,face_offsets=offs,face_category=cats,bone_segments=segs,bone_category=bcats)
 print(frame,'verts',len(arr),'faces',len(cats),'bounds',np.round(arr.min(0),1).tolist(),np.round(arr.max(0),1).tolist(),'bytes',os.path.getsize(p))
