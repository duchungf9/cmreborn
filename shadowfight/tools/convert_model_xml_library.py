import bpy, zipfile, xml.etree.ElementTree as ET, os, re, csv
from collections import Counter

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
ZIP=os.environ.get('SF2_ARCHIVE',os.path.join(ROOT,'sources','Shadow Fight 2 Assets.zip'))
OUT=os.path.join(ROOT,'outputs')
BLEND_OUT=os.path.join(OUT,'sf2_model_xml_library.blend')
GLB_OUT=os.path.join(OUT,'sf2_model_xml_library.glb')
CSV_OUT=os.path.join(OUT,'sf2_model_xml_manifest.csv')
os.makedirs(OUT,exist_ok=True)

DUP_FIXES=((b'Iterations="10" Iterations="10"',b'Iterations="10"'),
           (b'Attenuation="0.1" Attenuation="0.1"',b'Attenuation="0.1"'))
def parse_xml(data):
 for old,new in DUP_FIXES: data=data.replace(old,new)
 return ET.fromstring(data)
def f(v):
 if not v or v=='Null': return 0.0
 return float(str(v).replace(',','.'))
def node_pos(e): return (f(e.get('X')),f(e.get('Y')),f(e.get('Z')))
def section(root,name):
 e=root.find(name); return list(e) if e is not None else []
def resolve(root,dep_nodes):
 nodes=section(root,'Nodes')
 local={e.tag:node_pos(e) for e in nodes if e.get('Type')!='MacroNode' and all(e.get(k) is not None for k in ('X','Y','Z'))}
 macros=[e for e in nodes if e.get('Type')=='MacroNode']
 pos={**dep_nodes,**local}
 pending=list(macros)
 for _ in range(len(pending)+1):
  done=[]
  for e in pending:
   vals=[]; weights=[]
   for k in range(1,5):
    child=e.get(f'ChildNode{k}'); weight=e.get(f'LCC{k}')
    if not child or child=='Null' or weight is None: continue
    p=pos.get(child)
    if p is not None: vals.append(p); weights.append(f(weight))
   if vals:
    pos[e.tag]=tuple(sum(p[i]*w for p,w in zip(vals,weights)) for i in range(3)); done.append(e)
  if not done: break
  pending=[e for e in pending if e not in done]
 return pos,len(pending)

def safe_name(s):
 s=re.sub(r'[^A-Za-z0-9_]+','_',s).strip('_')
 return s[:63] or 'model'

def category(path):
 name=os.path.basename(path).lower()
 if name.startswith(('weapon_','ranged_')): return 'Weapon'
 if name.startswith(('armor_','helm_')): return 'Armor'
 if name.startswith(('head_','head.','body_','body.')) or name in ('head.xml','body.xml'): return 'Character'
 if name.startswith(('magic_','acid_','energy_','fire_','ice_','root_')): return 'Effect'
 return 'Other'

archive=zipfile.ZipFile(ZIP)
all_names=archive.namelist()
dep_paths=[n for n in all_names if '/Models/Dependencies/' in n and n.lower().endswith('.xml')]
deps=[]
for path in sorted(dep_paths):
 root=parse_xml(archive.read(path))
 coords={e.tag:node_pos(e) for e in section(root,'Nodes') if all(e.get(k) is not None for k in ('X','Y','Z'))}
 deps.append((path,coords))
model_paths=sorted(n for n in all_names if n.startswith('Shadow Fight 2 Assets/Models/') and '/Dependencies/' not in n and n.lower().endswith('.xml'))

# Fresh clean scene: this file is a mesh library, with one object per model XML.
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
root_col=bpy.data.collections.new('SF2 Model XML Library'); scene.collection.children.link(root_col)
folder_cols={}
materials={}
colors={'Weapon':(0.60,0.36,0.12,1.0),'Armor':(0.18,0.34,0.54,1.0),'Character':(0.12,0.15,0.20,1.0),'Effect':(0.42,0.20,0.56,1.0),'Other':(0.32,0.37,0.43,1.0)}
for cat,col in colors.items():
 mat=bpy.data.materials.new('SF2_'+cat); mat.diffuse_color=col; materials[cat]=mat
