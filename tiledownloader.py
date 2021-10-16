from owslib.wfs import WebFeatureService
import json
import urllib
import gzip
import argparse
from cjio import cityjson

CITYJSON_URL = "https://data.3dbag.nl/cityjson/v210908_fd2cee53/3dbag_v210908_fd2cee53_{TID}.json.gz"

def bbox_from_poi(poi, radius):
  x, y = poi
  return [ x-radius, y-radius, x+radius, y+radius ]

def get_tile_ids(bbox=(120389,485945,121389,486045)):
  wfs11 = WebFeatureService(url='https://data.3dbag.nl/api/BAG3D_v2/wfs', version='1.1.0')
  response = wfs11.getfeature(typename='BAG3D_v2:bag_tiles_3k', bbox=bbox, srsname='urn:x-ogc:def:crs:EPSG:28992', outputFormat='json')

  tiles = json.loads( response.read().decode('utf-8') )['features']
  tile_ids = [ tile['properties']['tile_id'] for tile in tiles ]

  return tile_ids

def download_3dbag(tile_ids):
  fnames = []
  for tid in tile_ids:
    url = CITYJSON_URL.format(TID=tid)
    print(url)
    fname = tid+'.json'
    fnames.append(fname)
    with urllib.request.urlopen(url) as response, open(fname, 'wb') as out_file:
      data = response.read() # a `bytes` object
      out_file.write( gzip.decompress(data) )
  
  return fnames

def prepf(file):
  def set_base_zero(cm):
    def collect_vertex_ids(v_correct, h_base, boundaries):
      if type(boundaries[0]) == list:
        for bb in boundaries:
          collect_vertex_ids(v_correct, h_base, bb)
      else:
        for v in boundaries:
          v_correct[v] = h_base
    
    v_correct = {}
    for building in cm.get_cityobjects(type='Building').values():
      h_base = int( building.attributes['h_maaiveld'] / cm.j['transform']['scale'][2] )
      for partid in building.children:
        part = cm.j['CityObjects'][partid]
        for geom in part['geometry']:
          collect_vertex_ids(v_correct, h_base, geom['boundaries'])
    for v, hb in v_correct.items():
      cm.j['vertices'][v][2] -= hb

  cm = cityjson.load(file)
  cm.extract_lod('2.2')
  set_base_zero(cm)
  return cm

def prep_for_blender(files, fout='x.obj', origin_offset = (0,0)):
  import multiprocessing

  pool_obj = multiprocessing.Pool()

  print('prepping cm\'s...')
  cms = pool_obj.map(prepf,files)
  # print(answer)
  
  print('merging cm\'s...')
  cms[0].merge(cms[1:])
  cm = cms[0]

  print('shifting origin...')
  # move to origin, notice that the transform object is gone after merging and the vertices are floats with the full coordinates
  for v in cm.j['vertices']:
    v[0] -= origin_offset[0]
    v[1] -= origin_offset[1]

  print('writing obj...')
  with open(fout, mode='w') as fo:
    re = cm.export2obj()
    fo.write(re.getvalue())

if __name__ == '__main__':
  # poi = (207515.1,474217.3)
  # radius = 1000
  # city_name = 'deventer'
  parser = argparse.ArgumentParser()
  parser.add_argument("poi", help="point of interest", nargs=2, type=float)
  parser.add_argument("radius", help="radius of bounding box around poi", type=float, default=1000)
  parser.add_argument("fout", help="name of output obj file", type=str)
  args = parser.parse_args()

  # print('getting tile ids...')
  # tids = get_tile_ids( bbox_from_poi(args.poi, args.radius) )
  # print('downloading tiles...')
  # fnames = download_3dbag(tids)
  # print('prepping for blender...')
  # prep_for_blender(fnames, args.fout', origin_offset=args.poi)

  with open('blendersetup.py', 'w') as f:
    f.write("bpy.ops.import_scene.obj(filepath='{}', filter_glob='*.obj;*.mtl', use_edges=False, use_smooth_groups=False, use_split_objects=False, use_split_groups=False, use_groups_as_vgroups=False, use_image_search=False, split_mode='OFF', global_clight_size=0, axis_forward='Y', axis_up='Z')".format(args.fout))