rows=[]; total_triangles=0; imported=0; zero=0; partial=0; parse_errors=[]
for idx,path in enumerate(model_paths,1):
 try:
  model=parse_xml(archive.read(path))
 except Exception as exc:
  parse_errors.append((path,str(exc))); rows.append((path,'',0,0,0,'parse_error',str(exc))); continue
 triangles=[e for e in section(model,'Figures') if e.get('Type')=='Triangle']
 candidate=None
 for dep_path,dep_nodes in deps:
  pos,unresolved_macros=resolve(model,dep_nodes)
  faces=[]; used=[]; idx_by_name={}
  for tri in triangles:
   names=[tri.get(k) for k in ('Node1','Node2','Node3')]
   if not all(names) or not all(n in pos for n in names): continue
   face=[]
   for name in names:
    if name not in idx_by_name:
     idx_by_name[name]=len(used); used.append(name)
    face.append(idx_by_name[name])
   if len(set(face))==3: faces.append(tuple(face))
  score=(len(faces),-unresolved_macros)
  if candidate is None or score>candidate[0]: candidate=(score,dep_path,pos,used,faces,unresolved_macros)
 if candidate is None: rows.append((path,'',0,len(triangles),0,'no_dependency', '')); zero+=1; continue
 _,dep_path,pos,used,faces,unresolved_macros=candidate
 if not faces:
  zero+=1; rows.append((path,os.path.basename(dep_path),len(used),len(triangles),0,'no_triangles','')); continue
 coords=[(pos[n][0],-pos[n][2],pos[n][1]) for n in used]
 folder=path.split('/')[-2]
 if folder not in folder_cols:
  fc=bpy.data.collections.new(safe_name(folder)); root_col.children.link(fc); folder_cols[folder]=fc
 mesh_name=safe_name(folder+'__'+os.path.splitext(os.path.basename(path))[0])
 mesh=bpy.data.meshes.new(mesh_name)
 mesh.from_pydata(coords,[],faces); mesh.update(); mesh.validate(verbose=False,clean_customdata=False)
 obj=bpy.data.objects.new(mesh_name,mesh); folder_cols[folder].objects.link(obj)
 cat=category(path); mesh.materials.append(materials[cat])
 obj['source_xml']=path; obj['dependency_xml']=dep_path; obj['triangle_count']=len(faces); obj['category']=cat
 imported+=1; total_triangles+=len(faces)
 if len(faces)<len(triangles): partial+=1
 status='ok' if len(faces)==len(triangles) else 'partial'
 note=f'unresolved_macronodes={unresolved_macros}' if unresolved_macros else ''
 rows.append((path,os.path.basename(dep_path),len(used),len(triangles),len(faces),status,note))
 if idx%100==0: print('PROGRESS',idx,'/',len(model_paths),'meshes',imported,'triangles',total_triangles,flush=True)

archive.close()
with open(CSV_OUT,'w',newline='',encoding='utf-8') as out:
 w=csv.writer(out); w.writerow(['source_xml','dependency_xml','vertices_used','triangles_source','triangles_imported','status','notes']); w.writerows(rows)
# Save editable Blender asset library.
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT,compress=True)
# Export all converted triangle meshes as a single standard GLB mesh library.
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.data.objects:
 if obj.type=='MESH': obj.select_set(True)
bpy.context.view_layer.objects.active=next((o for o in bpy.data.objects if o.type=='MESH'),None)
bpy.ops.export_scene.gltf(filepath=GLB_OUT,export_format='GLB',use_selection=True,export_animations=False,export_skins=False)
print('COMPLETE', 'sources',len(model_paths),'meshes',imported,'triangles',total_triangles,'zero',zero,'partial',partial,'parse_errors',len(parse_errors),'blend_bytes',os.path.getsize(BLEND_OUT),'glb_bytes',os.path.getsize(GLB_OUT),flush=True)
if parse_errors: print('PARSE_ERRORS',parse_errors,flush=True)
